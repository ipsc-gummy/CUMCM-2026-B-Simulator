"""Video-grounded Windows-style Qt presentation. No core/HTTP/time implementation."""
from pathlib import Path
from datetime import datetime
from collections import deque
import json
import shutil
from PySide6.QtCore import Qt, QTimer, QUrl, QByteArray, QSize, Signal
from PySide6.QtGui import QDesktopServices, QPixmap, QPainter, QIcon, QColor, QBrush, QLinearGradient
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QPushButton,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QFrame,
    QLineEdit,QSpinBox,QAbstractSpinBox,QSizePolicy,QFileDialog,QGraphicsDropShadowEffect,
    QPlainTextEdit,QListWidget)
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
QLineEdit,QSpinBox { background:#fcfdfc; border:1px solid #b9c1c3; border-radius:3px; padding:6px 9px; min-height:17px; }
QLineEdit:disabled { color:#84918d; background:#f8faf9; }
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
QLabel#osbadge { color:#6d3bb5; background:#f4edff; border:1px solid #d7c2f0; border-radius:3px; padding:3px 7px; font-size:9px; font-weight:700; }
QPlainTextEdit#sourceCode { background:#14201f; color:#dce9e5; border:0; padding:10px; font-family:Menlo,Consolas,monospace; font-size:10px; }
QListWidget#sourceTree { background:#f5f8f6; border:0; border-right:1px solid #d7dfdb; font-size:10px; padding:4px; }
QListWidget#sourceTree::item { padding:6px; }
QListWidget#sourceTree::item:selected { background:#dfeee8; color:#123e32; }
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

class SourceViewer(QWidget):
    fileRequested = Signal(str)
    def __init__(self,parent,close):
        super().__init__(parent);self.close_callback=close;self.metadata=None
        self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground);self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,145); }')
        self.setGeometry(parent.rect());outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch()
        row=QHBoxLayout();row.addStretch();self.card,v=box('dialog');self.card.setFixedSize(760,500)
        top=QWidget();th=QHBoxLayout(top);th.setContentsMargins(18,12,12,10);th.setSpacing(8)
        titles=QVBoxLayout();titles.setSpacing(2);self.team=label('正在读取公开源码…','heading');titles.addWidget(self.team);self.meta=label('通过 HTTPS 从排行榜获取','muted');titles.addWidget(self.meta);th.addLayout(titles);th.addStretch();self.badge=label('✦ OPEN SOURCE VERIFIED','osbadge');th.addWidget(self.badge);th.addWidget(button('×',self.close,'icon',24));v.addWidget(top)
        line=QFrame();line.setObjectName('separator');line.setStyleSheet('background:#d7dfdb');line.setFixedHeight(1);v.addWidget(line)
        content=QWidget();ch=QHBoxLayout(content);ch.setContentsMargins(0,0,0,0);ch.setSpacing(0)
        self.tree=QListWidget();self.tree.setObjectName('sourceTree');self.tree.setFixedWidth(170);self.tree.currentTextChanged.connect(self.select_file);ch.addWidget(self.tree)
        right=QWidget();rv=QVBoxLayout(right);rv.setContentsMargins(0,0,0,0);rv.setSpacing(0);self.details=label('','muted');self.details.setContentsMargins(12,8,12,8);self.details.setFixedHeight(48);self.details.setWordWrap(True);rv.addWidget(self.details)
        self.text=QPlainTextEdit();self.text.setObjectName('sourceCode');self.text.setReadOnly(True);self.text.setPlainText('正在读取…');rv.addWidget(self.text,1);ch.addWidget(right,1);v.addWidget(content,1)
        row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show()
    def close(self):
        self.hide();self.deleteLater();self.close_callback()
    def set_error(self,message):self.text.setPlainText(message)
    def set_metadata(self,data):
        self.metadata=data;self.team.setText(data['team_name']);s=data['verified_score'];self.meta.setText(f"{data['task'].upper()} · 排名 #{data['rank']} · 平均 {score(s['mean_clear_time_s'])} · 局均范围/单局数量 {scene_spread(s)} · 清除率 {percent(s['clear_rate'])}")
        self.details.setText(f"认证时间 {local_time(data['verified_at'])}  ·  {data['simulator_version']}\nSOURCE SHA256  {data['source_sha256']}")
        self.tree.blockSignals(True);self.tree.clear();self.tree.addItems(['策略说明','README']);self.tree.addItems(data['source_tree']);self.tree.blockSignals(False);self.tree.setCurrentRow(0)
    def select_file(self,name):
        if not self.metadata:return
        if name=='策略说明':self.text.setPlainText(self.metadata.get('description') or '未提供单独的策略说明，请查看 README。')
        elif name=='README':self.text.setPlainText(self.metadata.get('readme') or '未提供 README。')
        elif name:self.text.setPlainText('正在读取 '+name+'…');self.fileRequested.emit(name)
    def set_file(self,name,content):
        if self.tree.currentItem() and self.tree.currentItem().text()==name:self.text.setPlainText(content)

