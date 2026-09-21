# 贡献说明

欢迎提交 GUI、可访问性、跨平台兼容、HTTP 客户端、排行榜展示、文档和不依赖隐藏数据的测试改进。

提交 Pull Request 前请：

1. 保持 macOS 与 Windows 共用 GUI 源码。
2. 不提交 generator、physics、ErrorField、replay 或隐藏场景。
3. 不提交数据库、用户源码、日志、凭据或本地配置。
4. 不以新的模拟规则或 mock physics 替代私有 runtime。
5. 对行为变化补充直接相关的最小测试。
6. 不使用竞赛主办方的标志、图片或令人误解为官方产品的文案。

发现私有数据意外进入 Issue、PR 或提交历史时，请不要继续传播，并按 `SECURITY.md` 私下报告。
