# 公开与私有边界

公开仓库用于桌面客户端协作，不公开场景生成方法或隐藏评测材料。

## 公开

- GUI 与交互状态
- 本地 HTTP transport 与字段校验
- 排行榜 HTTPS 客户端
- 本地状态持久化和平台路径适配
- 机器狗客户端示例
- 不依赖隐藏数据的测试与文档

## 私有

- generator 与随机分布参数
- physics 与 ErrorField
- replay、golden scenes、hidden scenes
- evaluator 的隐藏验证场景
- 用户数据库、提交源码与认证 artifacts
- 部署凭据和服务器私有配置

`desktop_simulator/core_adapter.py` 是公开源码与私有 runtime 的边界。公开版本只提供明确的不可用
提示，不包含替代 generator、简化 physics 或伪造数据。发布版由私有构建流程注入冻结 runtime。
私有 runtime 即使随二进制包分发，也不因此纳入本公开仓库的 Apache-2.0 授权范围。

任何贡献都不得提交通过逆向、泄漏或其他未经授权方式获得的私有 core、场景或生成参数。