class LeaderboardAuth(QWidget):
    """Compact in-app sign-in dialog; anonymous leaderboard access remains available."""
    def __init__(self,parent,submit,close):
        super().__init__(parent);self.submit_callback=submit;self.close_callback=close
        self.setObjectName('veil');self.setAttribute(Qt.WA_StyledBackground);self.setStyleSheet('QWidget#veil { background:rgba(20,35,31,125); }')
        self.setGeometry(parent.rect());outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.addStretch()
        row=QHBoxLayout();row.addStretch();self.card,v=box('dialog');self.card.setFixedWidth(410)
        top=QWidget();th=QHBoxLayout(top);th.setContentsMargins(18,14,12,8);th.setSpacing(8)
        titles=QVBoxLayout();titles.setSpacing(2);titles.addWidget(label('排行榜账号','heading'));titles.addWidget(label('登录后查看我的队伍、排名和提交历史','muted'));th.addLayout(titles);th.addStretch();th.addWidget(button('×',self.close,'icon',24));v.addWidget(top)
        body=QWidget();bv=QVBoxLayout(body);bv.setContentsMargins(18,8,18,16);bv.setSpacing(6)
        bv.addWidget(label('用户名','muted'));self.username=QLineEdit();self.username.setPlaceholderText('请输入用户名');self.username.setMaxLength(32);bv.addWidget(self.username)
        bv.addWidget(label('密码','muted'));self.password=QLineEdit();self.password.setPlaceholderText('请输入密码');self.password.setEchoMode(QLineEdit.Password);self.password.setMaxLength(128);bv.addWidget(self.password)
        self.feedback=label('未登录仍可查看完整公开榜。账号请求仅通过 HTTPS 发送。','muted');self.feedback.setWordWrap(True);bv.addWidget(self.feedback);v.addWidget(body)
        footer,h=box('dialogFooter',(18,12,18,12),True);h.addWidget(label('密码不会写入本地文件','muted'));h.addStretch();h.setSpacing(8)
        self.register_button=button('注册',lambda:self.submit('register'),width=76);self.login_button=button('登录',lambda:self.submit('login'),'primary',76);h.addWidget(self.register_button);h.addWidget(self.login_button);v.addWidget(footer)
        self.password.returnPressed.connect(lambda:self.submit('login'))
        shadow=QGraphicsDropShadowEffect();shadow.setBlurRadius(28);shadow.setOffset(0,12);self.card.setGraphicsEffect(shadow)
        row.addWidget(self.card);row.addStretch();outer.addLayout(row);outer.addStretch();self.raise_();self.show();self.username.setFocus()
    def submit(self,method):
        username=self.username.text().strip();password=self.password.text();self.password.clear()
        if not username or not password:self.set_error('请输入用户名和密码。');return
        self.set_busy(True,'正在通过 HTTPS '+('登录…' if method=='login' else '注册…'))
        self.submit_callback(method,username,password)
    def set_busy(self,busy,message=None):
        self.login_button.setEnabled(not busy);self.register_button.setEnabled(not busy);self.username.setEnabled(not busy);self.password.setEnabled(not busy)
        if message:self.feedback.setStyleSheet('color:#4e5b60;font-size:10px;');self.feedback.setText(message)
    def set_error(self,message):
        self.set_busy(False);self.feedback.setStyleSheet('color:#9a2d2d;font-size:10px;');self.feedback.setText(message)
    def close(self):
        self.hide();self.deleteLater();self.close_callback()

