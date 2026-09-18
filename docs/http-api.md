# 本地 HTTP API

默认地址：`http://127.0.0.1:2026`

支持：

- `POST /enter`
- `POST /measure`
- `POST /clear`
- `POST /exit`

请求使用 JSON，并包含 `arena_id`、`robot_id` 和唯一的 `request_id`。
`/measure` 与 `/clear` 还包含：

```json
{
  "position": {"x": 0, "y": 0},
  "channel": 1
}
```

响应可能包含：

- `accepted`
- `virtual_time_s`
- `real_timestamp_ms`
- `measure_result`
- `svd_deg`
- `clear_result`
- `exit_reason`

移动和频道切换没有独立 API。`/measure` 由 simulator runtime 完成移动、必要的频道切换和检测；
`/clear` 完成移动与清除，并保持当前测向频道。

`request_id` 用于幂等处理。客户端应在重试同一请求时复用原 `request_id`，并为新动作生成新值。
倒计时结束前、会话结束后或生命周期状态不允许时，接口不会接受动作。

物理规则、场景生成和误差分布不在本公开仓库中。
