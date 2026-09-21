"""Video-grounded Windows-style Qt presentation. No core/HTTP/time implementation."""
from pathlib import Path
from datetime import datetime
from collections import deque
from time import monotonic
import ast
import json
import shutil
from zipfile import ZipFile, BadZipFile
from PySide6.QtCore import Qt, QTimer, QUrl, QByteArray, QSize, Signal
from PySide6.QtGui import (QDesktopServices,QPixmap,QPainter,QIcon,QColor,QFontDatabase,
    QFont,QBrush,QLinearGradient,QPainterPath)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QPushButton,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QFrame,
    QLineEdit,QSpinBox,QAbstractSpinBox,QSizePolicy,QFileDialog,QGraphicsDropShadowEffect,
    QPlainTextEdit,QListWidget,QStyledItemDelegate,QComboBox,QButtonGroup)
from .lifecycle import Session,ACTIVE,TERMINAL
from .http_server import HTTPService
from .protocol import identifier
from .leaderboard_client import LeaderboardGateway
from .platform_support import APP_VERSION, qt_font_stack

LABELS={'IDLE':'尚未开始','PREPARING':'正在准备数据','COUNTDOWN':'5秒倒计时',
        'WAITING_FOR_ENTER':'等待机器狗进入','RUNNING':'测试进行中','FINISHED':'测试已结束',
        'ABORTED':'测试已中止','TIMEOUT':'超时退出'}
REASONS={'user_exit':'机器狗已退出 /exit 指令','manual_abort':'手工中止','app_closed':'关闭程序',
         'program_timeout':'程序运行超时','test_window_timeout':'测试窗口超时','virtual_timeout':'虚拟时间超时',
         'technical_error':'技术异常','process_interrupted':'程序意外退出'}
LOGO=Path(__file__).resolve().parent/'assets/reference_logo.png'
LEADERBOARD_CACHE_TTL_S=30
STYLE='''
QWidget { font-family: __FONT_STACK__; font-size:12px; color:#0b1417; }
QMainWindow, QWidget#body, QWidget#page { background:#f3f5f4; }
QLabel { background:transparent; }
QWidget#sidebar { background:#202e30; border-right:1px solid #bac3c3; }
QLabel#brand { color:#ffffff; font-size:13px; font-weight:600; }
QLabel#navgroup, QLabel#version { color:#a3b7b9; font-size:10px; }
QFrame#separator { background:#3a484a; border:0; }
QWidget#header, QWidget#titlebar { background:#fcfdfc; }
QWidget#header { border-bottom:1px solid #d4d9d7; }
QLabel#headerTitle { font-size:12px; font-weight:700; }
QLabel#localNote { font-size:10px; font-weight:600; color:#840e0e; }
QFrame#notice { background:#fcf7df; border-top:1px solid #d4c99b; border-bottom:1px solid #d4c99b; }
QFrame#notice QLabel { color:#4e4214; }
QLabel#eyebrow { color:#4e5b60; font-size:10px; font-weight:600; }
QLabel#heading { font-size:16px; font-weight:700; }
QLabel#sectionTitle { font-size:13px; font-weight:700; }
QLabel#muted { color:#4e5b60; font-size:10px; }
QLabel#metric { font-size:13px; font-weight:700; }
QLabel#case { font-family:Menlo,Consolas,monospace; font-size:11px; font-weight:700; }
QFrame#panel { background:#fcfdfc; border-top:1px solid #bfc8c7; border-bottom:1px solid #d2d8d6; }
QFrame#strip { background:#f7faf8; border-bottom:1px solid #d2d8d6; }
QFrame#truth { background:#f3fbf6; border-bottom:1px solid #c5ded2; }
QFrame#saved { background:#e6f5ee; border-bottom:1px solid #b5d5c7; }
QFrame#countdown { background:#e8f4fc; border:1px solid #b2cbdc; }
QLabel#countTitle { font-size:16px; font-weight:700; color:#21465f; }
QLabel#countNumber { font-size:30px; font-weight:700; color:#21465f; }
QLabel#status { color:#185e50; background:#e8f5ef; border:1px solid #b6d7cb; border-radius:3px; font-size:10px; padding:6px 8px; }
QPushButton { background:#fcfdfc; border:1px solid #b4bdc0; border-radius:3px; padding:5px 12px; font-size:12px; font-weight:600; min-height:18px; }
QPushButton:hover { background:#eef4f1; border-color:#839491; }
QPushButton:pressed { background:#e3ebe6; }
QPushButton:disabled { color:#8d9996; background:#eef1ef; border-color:#d7dedb; }
QPushButton[role="primary"] { color:white; background:#18765f; border-color:#105d4b; }
QPushButton[role="primary"]:disabled { color:#bdcbc5; background:#9eb4aa; border-color:#9eb4aa; }
QPushButton[role="danger"] { color:white; background:#ae1419; border-color:#880e11; }
QPushButton[role="nav"] { color:#e1ecec; background:transparent; border:0; padding:6px 8px; font-size:12px; font-weight:400; text-align:left; }
QPushButton[role="nav"]:checked { color:white; background:#34494d; }
QPushButton[role="nav"]:hover { background:#2c3d40; }
QPushButton[role="icon"] { border:0; background:transparent; padding:0; min-height:0; }
QPushButton[role="title"] { border:0; background:transparent; border-radius:0; min-height:0; padding:0; font-weight:400; }
QPushButton[role="title"]:hover { background:#e6ebea; }
QPushButton#close:hover { background:#c92f35; color:white; }
QLineEdit,QSpinBox,QComboBox { background:#fcfdfc; border:1px solid #b9c1c3; border-radius:3px; padding:6px 9px; min-height:17px; }
QLineEdit:disabled { color:#84918d; background:#f8faf9; }
QComboBox QAbstractItemView { background:#fcfdfc; color:#0b1417; border:1px solid #b9c1c3; selection-background-color:#e5f1eb; selection-color:#112b22; }
QFileDialog { background:#f3f5f4; color:#0b1417; }
QFileDialog QListView,QFileDialog QTreeView { background:#fcfdfc; color:#0b1417; border:1px solid #cfd8d4; selection-background-color:#e5f1eb; selection-color:#112b22; }
QFileDialog QListView#sidebar { background:#f5f8f6; color:#0b1417; border:1px solid #cfd8d4; }
QFileDialog QListView::item:hover,QFileDialog QTreeView::item:hover { background:#f0f6f3; color:#0b1417; }
QFileDialog QToolButton { color:#0b1417; background:#fcfdfc; border:1px solid #b9c1c3; border-radius:3px; padding:4px; }
QFileDialog QToolButton:hover { background:#eef4f1; border-color:#839491; }
QTableWidget { font-weight:400; background:#fcfdfc; border:0; gridline-color:#e4e9e6; selection-background-color:#e5f1eb; selection-color:#112b22; font-size:10px; }
QHeaderView { background:#f6f9f7; }
QTableCornerButton::section { background:#f6f9f7; border:0; }
QHeaderView::section { background:#f6f9f7; color:#293b40; border:0; border-bottom:1px solid #cfd8d4; text-align:left; font-size:10px; font-weight:700; padding:0 8px; }
QTableWidget::item { border-bottom:1px solid #e5e9e7; padding:0 8px; }
QScrollBar:vertical { background:#fcfdfc; width:11px; margin:10px 0; }
QScrollBar::handle:vertical { background:#b5bfba; min-height:20px; }
QScrollBar::handle:vertical:disabled { background:#fcfdfc; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:#fcfdfc; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { border:0; height:10px; background:#f8faf9; }
QFrame#dialog { background:#fcfdfc; border:1px solid #c7d2ce; border-radius:5px; }
QFrame#dialogFooter { background:#f6faf7; border-top:1px solid #d3dbd7; border-bottom-left-radius:5px; border-bottom-right-radius:5px; }
QFrame#leaderHero { background:#eef6f3; border:1px solid #c9dbd4; border-radius:4px; }
QFrame#leaderPanel { background:#fcfdfc; border:1px solid #d2d9d6; border-radius:4px; }
QLabel#online { color:#147259; background:#e6f5ee; border:1px solid #b7dacb; border-radius:3px; padding:4px 8px; font-size:10px; font-weight:700; }
QLabel#offline { color:#8b2e2e; background:#faeeee; border:1px solid #e4c5c5; border-radius:3px; padding:4px 8px; font-size:10px; font-weight:700; }
QPushButton[role="tab"] { border:0; border-bottom:2px solid transparent; border-radius:0; background:transparent; padding:4px 18px; }
QPushButton[role="tab"]:checked { color:#126f58; border-bottom-color:#18765f; background:#edf6f2; }
QPushButton[role="account"] { color:#176f59; background:#f3faf7; border:1px solid #b9d8cc; padding:4px 10px; font-size:10px; }
QPushButton[role="account"]:hover { background:#e8f5ef; border-color:#7fb4a0; }
QPushButton[role="sourceChoice"] { color:#344642; background:#f8faf9; border:1px solid #c5ceca; border-radius:4px; padding:7px 11px; text-align:left; font-size:10px; font-weight:600; }
QPushButton[role="sourceChoice"]:hover { background:#eff5f2; border-color:#8ca29a; }
QPushButton[role="sourceChoice"]:checked { color:#114c3d; background:#e8f4ef; border:2px solid #287760; padding:6px 10px; }
QPushButton[role="sourceChoice"]:disabled { color:#84918d; background:#f0f3f1; border-color:#d7dedb; }
QPlainTextEdit#sourceCode { background:#14201f; color:#dce9e5; border:0; padding:10px; font-family:Menlo,Consolas,monospace; font-size:10px; }
QListWidget#sourceTree { background:#f5f8f6; border:0; border-right:1px solid #d7dfdb; font-size:10px; padding:4px; }
QListWidget#sourceTree::item { padding:6px; }
QListWidget#sourceTree::item:selected { background:#dfeee8; color:#123e32; }
QTableWidget#leaderboardTable { background:#fcfdfc; border:1px solid #d2d9d6; border-radius:4px; }
QTableWidget#leaderboardTable::item { border-bottom:1px solid #e5e9e7; padding:0 7px; }
QTableWidget#leaderboardTable::item:hover { background:#f7faf8; }
QTableWidget#leaderboardTable::item:selected { background:#e5f1eb; color:#112b22; }
QTableWidget#leaderboardTable QHeaderView::section { background:#f6f9f7; color:#536267; border-bottom:1px solid #cfd8d4; padding:0 7px; }
QFrame#sourceViewerCard { background:#fcfdfc; border:1px solid #c7d2ce; border-radius:6px; }
QWidget#sourceViewerHeader { background:#fcfdfc; border-bottom:1px solid #d7dfdb; }
QLabel#sourceDetails { color:#52625f; background:#f7faf8; border-bottom:1px solid #d7dfdb; padding:6px 12px; font-size:9px; }
'''
PATHS={
 'play':'<circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4z"/>',
 'clipboard':'<rect x="5" y="4" width="14" height="17" rx="2"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="m8 12 3 3 5-5"/>',
 'shield':'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z"/><path d="m8 11 3 3 5-5"/>',
 'bell':'<path d="M4 17h16l-3-4V9a5 5 0 0 0-10 0v4zM10 21h4"/>',
 'account':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="9" r="3"/><path d="M6 19v-2a6 5 0 0 1 12 0v2"/>',
 'settings':'<path d="m10 2 4 0 1 3 3 1 3 3-2 3 1 3-3 3-3-1-2 3-3-1-1-3-3-1-1-4 3-2 0-3 3-2z"/><circle cx="12" cy="12" r="3"/>',
 'info':'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
 'file':'<path d="M5 2h9l5 5v15H5zM14 2v6h5M9 5v2m0 3v2m0 3v2"/>',
 'radio':'<path d="m8 22 4-14 4 14M9 18h6M6 5a9 9 0 0 0 0 13M18 5a9 9 0 0 1 0 13M9 8a5 5 0 0 0 0 7M15 8a5 5 0 0 1 0 7"/><circle cx="12" cy="10" r="1"/>',
 'refresh':'<path d="M20 10a8 8 0 0 0-14-5L3 8m0-5v5h5M4 14a8 8 0 0 0 14 5l3-3m0 5v-5h-5"/>',
 'wifi':'<path d="M2 8a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0M9 16a5 5 0 0 1 6 0"/><circle cx="12" cy="20" r=".6"/>',
 'exit':'<path d="M9 3H4v18h5M12 12h10m-5-5 5 5-5 5"/>',
 'stop':'<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6"/>',
 'download':'<path d="M12 2v13m-5-5 5 5 5-5M4 15v6h16v-6"/>',
 'eye':'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
 'trophy':'<path d="M8 3h8v5a4 4 0 0 1-8 0zM10 12v4m4-4v4M8 20h8M10 16h4M8 5H4v2a4 4 0 0 0 4 4M16 5h4v2a4 4 0 0 1-4 4"/>',
 'code':'<path d="m8 7-5 5 5 5m8-10 5 5-5 5m-2-13-4 16"/>',
 'help':'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.7 2.7 0 1 1 4.3 2.2c-1.1.8-1.8 1.3-1.8 2.8M12 18v.2"/>'}

