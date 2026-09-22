# 数模模拟器 v30 第三方软件说明

本发行包包含或随构建使用以下第三方软件。各组件继续适用其上游许可；本说明不会改变
这些许可，也不会为私有 simulator runtime 另行授予许可。

| 组件 | 版本 | 发行包中的用途 | 许可 |
|---|---:|---|---|
| CPython | 3.13.11 | 内置 Python 运行时 | Python Software Foundation License |
| PySide6 / Qt for Python / Qt | 6.9.3 | Qt Widgets GUI、SVG、网络及动态 Qt frameworks | LGPL-3.0-only，或上游提供的其他可选许可 |
| NumPy | 2.3.5 | 本地模拟器数值运算 | BSD-3-Clause 及其发行包所列第三方条款 |
| PyInstaller | 6.16.0 | 可执行文件 bootloader 与封装 | GPL-2.0-or-later，带 bootloader 分发例外 |
| SciPy | 1.16.3 | 构建/测试环境依赖；当前 Mac App 不冻结 SciPy 模块 | BSD-3-Clause 及其发行包所列第三方条款 |

完整文本随 App 和 DMG 一起提供：

- `third_party_licenses/LGPL-3.0.txt`
- `third_party_licenses/NUMPY_LICENSE.txt`
- `third_party_licenses/SCIPY_LICENSE.txt`
- `third_party_licenses/PYTHON_LICENSE.txt`
- `third_party_licenses/PYINSTALLER_COPYING.txt`

PySide6/Qt 以动态 framework 形式放在 App 的 `Contents/Frameworks/PySide6/Qt/lib/` 下。
Qt 与 Qt for Python 的对应源代码和许可信息可从其上游项目取得：

- https://code.qt.io/cgit/qt/
- https://code.qt.io/cgit/pyside/pyside-setup.git/

NumPy 与 SciPy 的许可文本包含它们随二进制分发所需的第三方 notices。
