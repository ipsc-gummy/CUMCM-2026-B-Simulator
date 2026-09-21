# 架构说明

```text
机器狗客户端
    │  HTTP 127.0.0.1:2026
    ▼
桌面客户端公开层
    ├── Qt GUI
    ├── HTTP transport
    ├── 生命周期编排
    └── 持久化
           │ private adapter boundary
           ▼
     非公开 simulator runtime

桌面客户端
    │  HTTPS（公开榜 / 账号 / 提交 ZIP / 源码查看）
    ▼
公开 Leaderboard API
```

排行榜网络请求与本地测试相互隔离。排行榜不可用时，桌面客户端只在排行榜区域显示网络状态；
本地接口与测试页面不依赖排行榜服务器。

macOS 与 Windows 共用 `desktop_simulator/` 中的 GUI 和网络代码。平台差异仅限可写数据目录、
系统字体 fallback、窗口行为和构建配置。

桌面客户端不计算或伪造排行榜成绩。用户上传的 ZIP 由服务器隔离 evaluator
执行，权威指标返回后才显示为认证成绩。本公开仓库不包含服务器 backend 或 evaluator。
