"""Shared macOS/Windows executable entry point."""
import sys
sys.dont_write_bytecode = True
import argparse
from pathlib import Path
from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox
from desktop_simulator.persistence import Store
from desktop_simulator.gui import Window
from desktop_simulator.platform_support import default_data_dir


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=default_data_dir())
    parser.add_argument('--smoke-test', action='store_true', help='Run packaged GUI/HTTP acceptance in the specified data directory')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName('Q3Q4_Simulator')
    app.setOrganizationName('LocalSimulator')
    args.data_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(args.data_dir/'application.lock'))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.warning(None,'模拟器已运行','此数据目录已有模拟器运行，请切换到已打开的窗口。')
        return 1
    store = Store(args.data_dir)
    window = Window(store)
    window.show()
    if args.smoke_test:
        from desktop_simulator.smoke import run_smoke
        run_smoke(app, window)
    result = app.exec()
    lock.unlock()
    return result

if __name__ == '__main__':
    raise SystemExit(main())