def icon(name,color='#405154',size=18):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    p=QPixmap(size*2,size*2);p.fill(Qt.transparent);painter=QPainter(p);QSvgRenderer(QByteArray(svg.encode())).render(painter);painter.end();p.setDevicePixelRatio(2);return QIcon(p)

def label(text='',name=None):
    w=QLabel(text)
    if name:w.setObjectName(name)
    return w

def button(text,callback=None,role=None,width=None,ico=None):
    w=QPushButton(text)
    if role:w.setProperty('role',role)
    if width:w.setFixedWidth(width)
    w.setFixedHeight(30)
    if ico:w.setIcon(icon(ico,'#ffffff' if role in ('primary','danger') else '#405154',15));w.setIconSize(QSize(15,15))
    if callback:w.clicked.connect(callback)
    return w

def box(name='panel',margins=(0,0,0,0),horizontal=False):
    f=QFrame();f.setObjectName(name);layout=QHBoxLayout(f) if horizontal else QVBoxLayout(f)
    layout.setContentsMargins(*margins);layout.setSpacing(0);return f,layout

def image_label(size):
    w=QLabel();w.setPixmap(QPixmap(str(LOGO)).scaled(size*2,size*2,Qt.KeepAspectRatio,Qt.SmoothTransformation));w.pixmap().setDevicePixelRatio(2)
    w.setScaledContents(True);w.setFixedSize(size,size);return w

def duration(seconds):return '尚未进入' if seconds is None else f'{seconds//60:02d}:{seconds%60:02d}'

def score(value):
    return '—' if value is None else f'{float(value):,.2f} s'

def percent(value):
    return '—' if value is None else f'{float(value)*100:.2f}%'

def display_version(value):
    value=str(value)
    return value[:-2] if value.endswith('.0') else value

def local_metrics(row):
    return row.get('result_metrics') or {}

def local_result_text(row, include_practice_truth=False):
    metrics=local_metrics(row)
    if not metrics:return '本次测试未形成成绩指标'
    text=(f"清除率 {percent(metrics.get('clear_rate'))}  ·  "
          f"平均清除 {score(metrics.get('mean_clear_time_s'))}  ·  "
          f"本局 {metrics.get('target_count','—')} 个干扰源")
    truth=row.get('summary') if include_practice_truth else None
    if truth:text+=f"  ·  全向 {truth['omni']} / 定向 {truth['directional']}"
    return text

def local_history_summary(rows):
    metrics=[local_metrics(row) for row in rows if local_metrics(row)]
    if not metrics:return '暂无成绩'
    targets=sum(m['target_count'] for m in metrics)
    cleared=sum(m['cleared_count'] for m in metrics)
    means=[float(m['mean_clear_time_s']) for m in metrics if m.get('mean_clear_time_s') is not None]
    clear_rate=cleared/targets if targets else 0.0
    if not means:return f'{len(metrics)} 局 · 清除率 {percent(clear_rate)} · 暂无平均清除时间'
    average=sum(means)/len(means)
    return (f'{len(metrics)} 局 · 清除率 {percent(clear_rate)} · 平均 {score(average)} · '
            f'局均范围 {min(means):,.2f}–{max(means):,.2f} s')

def local_mean_range(metrics):
    fastest=metrics.get('fastest_clear_time_s',metrics.get('mean_clear_time_s'))
    slowest=metrics.get('slowest_clear_time_s',metrics.get('mean_clear_time_s'))
    return '—' if fastest is None or slowest is None else f'{float(fastest):,.2f}–{float(slowest):,.2f} s'

def short_test_code(value):
    value=str(value)
    return value if len(value)<=16 else value[:8]+'…'+value[-4:]

def detect_zip_dependencies(path):
    imports=set()
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith('.py'):continue
            tree=ast.parse(archive.read(name).decode('utf-8'),filename=name)
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports.update(alias.name.split('.',1)[0] for alias in node.names)
                elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module.split('.',1)[0])
    if 'scipy' in imports:return 'numpy==2.3.5\nscipy==1.16.3','已自动识别：NumPy + SciPy'
    if 'numpy' in imports:return 'numpy==2.3.5','已自动识别：NumPy'
    return '','已自动识别：Python 标准库'

def scene_spread(row):
    if row.get('scene_count') == 1 and row.get('target_count') is not None:
        return f"{int(row['target_count'])} 个干扰源"
    fastest,slowest=row.get('fastest_clear_time_s'),row.get('slowest_clear_time_s')
    return '—' if fastest is None or slowest is None else f'{float(fastest):,.2f}–{float(slowest):,.2f} s'

def local_time(value):
    if not value:return '—'
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone().strftime('%m/%d %H:%M')
    except (TypeError,ValueError):return str(value)

class Nav(QWidget):
    def __init__(self,callback):
        super().__init__();self.index=0;self.buttons=[];v=QVBoxLayout(self);v.setContentsMargins(8,3,8,0);v.setSpacing(0)
        names=['演练测试','问题3正式测试','问题4正式测试','排行榜','公告','账号','设置','帮助 / 规则','关于']
        symbols=['play','clipboard','shield','trophy','bell','account','settings','help','info']
        for i,(name,symbol) in enumerate(zip(names,symbols)):
            if i in (0,1,3,4):
                if i:
                    v.addSpacing(9);line=QFrame();line.setObjectName('separator');line.setFixedHeight(1);v.addWidget(line);v.addSpacing(4)
                group=label({0:'测试',1:'正式测试',3:'在线服务',4:'其他'}[i],'navgroup');group.setContentsMargins(7,0,0,0);group.setFixedHeight(21);v.addWidget(group)
            b=button(name,lambda checked=False,n=i:self.setCurrentRow(n),role='nav',ico=symbol);b.setCheckable(True);b.setIcon(icon(symbol,'#d9e8e8',16));b.setIconSize(QSize(16,16));b.setFixedHeight(30)
            b.setFixedWidth(128 if i in (1,2,7) else 82 if i in (0,3) else 62)
            self.buttons.append(b);v.addWidget(b,0,Qt.AlignLeft);v.addSpacing(3)
        v.addStretch();self.callback=callback
    def currentRow(self):return self.index
    def setCurrentRow(self,index):
        self.index=index
        for i,b in enumerate(self.buttons):b.setChecked(i==index)
        self.callback(index)

class TitleBar(QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName('titlebar');self.setFixedHeight(22);self.window_=window
        h=QHBoxLayout(self);h.setContentsMargins(5,0,0,0);h.setSpacing(3);h.addWidget(image_label(12));h.addWidget(label('无线电干扰源环境模拟器'));h.addStretch()
        for text,fn in [('—',window.showMinimized),('□',self.maximize),('×',window.close)]:
            b=button(text,fn,'title',36);b.setFixedHeight(22)
            if text=='×':b.setObjectName('close');b.setStyleSheet('font-size:18px;')
            h.addWidget(b)
    def maximize(self):self.window_.showNormal() if self.window_.isMaximized() else self.window_.showMaximized()
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:self.window_.windowHandle().startSystemMove()
    def mouseDoubleClickEvent(self,event):self.maximize()

class Modal(QWidget):
    """Same-window veil and centered web-style dialog, never an OS-native sheet."""
    def __init__(self,parent,title,text,confirm='确认',cancel=None,callback=None):
        super().__init__(parent);self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,115); }')
        self.setGeometry(parent.rect());self.callback=callback
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch()
        row=QHBoxLayout();row.addStretch();self.card,v=box('dialog');self.card.setFixedWidth(380)
        body=QWidget();b=QVBoxLayout(body);b.setContentsMargins(18,17,18,17);b.setSpacing(8)
        b.addWidget(label(title,'heading'));self.message=label(text);self.message.setWordWrap(True);self.message.setStyleSheet('color:#4e5b60; font-size:11px;');b.addWidget(self.message);v.addWidget(body)
        footer,h=box('dialogFooter',(18,12,18,12),True);h.addStretch();h.setSpacing(8)
        self.cancel_button=button(cancel,lambda:self.finish(False),width=82) if cancel else None
        if self.cancel_button:h.addWidget(self.cancel_button)
        self.confirm_button=button(confirm,lambda:self.finish(True),'primary',82);h.addWidget(self.confirm_button);v.addWidget(footer)
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(28);shadow.setOffset(0,12);self.card.setGraphicsEffect(shadow)
        row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show()
    def finish(self,ok):
        self.hide();self.deleteLater()
        if self.callback:self.callback(ok)

class WidgetCellDelegate(QStyledItemDelegate):
    """Keep machine-readable item text while a rich widget owns its painting."""
    def initStyleOption(self,option,index):
        super().initStyleOption(option,index)
        if index.data(Qt.UserRole):option.text=''

