# v30

现已发布：

- `ShuMo_Simulator_macOS.dmg`：macOS Apple Silicon
- `ShuMo_Simulator_Windows_x64.zip`：Windows 10/11 x64

Windows 版已在 Windows 11 x64 完成实机构建与验收，通过冻结 core regression、
客户端测试、打包后 Q3/Q4 E2E 和全新解压 E2E。

普通用户只需下载对应平台的 DMG/Windows ZIP；GitHub 自动生成的源码压缩包不是可运行软件。
源码压缩包不包含 simulator core、场景生成数据或服务器评测代码。

- 在 Simulator 左侧导航中集成 Q3/Q4 排行榜。
- 加入注册、登录、个人参赛名、我的成绩和提交历史。
- 支持直接上传策略 ZIP，提交时选择公开源码或仅提交成绩。
- 加入 `OPEN SOURCE VERIFIED` 徽章、金属扫光参赛名和客户端内源码查看器。
- 排行榜按 30 秒缓存读取，切换 Q3/Q4 不重复消耗流量；手工刷新可强制更新。
- 本地成绩页直接显示提交时间、缩略测试编码、干扰源数量、平均清除时间、清除率和局均范围。
- 恢复官方演示界面中的 CUMCM 图标，并明确社区项目边界。

冻结 simulator core、数学模型、随机生成规律、ErrorField、HTTP 2026 协议与虚拟计时规则未改动。
