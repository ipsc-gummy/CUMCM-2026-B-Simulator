"""Small platform choices shared by the single Mac/Windows GUI codebase."""
import os
from pathlib import Path
import sys


APP_VERSION = '1.1-dev'


def default_data_dir(platform_name=None, environ=None, home=None):
    platform_name = platform_name or sys.platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)
    if platform_name == 'win32':
        base = environ.get('LOCALAPPDATA') or environ.get('APPDATA')
        return Path(base) / 'Q3Q4_Simulator' if base else home / 'AppData/Local/Q3Q4_Simulator'
    if platform_name == 'darwin':
        return home / 'Library/Application Support/Q3Q4_Simulator'
    base = environ.get('XDG_DATA_HOME')
    return Path(base) / 'Q3Q4_Simulator' if base else home / '.local/share/Q3Q4_Simulator'


def qt_font_stack(platform_name=None):
    platform_name = platform_name or sys.platform
    if platform_name == 'win32':
        return '"Arial", "Microsoft YaHei UI", "Segoe UI"'
    if platform_name == 'darwin':
        return '"Arial", "PingFang SC"'
    return '"Arial", "Noto Sans CJK SC", "DejaVu Sans"'