class DataTable(QTableWidget):
    def __init__(self,headers,widths,empty_text,empty_icon='file',row_height=29):
        super().__init__(0,len(headers));self.fractions=widths;self.empty_text=empty_text
        self.setHorizontalHeaderLabels(headers);self.verticalHeader().hide();self.verticalHeader().setDefaultSectionSize(row_height)
        self.horizontalHeader().setFixedHeight(32);self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed);self.setShowGrid(False)
        self.setEditTriggers(QTableWidget.NoEditTriggers);self.setSelectionBehavior(QTableWidget.SelectRows)
        self.verticalScrollBar().rangeChanged.connect(lambda a,b:self.verticalScrollBar().setEnabled(b>a));self.verticalScrollBar().setEnabled(False);self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.empty=QWidget(self.viewport());ev=QVBoxLayout(self.empty);ev.setContentsMargins(0,0,0,0);ev.setSpacing(8)
        sym=QLabel();sym.setPixmap(icon(empty_icon,size=20).pixmap(20,20));sym.setAlignment(Qt.AlignCenter);ev.addWidget(sym)
        self.empty_label=label(empty_text,'muted');self.empty_label.setAlignment(Qt.AlignCenter);ev.addWidget(self.empty_label);self.empty.setFixedSize(260,46);self.place_empty()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        for i,f in enumerate(self.fractions):self.setColumnWidth(i,int((self.width()-12)*f))
        self.place_empty()
    def place_empty(self):self.empty.move((self.viewport().width()-260)//2,(self.viewport().height()-46)//2)
    def set_empty_text(self,text):self.empty_text=text;self.empty_label.setText(text)
    def rows(self,values):
        self.setRowCount(len(values));self.empty.setVisible(not values)
        for i,row in enumerate(values):
            for j,value in enumerate(row):self.setItem(i,j,QTableWidgetItem(str(value)))
        self.place_empty()
        for i,f in enumerate(self.fractions):self.setColumnWidth(i,int((self.width()-12)*f))

def centered_cell(widget,left_rule=None,interactive=False):
    cell=QWidget();layout=QHBoxLayout(cell);layout.setContentsMargins(1,0,1,0);layout.setSpacing(0);layout.addStretch();layout.addWidget(widget);layout.addStretch()
    if not interactive:cell.setAttribute(Qt.WA_TransparentForMouseEvents,True)
    if left_rule:cell.setStyleSheet(f'background:transparent;border-left:2px solid {left_rule};')
    else:cell.setStyleSheet('background:transparent;')
    return cell

def rich_cell(table,row,column,widget,interactive=False):
    table.item(row,column).setData(Qt.UserRole,True)
    table.setCellWidget(row,column,centered_cell(widget,interactive=interactive))

def left_rich_cell(table,row,column,widget):
    table.item(row,column).setData(Qt.UserRole,True)
    cell=QWidget();layout=QHBoxLayout(cell);layout.setContentsMargins(7,0,4,0);layout.setSpacing(0);layout.addWidget(widget,1)
    cell.setAttribute(Qt.WA_TransparentForMouseEvents,True);cell.setStyleSheet('background:transparent;')
    table.setCellWidget(row,column,cell)

class RankBadge(QLabel):
    PALETTES={
        1:('#846323','#b18a3e','#92702a','#71531c'),
        2:('#59676d','#879499','#657278','#4e5a5f'),
        3:('#7a503c','#a57458','#875a43','#694332'),
    }
    def __init__(self,rank):
        super().__init__(f'{rank:02d}');self.setAlignment(Qt.AlignCenter);self.setFixedSize(26,24)
        a,b,c,border=self.PALETTES[rank]
        self.setStyleSheet(f'color:white;background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {a},stop:.48 {b},stop:1 {c});border:1px solid {border};border-radius:5px;font-family:Menlo,Consolas,monospace;font-size:10px;font-weight:700;')

class VerifiedBadge(QFrame):
    def __init__(self):
        super().__init__();self.setFixedSize(76,24);self.setStyleSheet('QFrame { background:transparent;border:0; } QLabel { background:transparent;border:0;color:#697574;font-size:9px;font-weight:700; }')
        h=QHBoxLayout(self);h.setContentsMargins(1,0,1,0);h.setSpacing(5)
        shield=QLabel();shield.setFixedSize(13,20);shield.setAlignment(Qt.AlignCenter);shield.setPixmap(icon('shield','#17856e',11).pixmap(11,11));h.addWidget(shield);h.addWidget(label('VERIFIED'));h.addStretch()

class OpenSourceBadge(QFrame):
    def __init__(self):
        super().__init__();self.setFixedSize(118,26);self.setStyleSheet('QFrame { background:#f1f3f5;border:1px solid #cfd6d5;border-radius:13px; } QLabel { border:0;background:transparent; }')
        h=QHBoxLayout(self);h.setContentsMargins(0,0,5,0);h.setSpacing(0)
        emblem=QLabel();emblem.setFixedSize(29,24);emblem.setAlignment(Qt.AlignCenter);emblem.setPixmap(icon('code','#ffffff',11).pixmap(11,11));emblem.setStyleSheet('background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #174f49,stop:.5 #326c66,stop:1 #263f51);border-top-left-radius:12px;border-bottom-left-radius:12px;')
        h.addWidget(emblem);copy=QVBoxLayout();copy.setContentsMargins(7,2,0,2);copy.setSpacing(0)
        top=label('OPEN SOURCE');top.setStyleSheet('color:#465574;font-size:7px;font-weight:700;');bottom=label('VERIFIED');bottom.setStyleSheet('color:#697574;font-size:7px;font-weight:600;')
        copy.addWidget(top);copy.addWidget(bottom);h.addLayout(copy,1)

class OpenSourceTeamName(QWidget):
    """Slow metallic sheen reserved for OPEN SOURCE VERIFIED team names."""
    def __init__(self,text):
        super().__init__();self.text=str(text);self.phase=0.0;self.setToolTip(self.text)
        self.setFixedHeight(30);self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TransparentForMouseEvents,True);self.setAttribute(Qt.WA_TranslucentBackground,True)
        self.timer=QTimer(self);self.timer.setInterval(60);self.timer.timeout.connect(self.advance);self.timer.start()
    def advance(self):
        self.phase=(self.phase+.012)%1.0;self.update()
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.Antialiasing,True)
        font=QFont(self.font());font.setPixelSize(14);font.setWeight(QFont.DemiBold);painter.setFont(font)
        rect=self.rect().adjusted(0,1,-2,-1);metrics=painter.fontMetrics();text=metrics.elidedText(self.text,Qt.ElideRight,max(1,rect.width()))
        baseline=rect.top()+(rect.height()-metrics.height())//2+metrics.ascent();path=QPainterPath();path.addText(rect.left(),baseline,font,text)
        metal=QLinearGradient(rect.left(),0,rect.right(),0)
        for stop,color in ((0.0,'#174f49'),(.28,'#477276'),(.50,'#aa8b4e'),(.68,'#667f86'),(1.0,'#214e4c')):metal.setColorAt(stop,QColor(color))
        painter.fillPath(path,QBrush(metal))
        center=rect.left()-34+self.phase*(rect.width()+68);sheen=QLinearGradient(center-28,0,center+28,0)
        sheen.setColorAt(0.0,QColor(255,248,218,0));sheen.setColorAt(.42,QColor(237,226,188,38));sheen.setColorAt(.5,QColor(255,251,225,205));sheen.setColorAt(.58,QColor(221,234,230,42));sheen.setColorAt(1.0,QColor(255,248,218,0))
        painter.fillPath(path,QBrush(sheen));painter.end()

class SourceButton(QPushButton):
    NORMAL='QPushButton { color:white;background:#176454;border:1px solid #125447;border-radius:12px;padding:2px 4px;font-size:9px;font-weight:700;min-height:0; } QPushButton:pressed { background:#145a4d;border-color:#104c42; }'
    HOVER='QPushButton { color:white;background:#2c7f6e;border:1px solid #0f4e42;border-radius:12px;padding:2px 4px;font-size:9px;font-weight:700;min-height:0; } QPushButton:pressed { background:#145a4d;border-color:#104c42; }'
    def __init__(self,callback,text='查看源码'):
        super().__init__(text);self.setProperty('role','source');self.setFixedSize(70,24);self.setStyleSheet(self.NORMAL);self.setIcon(icon('code','#ffffff',10));self.setIconSize(QSize(10,10));self.clicked.connect(callback)
    def enterEvent(self,event):
        self.setStyleSheet(self.HOVER);super().enterEvent(event)
    def leaveEvent(self,event):
        self.setStyleSheet(self.NORMAL);super().leaveEvent(event)

class SourceViewer(QWidget):
    fileRequested = Signal(str)
    def __init__(self,parent,close):
        super().__init__(parent);self.close_callback=close;self.metadata=None
        self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground);self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,145); }')
        self.setGeometry(parent.rect());outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch()
        row=QHBoxLayout();row.addStretch();self.card,v=box('sourceViewerCard');self.card.setFixedSize(760,500)
        top=QWidget();top.setObjectName('sourceViewerHeader');th=QHBoxLayout(top);th.setContentsMargins(18,12,12,10);th.setSpacing(8)
        titles=QVBoxLayout();titles.setSpacing(2);self.team=label('正在读取源码…','heading');titles.addWidget(self.team);self.meta=label('通过 HTTPS 从排行榜获取','muted');titles.addWidget(self.meta);th.addLayout(titles);th.addStretch();self.owner_badge=label('OWNER · 私有提交','status');self.owner_badge.hide();th.addWidget(self.owner_badge);self.badge=OpenSourceBadge();th.addWidget(self.badge);th.addWidget(button('×',self.close,'icon',24));v.addWidget(top)
        content=QWidget();ch=QHBoxLayout(content);ch.setContentsMargins(0,0,0,0);ch.setSpacing(0)
        self.tree=QListWidget();self.tree.setObjectName('sourceTree');self.tree.setFixedWidth(170);self.tree.currentTextChanged.connect(self.select_file);ch.addWidget(self.tree)
        right=QWidget();rv=QVBoxLayout(right);rv.setContentsMargins(0,0,0,0);rv.setSpacing(0);self.details=label('','sourceDetails');self.details.setContentsMargins(12,5,12,5);self.details.setFixedHeight(48);self.details.setWordWrap(True);rv.addWidget(self.details)
        self.text=QPlainTextEdit();self.text.setObjectName('sourceCode');self.text.setReadOnly(True);self.text.setPlainText('正在读取…');rv.addWidget(self.text,1);ch.addWidget(right,1);v.addWidget(content,1)
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(18);shadow.setOffset(0,6);shadow.setColor(QColor(12,25,23,46));self.card.setGraphicsEffect(shadow)
        row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show()
    def close(self):
        self.hide();self.deleteLater();self.close_callback()
    def set_error(self,message):self.text.setPlainText(message)
    def set_metadata(self,data):
        self.metadata=data;public=data.get('is_public',True);self.badge.setVisible(public);self.owner_badge.setVisible(not public)
        self.team.setText(data['team_name']);s=data.get('verified_score') or {};rank='排名 #'+str(data['rank']) if data.get('rank') else '尚未上榜';self.meta.setText(f"{data['task'].upper()} · {rank} · 平均 {score(s.get('mean_clear_time_s'))} · 局均范围/单局数量 {scene_spread(s)} · 清除率 {percent(s.get('clear_rate'))}")
        self.details.setText(f"认证时间 {local_time(data.get('verified_at'))}  ·  {data['simulator_version']}\nSOURCE SHA256  {data['source_sha256']}")
        self.tree.blockSignals(True);self.tree.clear();items=['运行分析'] if data.get('analysis') else [];self.tree.addItems(items+['策略说明','README']);self.tree.addItems(data['source_tree']);self.tree.blockSignals(False);self.tree.setCurrentRow(0)
    def select_file(self,name):
        if not self.metadata:return
        if name=='运行分析':
            a=self.metadata.get('analysis') or {};runtime=a.get('runtime') or {};lines=[f"评测状态：{a.get('state','—')}",f"提交时间：{local_time(a.get('created_at'))}",f"完成时间：{local_time(a.get('finished_at'))}",f"入口：{self.metadata.get('entrypoint','—')}"]
            if runtime:lines.append('运行环境：'+' · '.join(f'{k} {v}' for k,v in runtime.items()))
            for i,item in enumerate(a.get('sandbox') or [],1):lines.append(f"验证运行 {i}：{item.get('status','—')}"+(f" · {float(item['elapsed_wall_s']):.2f}s" if item.get('elapsed_wall_s') is not None else ''))
            if a.get('message'):lines.extend(['',a['message']])
            self.text.setPlainText('\n'.join(lines))
        elif name=='策略说明':self.text.setPlainText(self.metadata.get('description') or '未提供单独的策略说明，请查看 README。')
        elif name=='README':self.text.setPlainText(self.metadata.get('readme') or '未提供 README。')
        elif name:self.text.setPlainText('正在读取 '+name+'…');self.fileRequested.emit(name)
    def set_file(self,name,content):
        if self.tree.currentItem() and self.tree.currentItem().text()==name:self.text.setPlainText(content)

