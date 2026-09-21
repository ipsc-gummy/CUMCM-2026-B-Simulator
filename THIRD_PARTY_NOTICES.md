# 第三方软件说明

本公开仓库的 Python 依赖见 `requirements.txt`。v30 桌面界面使用：

| 组件 | 版本 | 用途 | 上游许可 |
|---|---:|---|---|
| PySide6 / Qt for Python | 6.9.3 | Qt Widgets GUI、SVG 图标和跨平台运行库 | LGPL-3.0-only / GPL-3.0-only / 商业许可，以安装包所附条款为准 |

PySide6 和 Qt 不因本项目的 Apache-2.0 许可而改变其各自许可。分发桌面二进制时，
应保留 PySide6/Qt 包中的许可文本和必要 notices，并按所选许可遵守其重分发要求。

Python 标准库、打包工具及私有 simulator runtime 的许可不由本文件重新授予。
发布包中的完整第三方许可文本应与对应二进制一起提供。
