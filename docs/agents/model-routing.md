# 项目模型路由

按每个阶段实际承担的工作判定难度。派发时读取角色与难度交叉格里的精确 `model` 和 `reasoning_effort`。按[派发规程](../../plugins/zhiheng/skills/double-loop/references/dispatch.md)记录实际参数与返回结果。

| 难度 | 项目示例 | 默认模型和推理档位 |
| --- | --- | --- |
| `simple` | 修改 README 中一条本地验证命令并运行核对 | `gpt-6.2-sol` / `medium` |
| `regular` | 在开发交接和验收中补充同一个证据字段，验证传递结果 | `gpt-6.2-sol` / `high` |
| `complex` | 调整多工单集成时的版本与审查证据规则，覆盖并行实施、复用审查和返工 | `gpt-6.2-sol` / `max` |

`implement-ticket` 和 `implementation-slice` 固定使用 `high`。两条独立审查 `Standards` 和 `Spec` 固定使用 `max`。

| 角色 | `simple` | `regular` | `complex` |
| --- | --- | --- | --- |
| `plan-feature` | `gpt-6.2-sol` / `medium` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `max` |
| `implement-ticket` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `high` |
| `implementation-slice` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `high` |
| `accept-delivery` | `gpt-6.2-sol` / `medium` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `max` |
| `Standards` | `gpt-6.2-sol` / `max` | `gpt-6.2-sol` / `max` | `gpt-6.2-sol` / `max` |
| `Spec` | `gpt-6.2-sol` / `max` | `gpt-6.2-sol` / `max` | `gpt-6.2-sol` / `max` |
| `setup-harness` | `gpt-6.2-sol` / `medium` | `gpt-6.2-sol` / `high` | `gpt-6.2-sol` / `max` |