class Window(QMainWindow):
    def __init__(self,store,leaderboard=None):
        super().__init__();self.store=store;self.session=Session(store);self.service=None;self.server_error=''
        self.remote=leaderboard or LeaderboardGateway(parent=self);self.leaderboard_task='q3';self.leaderboard_rows=[];self.leaderboard_user=None;self.source_viewer=None;self.leaderboard_auth_dialog=None;self.leaderboard_error_kind=None
        self.release_config={'current_version':APP_VERSION,'latest_version':APP_VERSION,'release_notes':'V1 正在开发中。','mac_download_url':'','windows_download_url':'','announcement':'V1 开发中；下载入口将在发布后开放。','feedback_url':''}
        self.current_task='q3';self.current_mode='practice';self.detail=False;self.modal=None;self.shown_completion=None;self.last_key=None;self.history_key=None
        self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint);self.setWindowTitle('Q3Q4 本地模拟器');self.resize(1000,626);self.setMinimumSize(1000,626)
        QApplication.instance().setStyle('Fusion');self.setStyleSheet(STYLE.replace('__FONT_STACK__',qt_font_stack()))
        root=QWidget();self.setCentralWidget(root);v=QVBoxLayout(root);v.setContentsMargins(0,0,0,0);v.setSpacing(0);v.addWidget(TitleBar(self))
        self.body=QWidget();self.body.setObjectName('body');v.addWidget(self.body,1);h=QHBoxLayout(self.body);h.setContentsMargins(0,0,0,0);h.setSpacing(0)
        sidebar=QWidget();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(160);side=QVBoxLayout(sidebar);side.setContentsMargins(0,0,0,0);side.setSpacing(0)
        brand=QWidget();brand.setFixedHeight(50);bh=QHBoxLayout(brand);bh.setContentsMargins(14,0,10,0);bh.setSpacing(8);bh.addWidget(image_label(28));bh.addWidget(label('环境模拟器','brand'));bh.addStretch();side.addWidget(brand)
        line=QFrame();line.setObjectName('separator');line.setFixedHeight(1);side.addWidget(line)
        self.nav=Nav(self.navigate);side.addWidget(self.nav,1)
        self.version_label=label('v'+APP_VERSION+'  ·  本地复刻','version');self.version_label.setContentsMargins(16,0,0,0);self.version_label.setFixedHeight(32);self.version_label.setStyleSheet('border-top:1px solid #3a484a;');side.addWidget(self.version_label);h.addWidget(sidebar)
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
            historybar,hb=box('strip',(16,0,16,0),True);historybar.setFixedHeight(27);sym=label();sym.setPixmap(icon('file',size=15).pixmap(15,15));hb.addWidget(sym);hb.addSpacing(6);histitle=label('','sectionTitle');histitle.setStyleSheet('font-size:11px;font-weight:700;');hb.addWidget(histitle);hb.addStretch();hb.addWidget(label('可滚动查看全部','muted'));hb.addSpacing(10);hb.addWidget(button('',self.reload_history,'icon',18,'refresh'));pv.addWidget(historybar)
            table=DataTable(['测试案例编码','干扰源数量','开始时间','结束时间','文件大小','状态','操作'],[.20,.17,.145,.145,.14,.10,.10],'暂无日志文件')
            table.horizontalHeader().setFixedHeight(27)
            table.cellDoubleClicked.connect(lambda r,c,t=task:self.view_history(t,r));pv.addWidget(table,1)
            self.groups.append(dict(task=task,panel=panel,head=head,historybar=historybar,title=title,subtitle=sub,start=start,availability=availability,histitle=histitle,table=table,records=[]))
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
        self.summary,sh=box('truth',(16,6,16,6),True);self.summary.setFixedHeight(48);si=label();si.setPixmap(icon('radio','#204939',18).pixmap(18,18));sh.addWidget(si);sh.addSpacing(10);sv=QVBoxLayout();sv.setSpacing(1);sv.addWidget(label('本次演练测试干扰源数量','sectionTitle'));self.summary_text=label();sv.addWidget(self.summary_text);sh.addLayout(sv);sh.addStretch();pv.addWidget(self.summary)
        self.saved,sl=box('saved',(16,6,16,6),True);self.saved.setFixedHeight(47);li=label();li.setPixmap(icon('file','#1a5341',18).pixmap(18,18));sl.addWidget(li);sl.addSpacing(10);lv=QVBoxLayout();lv.setSpacing(1);self.saved_title=label('行为日志已保存','sectionTitle');lv.addWidget(self.saved_title);self.saved_name=label();self.saved_name.setStyleSheet('font-family:Menlo,Consolas,monospace;font-size:9px;');lv.addWidget(self.saved_name);sl.addLayout(lv);sl.addStretch();self.saved_size=label();self.saved_size.setMinimumWidth(64);self.saved_size.setAlignment(Qt.AlignRight|Qt.AlignVCenter);self.saved_size.setStyleSheet('font-size:10px;font-weight:700');sl.addWidget(self.saved_size);pv.addWidget(self.saved)
        feedback,fl=box('strip',(16,5,16,5));feedback.setFixedHeight(43);fl.addWidget(label('指令与反馈','sectionTitle'));self.feedback_hint=label('仅显示最新1000条','muted');fl.addWidget(self.feedback_hint);pv.addWidget(feedback)
        self.actions=DataTable(['接收时间','指令','位置','频道','响应摘要','虚拟时间'],[.16,.104,.244,.104,.232,.156],'等待机器狗发出指令','radio');pv.addWidget(self.actions,1)
    def _leaderboard_page(self):
        p,v=self.page();v.setContentsMargins(20,14,20,14)
        head=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(1);titles.addWidget(label('公开评测服务','eyebrow'));titles.addWidget(label('排行榜','heading'));head.addLayout(titles);head.addStretch()
        self.leaderboard_status=label('尚未连接','offline');head.addWidget(self.leaderboard_status);head.addSpacing(8);self.leaderboard_account_button=button('登录 / 注册',self.leaderboard_account_action,'account',90,'account');head.addWidget(self.leaderboard_account_button);head.addSpacing(6);self.leaderboard_refresh_button=button('刷新',self.refresh_leaderboard,width=72,ico='refresh');head.addWidget(self.leaderboard_refresh_button);v.addLayout(head);v.addSpacing(5)
        hero,hh=box('leaderHero',(10,2,10,2),True);hero.setFixedHeight(36);self.leaderboard_tabs=[]
        for task,text in [('q3','第3问（Q3）'),('q4','第4问（Q4）')]:
            tab=button(text,lambda checked=False,t=task:self.select_leaderboard_task(t),'tab',112);tab.setCheckable(True);tab.setChecked(task=='q3');self.leaderboard_tabs.append(tab);hh.addWidget(tab)
        self.my_results_tab=button('我的成绩',self.select_my_results,'tab',92);self.my_results_tab.setCheckable(True);self.my_results_tab.hide();hh.addWidget(self.my_results_tab)
        hh.addStretch();self.leaderboard_rule=label('清除率 > 89.9% · 按平均清除升序','muted');hh.addWidget(self.leaderboard_rule);hh.addSpacing(12);self.leaderboard_update=label('上次更新：—','muted');hh.addWidget(self.leaderboard_update);v.addWidget(hero);v.addSpacing(7)
        self.leaderboard_feedback=label('','muted');self.leaderboard_feedback.setWordWrap(True);self.leaderboard_feedback.setFixedHeight(22);self.leaderboard_feedback.hide();v.addWidget(self.leaderboard_feedback)
        self.leaderboard_view=QStackedWidget()
        self.leaderboard_table=DataTable(['排名','队伍','平均清除','局均最快–最慢 / 单局数量','清除率','认证','源码'],[.06,.21,.13,.22,.11,.18,.09],'暂无排行榜成绩','trophy',30)
        self.leaderboard_table.cellClicked.connect(self.leaderboard_cell);self.leaderboard_view.addWidget(self.leaderboard_table)
        profile,pv=box('leaderPanel',(14,11,14,12));top=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(2);self.profile_title=label('我的队伍 / 我的成绩','sectionTitle');titles.addWidget(self.profile_title);self.profile_summary=label('正在获取账号数据…','muted');titles.addWidget(self.profile_summary);top.addLayout(titles);top.addStretch();self.logout_button=button('退出账号',self.logout_leaderboard,width=78);self.logout_button.setFixedHeight(26);top.addWidget(self.logout_button);pv.addLayout(top);pv.addSpacing(9)
        self.my_submissions=DataTable(['任务','状态','平均清除','局均范围 / 单局数量','清除率','排名','提交时间'],[.07,.16,.13,.21,.11,.08,.24],'暂无提交记录','file',28);self.my_submissions.horizontalHeader().setFixedHeight(30);pv.addWidget(self.my_submissions,1);self.leaderboard_view.addWidget(profile);v.addWidget(self.leaderboard_view,1)
    def set_leaderboard_connection(self,online,text):
        self.leaderboard_status.setObjectName('online' if online else 'offline');self.leaderboard_status.setText(('●  ' if online else '○  ')+text);self.leaderboard_status.style().unpolish(self.leaderboard_status);self.leaderboard_status.style().polish(self.leaderboard_status)
    def set_leaderboard_feedback(self,text='',error=False,kind=None):
        self.leaderboard_error_kind=kind if text else None;self.leaderboard_feedback.setText(text);self.leaderboard_feedback.setVisible(bool(text));self.leaderboard_feedback.setStyleSheet('color:#9a2d2d;font-size:10px;' if error else 'color:#4e5b60;font-size:10px;')
    def clear_leaderboard_login(self):
        self.leaderboard_user=None;self.my_results_tab.hide();self.my_results_tab.setChecked(False);self.leaderboard_account_button.setText('登录 / 注册');self.leaderboard_view.setCurrentIndex(0)
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
        self.refresh_leaderboard(False)
    def select_my_results(self):
        if not self.leaderboard_user:self.open_leaderboard_auth();return
        for tab in self.leaderboard_tabs:tab.setChecked(False)
        self.my_results_tab.setChecked(True);self.leaderboard_view.setCurrentIndex(1);self.remote.call('dashboard',self.receive_leaderboard_dashboard)
    def refresh_leaderboard(self,include_session=True):
        self.leaderboard_refresh_button.setEnabled(False);self.set_leaderboard_connection(False,'正在连接')
        task=self.leaderboard_task
        self.remote.call('leaderboard',lambda data,error,t=task:self.receive_leaderboard(t,data,error),task)
        if include_session:
            self.remote.call('session',self.receive_leaderboard_session);self.remote.call('metadata',self.receive_release_metadata)
        elif self.leaderboard_user:self.remote.call('dashboard',self.receive_leaderboard_dashboard)
    def receive_leaderboard(self,task,data,error):
        if task!=self.leaderboard_task:return
        self.leaderboard_refresh_button.setEnabled(True)
        if error:self.show_remote_error(error);return
        self.set_leaderboard_connection(True,'HTTPS 在线')
        if self.leaderboard_error_kind!='auth':self.set_leaderboard_feedback()
        self.leaderboard_rows=list(data);self.leaderboard_update.setText('上次更新：'+datetime.now().strftime('%H:%M:%S'));self.leaderboard_table.set_empty_text('暂无排行榜成绩')
        values=[]
        for row in self.leaderboard_rows:
            open_source=row.get('open_source_status')=='OPEN_SOURCE_VERIFIED';badge='✦ OPEN SOURCE VERIFIED' if open_source else '✓ VERIFIED'
            values.append([row['rank'],row['team_name'],score(row.get('mean_clear_time_s')),scene_spread(row),percent(row.get('clear_rate')),badge,'查看源码' if open_source else '—'])
        self.leaderboard_table.rows(values)
        for index,row in enumerate(self.leaderboard_rows):
            if row.get('open_source_status')=='OPEN_SOURCE_VERIFIED':
                gradient=QLinearGradient(0,0,150,0);gradient.setColorAt(0,QColor('#7351c7'));gradient.setColorAt(.5,QColor('#167f91'));gradient.setColorAt(1,QColor('#188351'))
                item=self.leaderboard_table.item(index,1);item.setForeground(QBrush(gradient));font=item.font();font.setBold(True);item.setFont(font)
                self.leaderboard_table.item(index,5).setForeground(QColor('#6d3bb5'));self.leaderboard_table.item(index,6).setForeground(QColor('#176f59'))
            if not row.get('ranking_eligible',row.get('clear_rate',0)>.899):
                self.leaderboard_table.item(index,5).setText('未达门槛 · '+badge)
                for column in range(self.leaderboard_table.columnCount()):self.leaderboard_table.item(index,column).setForeground(QColor('#7f8984'))
            if row['rank']<=3:
                rank=self.leaderboard_table.item(index,0);rank.setForeground(QColor(('#a86a00','#536477','#9a5734')[row['rank']-1]));font=rank.font();font.setBold(True);rank.setFont(font)
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
        self.set_leaderboard_feedback();teams=data['teams'];submissions=data['submissions'];names='、'.join(t['team_name'] for t in teams);ranks=[f"{r['task'].upper()} #{r['rank']}" for r in submissions if r.get('rank')]
        if not teams:self.profile_summary.setText('尚未创建队伍 · '+('暂无提交记录' if not submissions else '已有提交记录'))
        else:self.profile_summary.setText('队伍：'+names+'  ·  '+(' / '.join(ranks[:3]) if ranks else '尚未上榜'))
        values=[]
        for row in submissions:
            status={'AWAITING_SOURCE':'等待上传源码','QUEUED':'QUEUED · 排队中','RUNNING':'RUNNING · 评测中','VERIFYING':'认证中','VERIFIED':'✓ VERIFIED','FAILED':'FAILED · 评测失败','TIMEOUT':'TIMEOUT · 超时','INTERRUPTED':'评测中断'}.get(row.get('status'),row.get('status','—'))
            if row.get('open_source_status')=='OPEN_SOURCE_VERIFIED':status='✦ OPEN SOURCE VERIFIED'
            values.append([row['task'].upper(),status,score(row.get('mean_clear_time_s')),scene_spread(row),percent(row.get('clear_rate')),'#'+str(row['rank']) if row.get('rank') else '—',local_time(row.get('created_at'))])
        self.my_submissions.rows(values)
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
    def open_leaderboard_source(self,submission_id):
        if self.source_viewer:self.source_viewer.close()
        self.source_viewer=SourceViewer(self.body,lambda:setattr(self,'source_viewer',None));self.source_viewer.fileRequested.connect(lambda path,sid=submission_id:self.load_source_file(sid,path));self.remote.call('code',self.receive_source,submission_id)
    def receive_source(self,data,error):
        if not self.source_viewer:return
        if error:self.source_viewer.set_error(str(error));return
        self.source_viewer.set_metadata(data)
    def load_source_file(self,submission_id,path):
        self.remote.call('code_file',lambda data,error,p=path:self.receive_source_file(p,data,error),submission_id,path)
    def receive_source_file(self,path,data,error):
        if self.source_viewer:self.source_viewer.set_file(path,str(error) if error else data)
    def receive_release_metadata(self,data,error):
        if error or not isinstance(data,dict):return
        for key in self.release_config:
            if isinstance(data.get(key),str):self.release_config[key]=data[key]
        self.apply_release_config()
    def apply_release_config(self):
        cfg=self.release_config;current=cfg['current_version'] or APP_VERSION;latest=cfg['latest_version'] or current
        self.version_label.setText('v'+current+'  ·  本地复刻');self.notice_text.setText(cfg['announcement'] or '暂无新公告。')
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
        if index==3:self.refresh_leaderboard()
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
        row=group['records'][index];self.dialog('测试历史',f"测试案例编码：{row['case_id']}\n{LABELS[row['state']]}，虚拟时间 {row['virtual_time_s']:.3f} s\n日志保存在本机。",'导出','关闭',lambda ok:self.export(row) if ok else None)
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
                g['histitle'].setText(name+'历史行为日志')
                headers=['测试案例编码','干扰源数量','开始时间','结束时间','文件大小','状态','操作'] if mode=='practice' else ['序号','测试案例编码','开始时间','结束时间','文件大小','状态','操作']
                g['table'].setHorizontalHeaderLabels(headers);g['table'].fractions=[.20,.17,.145,.145,.14,.10,.10] if mode=='practice' else [.104,.216,.16,.16,.16,.10,.10]
                rows=[]
                for i,r in enumerate(g['records']):
                    when=lambda k:datetime.fromtimestamp(r[k]/1000).strftime('%m/%d %H:%M:%S') if r.get(k) else '—'
                    start=[r['case_id'],str(r.get('summary',{}).get('source_total','—'))] if mode=='practice' else [i+1,r['case_id']]
                    rows.append(start+[when('created_ms'),when('ended_ms'),self.log_size(r),'已保存' if r['state'] in TERMINAL else LABELS[r['state']],'导出'])
                g['table'].rows(rows)
                for i,r in enumerate(g['records']):
                    b=button('导出',lambda checked=False,data=r:self.export(data),width=48,ico='download');b.setFixedHeight(22);b.setStyleSheet('font-size:10px;padding:0 3px;');g['table'].setCellWidget(i,6,b)
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
            truth=rm=='practice' and 'summary' in row and state in TERMINAL;self.summary.setVisible(truth)
            if truth:
                q=row['summary'];self.summary_text.setText(f"共{q['source_total']}个，全向{q['omni']}个，定向{q['directional']}个")
            self.saved.setVisible(state in TERMINAL);self.saved_name.setText(row['case_id']+'.jsonl');self.saved_size.setText(self.log_size(row));self.feedback_hint.setText(f"仅显示最新{self.store.settings['display_rows']}条")
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
                text=f"{name}：{REASONS.get(row['reason'],row['reason'])}，测试已结束。\n本次测试的日志已保存在本地。\n行为日志已保存。"
                self.dialog(name+('完成' if state=='FINISHED' else '已中止' if state=='ABORTED' else '超时退出'),text)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'modal') and self.modal:self.modal.setGeometry(self.body.rect())
        if hasattr(self,'source_viewer') and self.source_viewer:self.source_viewer.setGeometry(self.body.rect())
        if hasattr(self,'leaderboard_auth_dialog') and self.leaderboard_auth_dialog:self.leaderboard_auth_dialog.setGeometry(self.body.rect())
    def closeEvent(self,event):
        if self.session.state in ACTIVE:
            event.ignore();self.dialog('退出模拟器','退出将中止本次测试。是否继续？','继续','取消',lambda ok:self.dialog('再次确认退出','确认中止本次测试并退出模拟器？','退出','取消',lambda yes:self.close_confirmed() if yes else None) if ok else None);return
        self.timer.stop()
        if self.service:self.service.close();self.service=None
        if hasattr(self.remote,'close'):self.remote.close()
        event.accept()
    def close_confirmed(self):self.session.abort('app_closed');self.close()
