# 策略 ZIP 提交说明

## 最简流程

1. 打开客户端的“排行榜”，注册或登录。
2. 进入“我的成绩”，点击“提交策略”。
3. 选择 Q3 或 Q4。
4. 选择“公开源码”或“仅提交成绩”。
5. 选择 ZIP 并提交。首次提交会自动使用用户名作为个人参赛名。
6. 在“我的成绩”查看 `QUEUED`、`RUNNING` 和最终结果。

成绩由服务器 evaluator 计算，不需要也不能手填成绩。

## ZIP 里放什么

```text
source.zip
├── strategy.py       # 必需
├── README.md         # 可选
├── helper.py         # 可选
└── your_package/     # 可选
```

`strategy.py` 必须位于 ZIP 第一层，并提供：

```python
def run(api):
    # 把你的 Q3/Q4 策略写在这里
    ...
```

客户端固定使用入口 `strategy.py:run`。自己的 Python 辅助文件可以同时打包。
不要把 `strategy.py` 再套在一层文件夹中。

`examples/strategy_template/` 是最小格式模板。在该目录运行：

```bash
python make_zip.py
```

即可生成可上传的 `source.zip`。模板只用于说明格式，不是高分策略。

## 策略 API

`run(api)` 可调用六个公开方法：

- `api.move((x, y))`
- `api.switch_channel(channel)`
- `api.measure()`
- `api.clear()`
- `api.get_time()`
- `api.get_position()`

也兼容使用 `127.0.0.1:2026` 公开 HTTP 协议的零参数 `run()` 策略。
策略只能依据公开 API 返回值决策，不应读取 seed、场景文件或隐藏坐标。

## 依赖与限制

- ZIP 最大 10 MiB，源码使用 UTF-8。
- 服务器策略评测容器支持 Python 标准库、`numpy==2.3.5`、`scipy==1.16.3` 和 `numba==0.67.0`（使用 `llvmlite==0.49.0`）。
- 当前桌面客户端自动识别 NumPy/SciPy；即使显示“Python 标准库”，上传的策略仍可直接 `import numba`。网页提交可显式选择 Numba。
- Numba 首次 JIT 编译计入每局 90 秒现实时间上限；临时缓存不跨局保存，策略容器仍限 512 MiB、1 CPU。
- 不支持上传后任意执行 `pip install`、shell 命令或外部网络下载。
- 每个账号同时只有一个评测任务，24 小时内最多提交 5 次。
- 过慢、超时、内存超限或异常退出会标记为失败并停止本次评测。

## 公开还是不公开

- **公开源码**：评测通过后，ZIP 中的源码、README 和策略说明可被所有人查看。
- **仅提交成绩**：服务器仍需要运行 ZIP，但排行榜不提供源码入口。

请在上传前删除密码、令牌、个人信息和不想公开的文件。选择会绑定本次提交；
想改变选择时，应创建新提交。

## 常见问题

- **提示找不到 `strategy.py`**：检查 ZIP 第一层，不要压缩外层文件夹。
- **上传过大**：删除数据集、虚拟环境、缓存、日志、测试输出和二进制临时文件。
- **依赖被拒绝**：改用标准库、NumPy、SciPy 或固定版本的 Numba，不要上传完整 venv。
- **长时间 `QUEUED`**：服务器同时只处理一个评测，保持页面可定期查看状态。
- **`FAILED` / `TIMEOUT`**：在提交详情中查看运行分析，修正后重新提交。