class LeaderboardAuth(QWidget):
    """Compact in-app sign-in dialog; anonymous leaderboard access remains available."""
    def __init__(self,parent,submit,close):
        super().__init__(parent);self.submit_callback=submit;self.close_callback=close;self.mode='login'
        self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground);self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,125); }')
        self.setGeometry(parent.rect());outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch()
        row=QHBoxLayout();row.addStretch();self.card,v=box('dialog');self.card.setFixedWidth(410)
        top=QWidget();th=QHBoxLayout(top);th.setContentsMargins(18,14,12,8);th.setSpacing(8)
        titles=QVBoxLayout();titles.setSpacing(2);self.title=label('登录排行榜','heading');titles.addWidget(self.title);self.subtitle=label('登录后提交策略、查看排名和历史成绩','muted');titles.addWidget(self.subtitle);th.addLayout(titles);th.addStretch();th.addWidget(button('×',self.close,'icon',24));v.addWidget(top)
        body=QWidget();bv=QVBoxLayout(body);bv.setContentsMargins(18,8,18,16);bv.setSpacing(6)
        tabs=QHBoxLayout();tabs.setSpacing(6);self.login_tab=button('登录',lambda:self.set_mode('login'),'tab',80);self.register_tab=button('注册',lambda:self.set_mode('register'),'tab',80);self.login_tab.setCheckable(True);self.register_tab.setCheckable(True);tabs.addWidget(self.login_tab);tabs.addWidget(self.register_tab);tabs.addStretch();bv.addLayout(tabs);bv.addSpacing(3)
        bv.addWidget(label('用户名','muted'));self.username=QLineEdit();self.username.setPlaceholderText('请输入用户名');self.username.setMaxLength(32);bv.addWidget(self.username)
        bv.addWidget(label('密码','muted'));self.password=QLineEdit();self.password.setPlaceholderText('请输入密码');self.password.setEchoMode(QLineEdit.Password);self.password.setMaxLength(64);self.password_eye=self.password.addAction(icon('eye','#566863',14),QLineEdit.TrailingPosition);self.password_eye.triggered.connect(lambda:self.toggle_password(self.password));bv.addWidget(self.password)
        self.confirm_label=label('确认密码','muted');bv.addWidget(self.confirm_label);self.confirm=QLineEdit();self.confirm.setPlaceholderText('再输入一次密码');self.confirm.setEchoMode(QLineEdit.Password);self.confirm.setMaxLength(64);self.confirm_eye=self.confirm.addAction(icon('eye','#566863',14),QLineEdit.TrailingPosition);self.confirm_eye.triggered.connect(lambda:self.toggle_password(self.confirm));bv.addWidget(self.confirm)
        self.feedback=label('未登录也可以查看完整公开榜。','muted');self.feedback.setWordWrap(True);bv.addWidget(self.feedback);v.addWidget(body)
        footer,h=box('dialogFooter',(18,12,18,12),True);h.addStretch();h.setSpacing(8)
        self.submit_button=button('登录',self.submit,'primary',90);self.login_button=self.submit_button;h.addWidget(self.submit_button);v.addWidget(footer)
        self.password.returnPressed.connect(self.submit);self.confirm.returnPressed.connect(self.submit);self.set_mode('login')
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(28);shadow.setOffset(0,12);self.card.setGraphicsEffect(shadow)
        row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show();self.username.setFocus()
    def toggle_password(self,field):field.setEchoMode(QLineEdit.Normal if field.echoMode()==QLineEdit.Password else QLineEdit.Password)
    def set_mode(self,mode):
        self.mode=mode;register=mode=='register';self.login_tab.setChecked(not register);self.register_tab.setChecked(register);self.confirm_label.setVisible(register);self.confirm.setVisible(register);self.title.setText('创建排行榜账号' if register else '登录排行榜');self.subtitle.setText('注册后即可直接提交策略并参与个人排名' if register else '登录后提交策略、查看排名和历史成绩');self.submit_button.setText('注册并登录' if register else '登录');self.feedback.setStyleSheet('color:#4e5b60;font-size:10px;');self.feedback.setText('密码 8–64 个字符。' if register else '未登录也可以查看完整公开榜。')
    def submit(self):
        method=self.mode;username=self.username.text().strip();password=self.password.text()
        if not username or not password:self.set_error('请输入用户名和密码。');return
        if method=='register' and password!=self.confirm.text():self.set_error('两次输入的密码不一致。');return
        if method=='register' and not 8<=len(password)<=64:self.set_error('密码须为 8–64 个字符。');return
        self.set_busy(True,'正在通过 HTTPS '+('登录…' if method=='login' else '注册…'))
        self.submit_callback(method,username,password)
    def set_busy(self,busy,message=None):
        self.submit_button.setEnabled(not busy);self.login_tab.setEnabled(not busy);self.register_tab.setEnabled(not busy);self.username.setEnabled(not busy);self.password.setEnabled(not busy);self.confirm.setEnabled(not busy)
        if message:self.feedback.setStyleSheet('color:#4e5b60;font-size:10px;');self.feedback.setText(message)
    def set_error(self,message):
        self.set_busy(False);self.feedback.setStyleSheet('color:#9a2d2d;font-size:10px;');self.feedback.setText(message)
    def close(self):
        self.hide();self.deleteLater();self.close_callback()

class StrategyUpload(QWidget):
    def __init__(self,parent,teams,submit,close):
        super().__init__(parent);self.submit_callback=submit;self.close_callback=close;self.team_id=teams[0]['team_id']
        self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground);self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,125); }');self.setGeometry(parent.rect())
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch();row=QHBoxLayout();row.addStretch();self.card,v=box('dialog');self.card.setFixedWidth(520)
        top=QWidget();th=QHBoxLayout(top);th.setContentsMargins(18,14,12,8);titles=QVBoxLayout();titles.setSpacing(2);titles.addWidget(label('提交策略','heading'));titles.addWidget(label('服务器隔离评测 · 公开选择提交后不可更改','muted'));th.addLayout(titles);th.addStretch();th.addWidget(button('×',self.close,'icon',24));v.addWidget(top)
        body=QWidget();bv=QVBoxLayout(body);bv.setContentsMargins(18,6,18,14);bv.setSpacing(7)
        bv.addWidget(label('选择评测任务','muted'));self.task=QComboBox();self.task.addItem('问题3（Q3）','q3');self.task.addItem('问题4（Q4）','q4');self.task.setMinimumHeight(30);bv.addWidget(self.task)
        bv.addWidget(label('选择源码 ZIP','muted'));files=QHBoxLayout();files.setSpacing(7);self.path=QLineEdit();self.path.setReadOnly(True);self.path.setPlaceholderText('请选择 source.zip');files.addWidget(self.path,1);self.choose_button=button('选择 ZIP',self.choose,width=82,ico='file');files.addWidget(self.choose_button);bv.addLayout(files)
        self.environment=label('运行环境将在选择 ZIP 后自动识别','muted');bv.addWidget(self.environment)
        bv.addWidget(label('结果公开方式','muted'))
        choices=QHBoxLayout();choices.setSpacing(8);self.visibility_group=QButtonGroup(self);self.visibility_group.setExclusive(True)
        self.public_option=button('公开源码（推荐）\n认证后公开源码并显示专属徽章',role='sourceChoice');self.public_option.setCheckable(True);self.public_option.setFixedHeight(48)
        self.private_option=button('仅提交成绩\n源码不公开',role='sourceChoice');self.private_option.setCheckable(True);self.private_option.setFixedHeight(48)
        self.visibility_group.addButton(self.public_option,1);self.visibility_group.addButton(self.private_option,0);self.public_option.setChecked(True)
        choices.addWidget(self.public_option,1);choices.addWidget(self.private_option,1);bv.addLayout(choices)
        self.feedback=label('ZIP 第一层直接放 strategy.py；入口固定为 strategy.py:run；最大 10 MiB。','muted');self.feedback.setWordWrap(True);bv.addWidget(self.feedback);v.addWidget(body)
        footer,h=box('dialogFooter',(18,10,18,10),True);h.addWidget(label('上传后自动进入 Docker 评测队列','muted'));h.addStretch();self.submit_button=button('提交策略',self.submit,'primary',104);h.addWidget(self.submit_button);v.addWidget(footer)
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(28);shadow.setOffset(0,12);self.card.setGraphicsEffect(shadow);row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show()
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,'选择源码压缩包',str(Path.home()),'ZIP (*.zip)',options=QFileDialog.DontUseNativeDialog)
        if path:
            self.path.setText(path)
            try:self.environment.setText(detect_zip_dependencies(path)[1])
            except (BadZipFile,UnicodeError,SyntaxError,KeyError,OSError):self.environment.setText('无法识别 ZIP，请检查源码文件')
    def submit(self):
        if not self.path.text():self.set_error('请选择 source.zip。');return
        try:dependencies,_=detect_zip_dependencies(self.path.text())
        except (BadZipFile,UnicodeError,SyntaxError,KeyError,OSError):self.set_error('ZIP 无法读取，或 Python 源码不是有效的 UTF-8 文件。');return
        public=self.public_option.isChecked();self.set_busy(True,'正在通过 HTTPS 上传源码…');self.submit_callback(self.team_id,self.task.currentData(),self.path.text(),'strategy.py:run',dependencies,'',public,public)
    def set_busy(self,busy,message=None):
        self.submit_button.setEnabled(not busy);self.task.setEnabled(not busy);self.path.setEnabled(not busy);self.choose_button.setEnabled(not busy);self.public_option.setEnabled(not busy);self.private_option.setEnabled(not busy)
        if message:self.feedback.setStyleSheet('color:#4e5b60;font-size:10px;');self.feedback.setText(message)
    def set_error(self,message):self.set_busy(False);self.feedback.setStyleSheet('color:#9a2d2d;font-size:10px;');self.feedback.setText(message)
    def close(self):self.hide();self.deleteLater();self.close_callback()

