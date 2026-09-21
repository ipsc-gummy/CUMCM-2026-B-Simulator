# CUMCM 2026 数模 B 题模拟器 v30

Q3/Q4 Simulator 是面向机器狗策略开发的桌面工具：本地测试使用
`127.0.0.1:2026` HTTP 接口，排行榜与策略提交通过 HTTPS 连接。
macOS 和 Windows 共用同一套 PySide6/Qt 界面源码。

> **本项目是社区开发工具，不代表竞赛主办方。**

## 下载

已打包版本从 [GitHub Releases](https://github.com/ipsc-gummy/CUMCM-2026-B-Simulator/releases)
下载。根据 Release 页面已提供的附件选择 macOS 或 Windows 版本。

- macOS：打开 `.dmg`，将 App 拖入“应用程序”。v30 未做 Apple notarization。
- Windows：解压完整目录后运行 `Q3Q4_Simulator.exe`，不要只单独移动 EXE。

下载地址也会在客户端“公告”页中显示；客户端不做强制自动更新。

## 功能

- Q3 / Q4 本地测试生命周期、倒计时、指令反馈和成绩指标
- `POST /enter`、`POST /measure`、`POST /clear`、`POST /exit`
- Q3 / Q4 分榜，未登录也能查看
- 注册、登录、个人参赛名、我的成绩与提交历史
- 上传策略 ZIP，服务器隔离评测后自动上榜
- `VERIFIED` / `OPEN SOURCE VERIFIED` 状态和公开源码查看
- 排行榜断网或服务异常时，本地模拟器仍可独立使用

## 提交策略

登录后打开“排行榜 → 我的成绩 → 提交策略”，选择 Q3/Q4 和一个 ZIP。
ZIP 第一层直接放 `strategy.py`，固定入口为 `strategy.py:run`。

```text
source.zip
├── strategy.py       # 必需：包含 def run(api)
├── README.md         # 可选：策略说明
└── helper.py         # 可选：自己的辅助源码
```

提交时直接二选一：

- **公开源码（推荐）**：认证通过后公开本次源码，显示动态 `OPEN SOURCE VERIFIED` 样式。
- **仅提交成绩**：源码会在服务器中评测，但不在排行榜公开。

选择一经提交不可更改。每个账号同时只评测一条，页面显示
`QUEUED → RUNNING → VERIFIED / FAILED / TIMEOUT`。

完整格式、API 和排错见 [策略 ZIP 提交说明](docs/submitting-a-strategy.md)。

## 排名规则

1. 清除率严格大于 `89.9%` 的成绩进入达标组。
2. 达标组按平均清除时间升序。
3. 未达标组整体置后。
4. 多局先计算每局平均清除时间，再对各局等权平均。
5. 多局展示“局均最快–局均最慢”，单局展示干扰源数量。
6. 总时间不展示，也不参与排名。

公开榜每人每题只显示当前最佳认证成绩，其他记录保留在“我的成绩”。
详见 [排行榜规则](docs/ranking-rules.md)。

## 公开源码边界

本仓库公开 GUI、HTTP 传输层、排行榜 HTTPS 客户端、跨平台适配、
机器狗客户端示例和文档。下列内容不在公开仓库或其 Git 历史中：

- Q3/Q4 场景生成器、随机分布参数和数据集
- physics、ErrorField 与计时内核
- replay、golden scenes 和 hidden scenes
- 排行榜 backend、evaluator、数据库、提交文件和认证 artifacts
- 部署凭据与服务器私有配置

源码检出版可用于开发 GUI 和查看公开排行榜；完整本地 Q3/Q4 仿真使用
Releases 中的桌面应用。详见 [公开与私有边界](docs/private-core-boundary.md)。

## 从源码打开公开客户端

需要 Python 3.11 或 3.12：

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python app.py
```

公开源码检出版不包含本地仿真 core，点击开始本地测试时会明确报错；
排行榜、账号和策略提交页可正常使用。

## 文档

- [策略 ZIP 提交说明](docs/submitting-a-strategy.md)
- [架构说明](docs/architecture.md)
- [本地 HTTP API](docs/http-api.md)
- [排行榜规则](docs/ranking-rules.md)
- [公开与私有边界](docs/private-core-boundary.md)
- [隐私说明](PRIVACY.md)
- [第三方软件说明](THIRD_PARTY_NOTICES.md)
- [品牌与标识](docs/brand.md)
- [贡献说明](CONTRIBUTING.md)
- [安全报告](SECURITY.md)

## License

本仓库中的公开源码使用 [Apache License 2.0](LICENSE)。该许可证不适用于
未包含在本仓库中的私有 simulator core、隐藏数据、评测服务或第三方组件。