class Window(QMainWindow):
    def __init__(self,store,leaderboard=None):
        super().__init__();self.store=store;self.session=Session(store);self.service=None;self.server_error=''
        self.remote=leaderboard or LeaderboardGateway(parent=self);self.leaderboard_task='q3';self.leaderboard_rows=[];self.leaderboard_cache={};self.leaderboard_bootstrapped=False;self.leaderboard_user=None;self.leaderboard_teams=[];self.leaderboard_submissions=[];self.source_viewer=None;self.source_viewer_owner=False;self.leaderboard_auth_dialog=None;self.strategy_upload_dialog=None;self.leaderboard_error_kind=None
        self.personal_identity_pending=False
        self.release_config={'current_version':APP_VERSION,'latest_version':APP_VERSION,'release_notes':'v30 首个公开版本。','mac_download_url':'','windows_download_url':'','announcement':'Q3Q4 Simulator v30 已发布。','feedback_url':''}
        self.current_task='q3';self.current_mode='practice';self.detail=False;self.modal=None;self.shown_completion=None;self.last_key=None;self.history_key=None
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint);self.setWindowTitle('Q3Q4 本地模拟器');self.resize(1000,626);self.setMinimumSize(1000,626)
        QApplication.instance().setStyle('Fusion');self.setStyleSheet(STYLE.replace('__FONT_STACK__',qt_font_stack()))
        root=QWidget();self.setCentralWidget(root);v=QVBoxLayout(root);v.setContentsMargins(0,0,0,0);v.setSpacing(0);v.addWidget(TitleBar(self))
        self.body=QWidget();self.body.setObjectName('body');v.addWidget(self.body,1);h=QHBoxLayout(self.body);h.setContentsMargins(0,0,0,0);h.setSpacing(0)
        sidebar=QWidget();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(160);side=QVBoxLayout(sidebar);side.setContentsMargins(0,0,0,0);side.setSpacing(0)
        brand=QWidget();brand.setFixedHeight(50);bh=QHBoxLayout(brand);bh.setContentsMargins(14,0,10,0);bh.setSpacing(8);bh.addWidget(image_label(28));bh.addWidget(label('环境模拟器','brand'));bh.addStretch();side.addWidget(brand)
        line=QFrame();line.setObjectName('separator');line.setFixedHeight(1);side.addWidget(line)
        self.nav=Nav(self.navigate);side.addWidget(self.nav,1)
        self.version_label=label('v'+display_version(APP_VERSION)+'  ·  本地复刻','version');self.version_label.setContentsMargins(16,0,0,0);self.version_label.setFixedHeight(32);self.version_label.setStyleSheet('border-top:1px solid #3a484a;');side.addWidget(self.version_label);h.addWidget(sidebar)
        right=QWidget();rv=QVBoxLayout(right);rv.setContentsMargins(0,0,0,0);rv.setSpacing(0);h.addWidget(right,1)
        header=QWidget();header.setObjectName('header');header.setFixedHeight(50);hh=QHBoxLayout(header);hh.setContentsMargins(20,8,20,8)
        titles=QVBoxLayout();titles.setSpacing(1);titles.addWidget(label('无线电干扰源环境模拟器','headerTitle'));titles.addWidget(label('本地仿真独立运行 · 排行榜通过 HTTPS 连接','localNote'));hh.addLayout(titles);hh.addStretch()
        wifi=label();wifi.setPixmap(icon('wifi','#267445',14).pixmap(14,14));hh.addWidget(wifi);local=label('本地运行');local.setStyleSheet('color:#267445');hh.addWidget(local)
        self.account_badge=label();self.account_badge.setStyleSheet('color:#4e5b60; border-left:1px solid #d4d9d7; padding-left:10px; margin-left:6px;');hh.addWidget(self.account_badge)
        hh.addWidget(button('',self.close,'icon',24,'exit'));rv.addWidget(header)
        self.notice,nh=box('notice',(20,0,20,0),True);self.notice.setFixedHeight(43);i=label();i.setPixmap(icon('info','#534410',15).pixmap(15,15));nh.addWidget(i);nh.addSpacing(8);self.notice_text=label(self.release_config['announcement']);nh.addWidget(self.notice_text);nh.addStretch();nh.addWidget(button('×',self.notice.hide,'icon',16));rv.addWidget(self.notice)
        self.pages=QStackedWidget();rv.addWidget(self.pages,1)
        self.groups=[];self._dashboard();self._detail();self._leaderboard_page();self._announcements();self._account();self._settings();self._help();self._about();self.apply_release_config()
        self.open_server(store.settings['port']);self.nav.setCurrentRow(0)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(100);self.refresh()
    def open_server(self,port):
        try:self.service=HTTPService(self.session,port);self.server_error=''
        except OSError as exc:self.server_error=f'端口{port}不可用：{exc}。请在设置中修改。'
    def page(self):
        p=QWidget();p.setObjectName('page');v=QVBoxLayout(p);v.setContentsMargins(20,20,20,20);v.setSpacing(0);self.pages.addWidget(p);return p,v
    def _dashboard(self):
        p,v=self.page();self.dashboard_eyebrow=label('不限次数','eyebrow');self.dashboard_eyebrow.setFixedHeight(16);v.addWidget(self.dashboard_eyebrow)
        self.dashboard_title=label('演练测试','heading');self.dashboard_title.setFixedHeight(22);v.addWidget(self.dashboard_title);self.dashboard_gap=QWidget();self.dashboard_gap.setFixedHeight(7);v.addWidget(self.dashboard_gap)
        for task in ('q3','q4'):
            panel,pv=box();head,hh=box('strip',(16,0,16,0),True);head.setFixedHeight(50)
            tv=QVBoxLayout();tv.setSpacing(2);tv.setAlignment(Qt.AlignVCenter);title=label('','sectionTitle');sub=label('','muted');title.setFixedHeight(18);sub.setFixedHeight(14);tv.addWidget(title);tv.addWidget(sub);hh.addLayout(tv);hh.addStretch();availability=label('可以开始','muted');hh.addWidget(availability);hh.addSpacing(56)
            start=button('',lambda checked=False,t=task:self.start_test(t),width=150);hh.addWidget(start);pv.addWidget(head)
            historybar,hb=box('strip',(16,0,16,0),True);historybar.setFixedHeight(27);sym=label();sym.setPixmap(icon('file',size=15).pixmap(15,15));hb.addWidget(sym);hb.addSpacing(6);histitle=label('','sectionTitle');histitle.setStyleSheet('font-size:11px;font-weight:700;');hb.addWidget(histitle);hb.addSpacing(12);history_summary=label('暂无成绩','muted');hb.addWidget(history_summary);hb.addStretch();hb.addWidget(label('可滚动查看全部','muted'));hb.addSpacing(10);hb.addWidget(button('',self.reload_history,'icon',18,'refresh'));pv.addWidget(historybar)
            table=DataTable(['提交时间','测试代码','干扰源数量','平均清除时间','清除率','局均范围','状态'],[.16,.225,.115,.14,.105,.155,.10],'暂无测试成绩')
            table.horizontalHeader().setFixedHeight(27)
            table.cellDoubleClicked.connect(lambda r,c,t=task:self.view_history(t,r));pv.addWidget(table,1)
            self.groups.append(dict(task=task,panel=panel,head=head,historybar=historybar,title=title,subtitle=sub,start=start,availability=availability,histitle=histitle,history_summary=history_summary,table=table,records=[]))
            v.addWidget(panel,1);v.addSpacing(10)
        self.formal_note=label('本地正式测试仅保存本机记录，不占用或同步官方正式测试次数。','muted');self.formal_note.setStyleSheet('color:#81702c;font-size:10px;');self.formal_note.setFixedHeight(27);v.addWidget(self.formal_note)
        self.dashboard_spacer=QWidget();v.addWidget(self.dashboard_spacer,1);self.dashboard_spacer.hide()
    def _detail(self):
        p,v=self.page();heading=QHBoxLayout();heading.setSpacing(0);self.title=label();self.title.setStyleSheet('font-size:19px;font-weight:700;');heading.addWidget(self.title);heading.addStretch();self.status_label=label('','status');heading.addWidget(self.status_label);v.addLayout(heading);v.addSpacing(7)
        self.countdown,cl=box('countdown',(16,10,16,10),True);self.countdown.setFixedHeight(62);left=QVBoxLayout();left.setSpacing(2)
        self.count_title=label('机器狗接口即将开放','countTitle');left.addWidget(self.count_title);self.count_hint=label('数据已经准备好，倒计时结束后开启25分钟测试窗口并开放接口端口。','muted');left.addWidget(self.count_hint);cl.addLayout(left);cl.addStretch();self.count_number=label('5','countNumber');cl.addWidget(self.count_number);self.count_unit=label('秒');self.count_unit.setStyleSheet('color:#21465f;font-weight:700;');cl.addWidget(self.count_unit,0,Qt.AlignBottom);v.addWidget(self.countdown)
        self.count_gap=QWidget();self.count_gap.setFixedHeight(10);v.addWidget(self.count_gap)
        panel,pv=box();v.addWidget(panel,1)
        metricbar,mh=box('panel',(16,0,16,0),True);metricbar.setFixedHeight(66);self.metrics=[]
        for caption,weight in [('测试案例编码',34),('测试窗口剩余',20),('机器狗程序剩余',22),('接口端口',10)]:
            bv=QVBoxLayout();bv.setSpacing(2);bv.setAlignment(Qt.AlignVCenter);cap=label(caption,'muted');cap.setFixedHeight(15);bv.addWidget(cap);value=label('—','case' if not self.metrics else 'metric');value.setFixedHeight(20);value.setTextInteractionFlags(Qt.TextSelectableByMouse);bv.addWidget(value);mh.addLayout(bv,weight);self.metrics.append(value)
        self.abort_button=button('中止测试',self.abort_test,'danger',94,'stop');self.return_button=button('返回演练测试',self.return_dashboard,width=96);mh.addWidget(self.abort_button);mh.addWidget(self.return_button);pv.addWidget(metricbar)
        self.summary,sh=box('truth',(16,6,16,6),True);self.summary.setFixedHeight(48);si=label();si.setPixmap(icon('radio','#204939',18).pixmap(18,18));sh.addWidget(si);sh.addSpacing(10);sv=QVBoxLayout();sv.setSpacing(1);self.summary_title=label('本次测试成绩','sectionTitle');sv.addWidget(self.summary_title);self.summary_text=label();sv.addWidget(self.summary_text);sh.addLayout(sv);sh.addStretch();pv.addWidget(self.summary)
        self.saved,self.saved_layout=box('saved',(16,5,16,5),True);self.saved.setFixedHeight(37);li=label();li.setPixmap(icon('file','#52625f',15).pixmap(15,15));self.saved_layout.addWidget(li);self.saved_layout.addSpacing(8);self.saved_title=label('详细请求记录已在后台保存，仅用于排错','muted');self.saved_layout.addWidget(self.saved_title);self.saved_layout.addStretch();pv.addWidget(self.saved)
        feedback,fl=box('strip',(16,5,16,5));feedback.setFixedHeight(43);fl.addWidget(label('指令与反馈','sectionTitle'));self.feedback_hint=label('仅显示最新1000条','muted');fl.addWidget(self.feedback_hint);pv.addWidget(feedback)
        self.actions=DataTable(['接收时间','指令','位置','频道','响应摘要','虚拟时间'],[.16,.104,.244,.104,.232,.156],'等待机器狗发出指令','radio');pv.addWidget(self.actions,1)
    def _leaderboard_page(self):
        p,v=self.page();v.setContentsMargins(20,14,20,14)
        head=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(1);titles.addWidget(label('公开评测服务','eyebrow'));titles.addWidget(label('排行榜','heading'));head.addLayout(titles);head.addStretch()
        self.leaderboard_status=label('尚未连接','offline');head.addWidget(self.leaderboard_status);head.addSpacing(8);self.leaderboard_account_button=button('登录 / 注册',self.leaderboard_account_action,'account',90,'account');head.addWidget(self.leaderboard_account_button);head.addSpacing(6);self.leaderboard_refresh_button=button('刷新',self.manual_refresh_leaderboard,width=72,ico='refresh');head.addWidget(self.leaderboard_refresh_button);v.addLayout(head);v.addSpacing(5)
        hero,hh=box('leaderHero',(10,2,10,2),True);hero.setFixedHeight(36);self.leaderboard_tabs=[]
        for task,text in [('q3','第3问（Q3）'),('q4','第4问（Q4）')]:
            tab=button(text,lambda checked=False,t=task:self.select_leaderboard_task(t),'tab',112);tab.setCheckable(True);tab.setChecked(task=='q3');self.leaderboard_tabs.append(tab);hh.addWidget(tab)
        self.my_results_tab=button('我的成绩',self.select_my_results,'tab',92);self.my_results_tab.setCheckable(True);self.my_results_tab.hide();hh.addWidget(self.my_results_tab)
        hh.addStretch();self.leaderboard_rule=label('清除率 > 89.9% · 按平均清除升序','muted');hh.addWidget(self.leaderboard_rule);hh.addSpacing(12);self.leaderboard_update=label('上次更新：—','muted');hh.addWidget(self.leaderboard_update);v.addWidget(hero);v.addSpacing(7)
        self.leaderboard_feedback=label('','muted');self.leaderboard_feedback.setWordWrap(True);self.leaderboard_feedback.setFixedHeight(22);self.leaderboard_feedback.hide();v.addWidget(self.leaderboard_feedback)
        self.leaderboard_view=QStackedWidget()
        self.leaderboard_table=DataTable(['排名','队伍','平均清除','局均最快–最慢 / 单局数量','清除率','认证','源码'],[.06,.20,.13,.22,.11,.18,.10],'暂无排行榜成绩','trophy',40)
        self.leaderboard_table.setObjectName('leaderboardTable');self.leaderboard_table.setItemDelegate(WidgetCellDelegate(self.leaderboard_table))
        self.leaderboard_table.cellClicked.connect(self.leaderboard_cell);self.leaderboard_view.addWidget(self.leaderboard_table)
        profile,pv=box('leaderPanel',(14,11,14,12));top=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(2);self.profile_title=label('我的成绩','sectionTitle');titles.addWidget(self.profile_title);self.profile_summary=label('正在获取账号数据…','muted');titles.addWidget(self.profile_summary);top.addLayout(titles);top.addStretch();self.strategy_submit_button=button('提交策略',self.open_strategy_upload,'primary',132,'code');self.strategy_submit_button.setFixedHeight(28);top.addWidget(self.strategy_submit_button);top.addSpacing(5);self.logout_button=button('退出账号',self.logout_leaderboard,width=78);self.logout_button.setFixedHeight(26);top.addWidget(self.logout_button);pv.addLayout(top);pv.addSpacing(8)
        self.submit_guide,guide=box('strip',(14,8,14,8),True);self.submit_guide.setFixedHeight(68);guide_text=QVBoxLayout();guide_text.setSpacing(2);guide_text.addWidget(label('第一次提交只需要一个 ZIP','sectionTitle'));self.submit_guide_text=label('1. ZIP 第一层放 strategy.py   2. 点击右上角“提交策略”   3. 上传后自动进入隔离评测','muted');guide_text.addWidget(self.submit_guide_text);guide.addLayout(guide_text);guide.addStretch();pv.addWidget(self.submit_guide);pv.addSpacing(8)
        self.my_submissions=DataTable(['任务','状态','平均清除','局均范围 / 单局数量','清除率','排名','提交时间','操作'],[.06,.14,.12,.19,.10,.07,.19,.13],'尚无提交；点击上方“提交策略”开始评测','file',30);self.my_submissions.horizontalHeader().setFixedHeight(30);pv.addWidget(self.my_submissions,1);self.leaderboard_view.addWidget(profile);v.addWidget(self.leaderboard_view,1)
    def set_leaderboard_connection(self,online,text):
        self.leaderboard_status.setObjectName('online' if online else 'offline');self.leaderboard_status.setText(('●  ' if online else '○  ')+text);self.leaderboard_status.style().unpolish(self.leaderboard_status);self.leaderboard_status.style().polish(self.leaderboard_status)
    def set_leaderboard_feedback(self,text='',error=False,kind=None):
        self.leaderboard_error_kind=kind if text else None;self.leaderboard_feedback.setText(text);self.leaderboard_feedback.setVisible(bool(text));self.leaderboard_feedback.setStyleSheet('color:#9a2d2d;font-size:10px;' if error else 'color:#4e5b60;font-size:10px;')
    def clear_leaderboard_login(self):
        if self.strategy_upload_dialog:self.strategy_upload_dialog.close()
        self.leaderboard_user=None;self.personal_identity_pending=False;self.my_results_tab.hide();self.my_results_tab.setChecked(False);self.leaderboard_account_button.setText('登录 / 注册');self.leaderboard_view.setCurrentIndex(0)
    def show_remote_error(self,error):
        kind=getattr(error,'kind','request');message=str(error)
        if kind=='auth':
            self.clear_leaderboard_login();self.set_leaderboard_connection(True,'HTTPS 在线')
        elif kind=='service_unavailable':self.set_leaderboard_connection(False,'服务暂时不可用')
        else:self.set_leaderboard_connection(True,'HTTPS 在线')
        self.set_leaderboard_feedback(message,True,kind)
    def select_leaderboard_task(self,task):
        self.leaderboard_task=task;self.leaderboard_view.setCurrentIndex(0);self.my_results_tab.setChecked(False)
        for i,tab in enumerate(self.leaderboard_tabs):tab.setChecked(i==(0 if task=='q3' else 1))
        self.refresh_leaderboard(False,False)
    def select_my_results(self):
        if not self.leaderboard_user:self.open_leaderboard_auth();return
        for tab in self.leaderboard_tabs:tab.setChecked(False)
        self.my_results_tab.setChecked(True);self.leaderboard_view.setCurrentIndex(1);self.remote.call('dashboard',self.receive_leaderboard_dashboard)
    def refresh_leaderboard(self,include_session=True,force=False):
        task=self.leaderboard_task;cached=self.leaderboard_cache.get(task)
        if cached and not force:
            fetched_mono,fetched_at,rows=cached;self.render_leaderboard(task,rows,fetched_at,True)
            if monotonic()-fetched_mono<LEADERBOARD_CACHE_TTL_S:
                if include_session:
                    self.leaderboard_bootstrapped=True
                    self.remote.call('session',self.receive_leaderboard_session);self.remote.call('metadata',self.receive_release_metadata)
                return
        self.leaderboard_refresh_button.setEnabled(False);self.set_leaderboard_connection(False,'正在连接')
        self.remote.call('leaderboard',lambda data,error,t=task:self.receive_leaderboard(t,data,error),task)
        if include_session:
            self.leaderboard_bootstrapped=True
            self.remote.call('session',self.receive_leaderboard_session);self.remote.call('metadata',self.receive_release_metadata)
    def manual_refresh_leaderboard(self):
        if self.leaderboard_view.currentIndex()==1 and self.leaderboard_user:self.remote.call('dashboard',self.receive_leaderboard_dashboard)
        else:self.refresh_leaderboard(False,True)
    def receive_leaderboard(self,task,data,error):
        self.leaderboard_refresh_button.setEnabled(True)
        if error:
            if task==self.leaderboard_task:self.show_remote_error(error)
            return
        fetched_at=datetime.now();rows=list(data);self.leaderboard_cache[task]=(monotonic(),fetched_at,rows)
        if task!=self.leaderboard_task:return
        self.render_leaderboard(task,rows,fetched_at,False)
    def render_leaderboard(self,task,rows,fetched_at,cached=False):
        if task!=self.leaderboard_task:return
        self.set_leaderboard_connection(True,'HTTPS 在线')
        if cached:self.set_leaderboard_connection(True,'本地缓存')
        if self.leaderboard_error_kind!='auth':self.set_leaderboard_feedback()
        self.leaderboard_rows=list(rows);self.leaderboard_update.setText('上次更新：'+fetched_at.strftime('%H:%M:%S'));self.leaderboard_table.set_empty_text('暂无排行榜成绩')
        values=[]
        for row in self.leaderboard_rows:
            open_source=row.get('open_source_status')=='OPEN_SOURCE_VERIFIED';badge='✦ OPEN SOURCE VERIFIED' if open_source else '✓ VERIFIED'
            values.append([row['rank'],row['team_name'],score(row.get('mean_clear_time_s')),scene_spread(row),percent(row.get('clear_rate')),badge,'查看源码' if open_source else '—'])
        for existing_row in range(self.leaderboard_table.rowCount()):
            for column in (0,1,5,6):self.leaderboard_table.removeCellWidget(existing_row,column)
        self.leaderboard_table.rows(values)
        for index,row in enumerate(self.leaderboard_rows):
            eligible=row.get('ranking_eligible',row.get('clear_rate',0)>.899)
            open_source=row.get('open_source_status')=='OPEN_SOURCE_VERIFIED'
            for column in (2,3,4):
                item=self.leaderboard_table.item(index,column);font=QFontDatabase.systemFont(QFontDatabase.FixedFont);font.setPointSize(item.font().pointSize());font.setBold(True);item.setFont(font)
            rank_item=self.leaderboard_table.item(index,0);rank_item.setTextAlignment(Qt.AlignCenter)
            if eligible and row['rank']<=3:
                rich_cell(self.leaderboard_table,index,0,RankBadge(row['rank']))
            if eligible and open_source:
                left_rich_cell(self.leaderboard_table,index,1,OpenSourceTeamName(row['team_name']))
                rich_cell(self.leaderboard_table,index,5,OpenSourceBadge())
                source=SourceButton(lambda checked=False,i=index,sid=row['id']:self.open_source_from_row(i,sid))
                rich_cell(self.leaderboard_table,index,6,source,True)
            elif eligible:
                verified=self.leaderboard_table.item(index,5);verified.setForeground(QColor('#52625f'));font=verified.font();font.setBold(True);verified.setFont(font)
                rich_cell(self.leaderboard_table,index,5,VerifiedBadge())
            if not eligible:
                self.leaderboard_table.item(index,5).setText('未达门槛 · '+badge)
                for column in range(self.leaderboard_table.columnCount()):self.leaderboard_table.item(index,column).setForeground(QColor('#7f8984'))
    def receive_leaderboard_session(self,data,error):
        if error:self.show_remote_error(error);return
        self.leaderboard_user=data.get('user')
        if self.leaderboard_user:
            self.my_results_tab.show();self.leaderboard_account_button.setText(self.leaderboard_user['username']);self.profile_title.setText(self.leaderboard_user['username']+' · 我的成绩');self.remote.call('dashboard',self.receive_leaderboard_dashboard)
        else:
            self.my_results_tab.hide();self.my_results_tab.setChecked(False);self.leaderboard_account_button.setText('登录 / 注册')
            if self.leaderboard_view.currentIndex()==1:self.select_leaderboard_task(self.leaderboard_task)
    def receive_leaderboard_dashboard(self,data,error):
        if error:self.show_remote_error(error);return
        self.set_leaderboard_feedback();teams=data['teams'];submissions=data['submissions'];self.leaderboard_teams=list(teams);self.leaderboard_submissions=list(submissions);self.strategy_submit_button.setEnabled(True);names='、'.join(t['team_name'] for t in teams);ranks=[f"{r['task'].upper()} #{r['rank']}" for r in submissions if r.get('rank')]
        if not teams:self.profile_summary.setText('还没有提交策略 · 首次提交时将自动使用用户名作为参赛名')
        else:self.profile_summary.setText('参赛名：'+names+'  ·  '+(' / '.join(ranks[:3]) if ranks else '尚未上榜'))
        self.submit_guide.setVisible(not submissions)
        values=[]
        for row in submissions:
            status={'AWAITING_SOURCE':'等待上传源码','QUEUED':'QUEUED · 排队中','RUNNING':'RUNNING · 评测中','VERIFYING':'认证中','VERIFIED':'✓ VERIFIED','FAILED':'FAILED · 评测失败','TIMEOUT':'TIMEOUT · 超时','INTERRUPTED':'评测中断'}.get(row.get('status'),row.get('status','—'))
            if row.get('open_source_status')=='OPEN_SOURCE_VERIFIED':status='✦ OPEN SOURCE VERIFIED'
            values.append([row['task'].upper(),status,score(row.get('mean_clear_time_s')),scene_spread(row),percent(row.get('clear_rate')),'#'+str(row['rank']) if row.get('rank') else '—',local_time(row.get('created_at')),'查看分析' if row.get('source_sha256') else '—'])
        for existing_row in range(self.my_submissions.rowCount()):self.my_submissions.removeCellWidget(existing_row,7)
        self.my_submissions.rows(values)
        for index,row in enumerate(submissions):
            if row.get('source_sha256'):
                rich_cell(self.my_submissions,index,7,SourceButton(lambda checked=False,sid=row['id']:self.open_owner_source(sid),'查看分析'),True)
    def open_strategy_upload(self):
        if not self.leaderboard_user:self.open_leaderboard_auth();return
        if self.strategy_upload_dialog:self.strategy_upload_dialog.raise_();return
        if not self.leaderboard_teams:
            if self.personal_identity_pending:return
            self.personal_identity_pending=True;self.strategy_submit_button.setEnabled(False);self.profile_summary.setText('正在用用户名建立个人参赛身份…')
            self.remote.call('create_personal_team',self.finish_personal_identity,self.leaderboard_user['username']);return
        self.strategy_upload_dialog=StrategyUpload(self.body,self.leaderboard_teams,self.submit_strategy,lambda:setattr(self,'strategy_upload_dialog',None))
    def finish_personal_identity(self,data,error):
        self.personal_identity_pending=False;self.strategy_submit_button.setEnabled(True)
        if error:
            self.profile_summary.setText('个人参赛身份尚未建立');self.show_remote_error(error);return
        self.leaderboard_teams=[data];self.profile_summary.setText('参赛名：'+data['team_name']+' · 尚未上榜');self.open_strategy_upload()
    def submit_strategy(self,team_id,task,path,entrypoint,dependencies,description,open_source,consent):
        try:
            with ZipFile(path) as archive:
                name=next((n for n in archive.namelist() if n.casefold()=='readme.md'),None)
                readme=archive.read(name).decode('utf-8') if name else f'# {Path(path).stem}\n\nEntrypoint: `{entrypoint}`'
        except (BadZipFile,UnicodeError,KeyError,OSError):
            self.strategy_upload_dialog.set_error('ZIP 无法读取，或 README.md 不是 UTF-8 文本。');return
        self.remote.call('submit_strategy',self.finish_strategy_upload,team_id,task,path,entrypoint,dependencies,readme,description,open_source,consent)
    def finish_strategy_upload(self,data,error):
        if error:
            if self.strategy_upload_dialog:self.strategy_upload_dialog.set_error(str(error))
            return
        if self.strategy_upload_dialog:self.strategy_upload_dialog.close()
        self.set_leaderboard_feedback('策略已上传并进入 Docker 评测队列。');self.select_my_results()
    def leaderboard_account_action(self):
        self.select_my_results() if self.leaderboard_user else self.open_leaderboard_auth()
    def open_leaderboard_auth(self):
        if self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.raise_();return
        self.leaderboard_auth_dialog=LeaderboardAuth(self.body,self.authenticate_leaderboard,lambda:setattr(self,'leaderboard_auth_dialog',None))
    def authenticate_leaderboard(self,method,username,password):
        self.remote.call(method,lambda data,error:self.finish_leaderboard_auth(data,error),username,password)
    def finish_leaderboard_auth(self,data,error):
        if error:
            if self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.set_error(str(error))
            if getattr(error,'kind',None)=='service_unavailable':self.show_remote_error(error)
            return
        if self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.close()
        self.leaderboard_user=data['user'];self.my_results_tab.show();self.leaderboard_account_button.setText(self.leaderboard_user['username']);self.profile_title.setText(self.leaderboard_user['username']+' · 我的成绩');self.set_leaderboard_connection(True,'HTTPS 在线');self.set_leaderboard_feedback();self.select_my_results()
    def logout_leaderboard(self):
        self.logout_button.setEnabled(False);self.remote.call('logout',self.finish_leaderboard_logout)
    def finish_leaderboard_logout(self,data,error):
        self.logout_button.setEnabled(True)
        if error:self.show_remote_error(error);return
        self.clear_leaderboard_login();self.select_leaderboard_task(self.leaderboard_task)
    def leaderboard_cell(self,row,column):
        if column!=6 or not 0<=row<len(self.leaderboard_rows):return
        item=self.leaderboard_rows[row]
        if item.get('open_source_status')=='OPEN_SOURCE_VERIFIED':self.open_leaderboard_source(item['id'])
    def open_source_from_row(self,row,submission_id):
        self.leaderboard_table.selectRow(row);self.open_leaderboard_source(submission_id)
    def open_leaderboard_source(self,submission_id):
        self.show_source_viewer(submission_id,False)
    def open_owner_source(self,submission_id):
        self.show_source_viewer(submission_id,True)
    def show_source_viewer(self,submission_id,owner):
        if self.source_viewer:self.source_viewer.close()
        self.source_viewer_owner=owner;self.source_viewer=SourceViewer(self.body,self.close_source_viewer);self.source_viewer.fileRequested.connect(lambda path,sid=submission_id:self.load_source_file(sid,path));self.remote.call('owner_code' if owner else 'code',self.receive_source,submission_id)
    def close_source_viewer(self):self.source_viewer=None;self.source_viewer_owner=False
    def receive_source(self,data,error):
        if not self.source_viewer:return
        if error:self.source_viewer.set_error(str(error));return
        self.source_viewer.set_metadata(data)
    def load_source_file(self,submission_id,path):
        self.remote.call('owner_code_file' if self.source_viewer_owner else 'code_file',lambda data,error,p=path:self.receive_source_file(p,data,error),submission_id,path)
    def receive_source_file(self,path,data,error):
        if self.source_viewer:self.source_viewer.set_file(path,str(error) if error else data)
    def receive_release_metadata(self,data,error):
        if error or not isinstance(data,dict):return
        for key in self.release_config:
            if isinstance(data.get(key),str):self.release_config[key]=data[key]
        self.apply_release_config()
    def apply_release_config(self):
        cfg=self.release_config;current=cfg['current_version'] or APP_VERSION;latest=cfg['latest_version'] or current
        self.version_label.setText('v'+display_version(current)+'  ·  本地复刻');self.notice_text.setText(cfg['announcement'] or '暂无新公告。')
        self.announcement_text.setText(cfg['announcement'] or '暂无新公告。');self.release_versions.setText(f'当前版本 {current}  ·  最新版本 {latest}')
        self.release_notes.setText(cfg['release_notes'] or '暂无版本说明。');self.about_version.setText(f'当前版本 {current} · 最新版本 {latest} · Mac / Windows 共用界面')
        for key,button_ in (('mac_download_url',self.mac_download),('windows_download_url',self.windows_download),('feedback_url',self.feedback_button)):
            available=bool(cfg[key]);button_.setEnabled(available)
            button_.setText({'mac_download_url':'下载 macOS','windows_download_url':'下载 Windows','feedback_url':'意见反馈'}[key] if available else '即将开放')
    def open_release_url(self,key):
        url=self.release_config.get(key,'')
        if url:QDesktopServices.openUrl(QUrl(url))
    def _announcements(self):
        p,v=self.page();v.addWidget(label('系统通知','eyebrow'));v.addWidget(label('公告','heading'));v.addSpacing(17)
        card,cv=box('panel',(16,14,16,14));cv.addWidget(label('♧  最新公告','sectionTitle'));cv.addSpacing(6);self.announcement_text=label();self.announcement_text.setWordWrap(True);cv.addWidget(self.announcement_text);v.addWidget(card);v.addSpacing(10)
        release,rv=box('panel',(16,14,16,14));rv.addWidget(label('版本与下载','sectionTitle'));self.release_versions=label('','muted');rv.addWidget(self.release_versions);rv.addSpacing(6);self.release_notes=label();self.release_notes.setWordWrap(True);rv.addWidget(self.release_notes);rv.addSpacing(10)
        actions=QHBoxLayout();self.mac_download=button('即将开放',lambda:self.open_release_url('mac_download_url'),width=112);self.windows_download=button('即将开放',lambda:self.open_release_url('windows_download_url'),width=112);self.feedback_button=button('即将开放',lambda:self.open_release_url('feedback_url'),width=96);actions.addWidget(self.mac_download);actions.addWidget(self.windows_download);actions.addStretch();actions.addWidget(self.feedback_button);rv.addLayout(actions);v.addWidget(release);v.addStretch()
    def _account(self):
        p,v=self.page();v.addWidget(label('身份信息','eyebrow'));v.addWidget(label('账号','heading'));v.addSpacing(17)
        card,cv=box('panel',(16,16,16,16));cv.addWidget(label('修改密码','sectionTitle'));hint=label('本地模式不验证参赛身份，密码修改不可用；可保存客户端原有标识。','muted');cv.addWidget(hint);cv.addSpacing(16)
        grid=QGridLayout();grid.setContentsMargins(0,0,0,0);grid.setHorizontalSpacing(10);grid.setVerticalSpacing(4);self.robot_edit=QLineEdit(self.store.settings['robot_id']);self.account_fields=[self.robot_edit]
        for col,title in enumerate(('参赛队号','队员1姓名','队员1手机号')):
            field_label=label(title);field_label.setStyleSheet('font-size:11px;font-weight:600;');grid.addWidget(field_label,0,col);edit=self.robot_edit if col==0 else QLineEdit()
            if col:edit.setEnabled(False);self.account_fields.append(edit)
            grid.addWidget(edit,1,col)
        grid.setRowMinimumHeight(2,28)
        for col,title in enumerate(('原密码','新密码','确认新密码')):
            field_label=label(title);field_label.setStyleSheet('font-size:11px;font-weight:600;');grid.addWidget(field_label,3,col);edit=QLineEdit();edit.setEchoMode(QLineEdit.Password);edit.addAction(icon('eye',size=14),QLineEdit.TrailingPosition);edit.setEnabled(False);grid.addWidget(edit,4,col)
        help_=label('密码须为12至64个字符，同时包含字母和数字；\n本地版不向官方服务器验证或提交密码。','muted');help_.setWordWrap(True);grid.addWidget(help_,5,1)
        cv.addLayout(grid);cv.addSpacing(16);end=QHBoxLayout();end.addStretch();self.account_save=button('保存本地标识',self.save_identity,'primary',100);end.addWidget(self.account_save);cv.addLayout(end);v.addWidget(card);v.addStretch()
    def _settings(self):
        p,v=self.page();v.addWidget(label('本机配置','eyebrow'));v.addWidget(label('设置','heading'));v.addSpacing(17)
        panel,pv=box();v.addWidget(panel)
        self.port_edit=QSpinBox();self.port_edit.setRange(1024,65535);self.port_edit.setValue(self.store.settings['port']);self.port_edit.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.rows_edit=QSpinBox();self.rows_edit.setRange(100,5000);self.rows_edit.setValue(self.store.settings['display_rows'])
        for name,edit in [('机器狗接口端口',self.port_edit),('指令与反馈显示条数',self.rows_edit)]:
            row,rh=box('strip',(16,12,16,12),True);row.setFixedHeight(106);left=QVBoxLayout();left.setSpacing(4);left.addWidget(label(name,'sectionTitle'));edit.setFixedWidth(252);edit.setFixedHeight(30);left.addWidget(edit)
            desc=label('','muted');left.addWidget(desc);rh.addLayout(left);rh.addStretch();save=button('保存',self.save_settings,width=82);rh.addWidget(save,0,Qt.AlignVCenter);pv.addWidget(row)
            if edit is self.port_edit:self.port_note=desc;self.save_button=save
            else:self.rows_note=desc;self.rows_save=save
        self.settings_message=label('','muted');v.addWidget(self.settings_message);v.addStretch()
    def _help(self):
        p,v=self.page();v.addWidget(label('使用说明','eyebrow'));v.addWidget(label('帮助 / 排行榜规则','heading'));v.addSpacing(12)
        sections=[
            ('本地模拟器','Q3 / Q4 本地测试监听 127.0.0.1:2026。机器狗依次使用 /enter、/measure、/clear、/exit；移动和频道切换由请求自动处理。本地测试不依赖排行榜服务器。'),
            ('排行榜','清除率严格大于 89.9% 才进入达标组，达标后按平均清除时间升序。多局先算每局平均清除时间，再对各局等权平均，并展示局均最快–最慢；不使用总时间排名。'),
            ('策略 ZIP','ZIP 第一层直接放 strategy.py，文件中提供 def run(api)。选择 Q3/Q4 和运行依赖后直接提交，服务器会自动检查并进入 Docker 评测。'),
            ('Open Source Verified','用户主动上传源码后，平台在隔离环境中重新运行。通过后显示 OPEN SOURCE VERIFIED，README、策略说明和认证源码可以公开查看；普通 VERIFIED 不公开源码。'),
        ]
        for title,text in sections:
            card,cv=box('panel',(16,12,16,12));cv.addWidget(label(title,'sectionTitle'));cv.addSpacing(5);body=label(text,'muted');body.setWordWrap(True);cv.addWidget(body);v.addWidget(card);v.addSpacing(9)
        v.addStretch()
    def _about(self):
        p,v=self.page();v.addWidget(label('环境模拟器','eyebrow'));v.addWidget(label('关于','heading'));v.addSpacing(17)
        panel,h=box('panel',(16,16,16,16),True);h.addWidget(image_label(48));h.addSpacing(12);bv=QVBoxLayout();bv.setSpacing(3);bv.addWidget(label('无线电干扰源环境模拟器','sectionTitle'));self.about_version=label('','muted');bv.addWidget(self.about_version);bv.addWidget(label('核心 Q3_Q4_LOCAL_SIMULATOR_V1','muted'));h.addLayout(bv);h.addStretch();v.addWidget(panel);v.addStretch()
    def navigate(self,index):
        if not hasattr(self,'pages'):return
        self.detail=False
        if index<3:self.current_task='q4' if index==2 else 'q3';self.current_mode='practice' if index==0 else 'formal';self.pages.setCurrentIndex(0)
        else:self.pages.setCurrentIndex(index-1)
        self.history_key=None
        if index==3:self.refresh_leaderboard(not self.leaderboard_bootstrapped,False)
        if hasattr(self,'settings_message'):self.refresh()
    def selection(self):return self.current_task,self.current_mode
    def dialog(self,title,text,confirm='确认',cancel=None,callback=None):
        if self.modal:self.modal.hide();self.modal.deleteLater()
        def done(ok):self.modal=None;callback(ok) if callback else None
        self.modal=Modal(self.body,title,text,confirm,cancel,done);return self.modal
    def start_test(self,task=None):
        if self.session.state in ACTIVE:
            row=self.session.row
            if row and row['task']==(task or self.current_task) and row['mode']==self.current_mode:
                self.detail=True;self.pages.setCurrentIndex(1);self.refresh()
            return
        if task:self.current_task=task
        if self.current_mode=='formal':
            n=self.current_task[-1]
            self.dialog('开始正式测试',f'即将开始问题{n}的本地正式测试，是否继续？','继续','取消',lambda ok:self.dialog('再次确认开始',f'启动成功后将记录一次问题{n}的本地正式测试。确定开始吗？','确认开始','取消',lambda yes:self.begin() if yes else None) if ok else None)
        else:self.begin()
    def begin(self):
        self.detail=True;self.pages.setCurrentIndex(1);self.session.start(self.current_task,self.current_mode);self.last_key=None;self.refresh()
    def abort_test(self):
        self.dialog('中止测试','确定要中止当前测试吗？','继续','取消',lambda ok:self.dialog('再次确认中止','中止后本次测试不能继续，行为日志将保留。确定中止吗？','中止测试','取消',lambda yes:self.do_abort() if yes else None) if ok else None)
    def do_abort(self):self.session.abort();self.refresh()
    def return_dashboard(self):self.detail=False;self.pages.setCurrentIndex(0);self.history_key=None;self.refresh()
    def save_identity(self):
        if self.session.state in ACTIVE:return
        value=self.robot_edit.text()
        if not identifier(value,64):self.dialog('标识格式不正确','本地标识需为1至64个UTF-8字节，不能含控制或不可见格式字符。');return
        self.store.save_settings({**self.store.settings,'robot_id':value});self.refresh();self.dialog('保存成功','本地机器狗标识已保存。')
    def save_settings(self):
        if self.session.state in ACTIVE:return
        port=self.port_edit.value()
        if self.service is None or port!=self.service.port:
            try:new=HTTPService(self.session,port)
            except OSError as exc:self.settings_message.setText(f'无法使用端口{port}：{exc}');return
            if self.service:self.service.close()
            self.service=new;self.server_error=''
        self.store.save_settings({**self.store.settings,'port':port,'display_rows':self.rows_edit.value()});self.session.events=deque(self.session.events,maxlen=self.rows_edit.value());self.settings_message.setText('设置已保存。');self.refresh()
    def reload_history(self):self.history_key=None;self.refresh()
    def log_size(self,row):
        p=self.store.root/'logs'/(row['case_id']+'.jsonl');return f'{p.stat().st_size/1024:.1f} KiB' if p.exists() else '—'
    def view_history(self,task,index):
        group=next(g for g in self.groups if g['task']==task)
        if not 0<=index<len(group['records']):return
        row=group['records'][index]
        self.dialog('测试成绩',f"测试案例编码：{row['case_id']}\n{LABELS[row['state']]}\n{local_result_text(row,row.get('mode')=='practice')}\n详细请求记录仅在后台用于排错。")
    def export(self,row):
        source=self.store.root/'logs'/(row['case_id']+'.jsonl')
        target,_=QFileDialog.getSaveFileName(self,'导出行为日志',str(Path.home()/source.name),'JSONL (*.jsonl)',options=QFileDialog.DontUseNativeDialog)
        if target:shutil.copyfile(source,target)
    def refresh(self):
        s=self.session.snapshot();state=s['state'];row=s['row'];task,mode=self.selection();active=state in ACTIVE
        self.account_badge.setText('队号 '+self.store.settings['robot_id']);self.port_note.setText(self.server_error or f"端口{self.service.port if self.service else self.store.settings['port']}已保留")
        self.rows_note.setText('可设置100至5000条，默认1000条。仅影响界面显示，不影响请求处理和完整行为日志。')
        self.save_button.setEnabled(not active);self.rows_save.setEnabled(not active);self.account_save.setEnabled(not active);self.port_edit.setEnabled(not active);self.rows_edit.setEnabled(not active);self.robot_edit.setEnabled(not active)
        self.dashboard_eyebrow.setText('不限次数' if mode=='practice' else '正式测试');self.dashboard_title.setText('演练测试' if mode=='practice' else f'问题{task[-1]}正式测试')
        self.dashboard_gap.setFixedHeight(7 if mode=='practice' else 16);self.formal_note.setVisible(mode=='formal');self.dashboard_spacer.setVisible(mode=='formal')
        key=(mode,task,state,row['case_id'] if row else None)
        if key!=self.history_key:
            records=self.store.history()
            for g in self.groups:
                visible=mode=='practice' or task==g['task'];g['panel'].setVisible(visible)
                g['panel'].setMinimumHeight(204 if mode=='practice' else 259);g['panel'].setMaximumHeight(204 if mode=='practice' else 259)
                g['head'].setFixedHeight(50 if mode=='practice' else 60);g['historybar'].setFixedHeight(27 if mode=='practice' else 34);g['table'].horizontalHeader().setFixedHeight(27 if mode=='practice' else 32)
                n=g['task'][-1];name=f"问题{n}{'演练' if mode=='practice' else '正式'}测试"
                g['title'].setText(name);g['start'].setText('开始'+name);g['start'].setProperty('role','primary' if mode=='formal' else 'normal');g['start'].style().unpolish(g['start']);g['start'].style().polish(g['start'])
                g['records']=[r for r in records if r['task']==g['task'] and r['mode']==mode]
                g['subtitle'].setText(('全向干扰源场景' if n=='3' else '包含定向干扰源的场景') if mode=='practice' else f"已用{len(g['records'])}次，本地次数记录")
                g['histitle'].setText(name+'成绩记录')
                g['history_summary'].setText(local_history_summary(g['records']))
                headers=['提交时间','测试代码','干扰源数量','平均清除时间','清除率','局均范围','状态']
                g['table'].setHorizontalHeaderLabels(headers);g['table'].fractions=[.16,.225,.115,.14,.105,.155,.10]
                rows=[]
                for i,r in enumerate(g['records']):
                    when=lambda k:datetime.fromtimestamp(r[k]/1000).strftime('%m/%d %H:%M:%S') if r.get(k) else '—'
                    metrics=local_metrics(r)
                    rows.append([when('created_ms'),short_test_code(r['case_id']),f"{metrics['target_count']} 个" if metrics.get('target_count') is not None else '—',score(metrics.get('mean_clear_time_s')),percent(metrics.get('clear_rate')),local_mean_range(metrics),LABELS[r['state']]])
                g['table'].rows(rows)
                for i,r in enumerate(g['records']):g['table'].item(i,1).setToolTip(r['case_id'])
            self.history_key=key
        for g in self.groups:
            ongoing=active and row and row['task']==g['task'] and row['mode']==mode
            if ongoing:g['start'].setText('返回当前测试')
            g['start'].setEnabled((ongoing or not active) and self.service is not None and self.modal is None)
            g['availability'].setText('测试进行中' if active else '可以开始')
        if row:
            rt=row['task'];rm=row['mode'];color='#13745e' if rm=='practice' else '#8a6325'
            self.title.setText(f'<span style="color:#285d90">问题{rt[-1]}</span> <span style="color:{color}">{"演练" if rm=="practice" else "正式"}</span> 测试')
            self.status_label.setText('●  '+LABELS[state]);self.countdown.setVisible(state in ('PREPARING','COUNTDOWN'));self.count_gap.setVisible(state in ('PREPARING','COUNTDOWN'))
            self.count_title.setText('正在准备测试数据' if state=='PREPARING' else '机器狗接口即将开放');self.count_number.setText('…' if state=='PREPARING' else str(s['countdown'] or 0));self.count_unit.setVisible(state=='COUNTDOWN')
            self.count_hint.setText('正在准备本次测试数据，请稍候。' if state=='PREPARING' else '数据已经准备好，倒计时结束后开启25分钟测试窗口并开放接口端口。')
            self.metrics[0].setText(row['case_id']);self.metrics[1].setText(duration(s['window_remaining']) if s['window_remaining'] is not None else '25:00');self.metrics[2].setText(duration(s['program_remaining']));self.metrics[3].setText(str(self.service.port if self.service else self.store.settings['port']))
            self.abort_button.setVisible(active);self.abort_button.setEnabled(active);self.return_button.setVisible(state in TERMINAL);self.return_button.setText('返回演练测试' if rm=='practice' else '返回正式测试')
            has_result=state in TERMINAL and bool(local_metrics(row));self.summary.setVisible(has_result)
            if has_result:self.summary_text.setText(local_result_text(row,rm=='practice'))
            self.saved.setVisible(state in TERMINAL);self.feedback_hint.setText(f"仅显示最新{self.store.settings['display_rows']}条")
            events=s['events'];event_key=(row['case_id'],len(events),events[-1] if events else None)
            if event_key!=self.last_key:
                values=[]
                for event in events:
                    res=event['response'];p=event['position'];path=event['path'];summary='未执行'
                    if res['accepted']:
                        if path=='/enter':summary='进入成功'
                        elif path=='/exit':summary='正常退出'
                        elif path=='/clear':summary='已清除' if res.get('clear_result')=='success' else '范围内无目标'
                        else:summary=f"示向度 {res['svd_deg']:.2f}°" if 'svd_deg' in res else '距离过近' if res.get('measure_result')=='near' else '未测得信号'
                    if event['status']!=200:summary=f"HTTP {event['status']} · "+summary
                    if event['replay']:summary+='（重试）'
                    pos=f"({p['x']:.2f}, {p['y']:.2f})" if isinstance(p,dict) and all(type(p.get(k)) in (int,float) for k in ('x','y')) else '--'
                    values.append([datetime.fromtimestamp(event['received_ms']/1000).strftime('%H:%M:%S'),{'/enter':'进入','/measure':'测量','/clear':'清除','/exit':'退出'}.get(path,path),pos,event['channel'] if event['channel'] is not None else '--',summary,f"{res['virtual_time_s']:.3f} s"])
                self.actions.fractions=[.16,.104,.244,.104,.232,.156] if values else [.20,.13,.13,.13,.20,.21];self.actions.rows(values);self.last_key=event_key
            if state in TERMINAL and self.shown_completion!=row['case_id']:
                self.shown_completion=row['case_id'];name=f"问题{rt[-1]}{'演练' if rm=='practice' else '正式'}测试"
                text=f"{name}：{REASONS.get(row['reason'],row['reason'])}，测试已结束。\n{local_result_text(row,rm=='practice')}\n本次成绩已记录。"
                self.dialog(name+('完成' if state=='FINISHED' else '已中止' if state=='ABORTED' else '超时退出'),text)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'modal') and self.modal:self.modal.setGeometry(self.body.rect())
        if hasattr(self,'source_viewer') and self.source_viewer:self.source_viewer.setGeometry(self.body.rect())
        if hasattr(self,'leaderboard_auth_dialog') and self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.setGeometry(self.body.rect())
        if hasattr(self,'strategy_upload_dialog') and self.strategy_upload_dialog:self.strategy_upload_dialog.setGeometry(self.body.rect())
    def closeEvent(self,event):
        if self.session.state in ACTIVE:
            event.ignore();self.dialog('退出模拟器','退出将中止本次测试。是否继续？','继续','取消',lambda ok:self.dialog('再次确认退出','确认中止本次测试并退出模拟器？','退出','取消',lambda yes:self.close_confirmed() if yes else None) if ok else None);return
        self.timer.stop()
        if self.strategy_upload_dialog:self.strategy_upload_dialog.close()
        if self.source_viewer:self.source_viewer.close()
        if self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.close()
        if self.service:self.service.close();self.service=None
        if hasattr(self.remote,'close'):self.remote.close()
        event.accept()
    def close_confirmed(self):self.session.abort('app_closed');self.close()
