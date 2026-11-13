# I-02 隔离执行请求

在 `tests/fixtures/local-project/` 的临时副本里，使用 `zh` 阶段技能完成一个本地任务：增加 `apply_discount(lines, rate)`，以现有 `subtotal` 为基础，`rate` 为 0 到 1 的 Decimal 兼容输入，结果四舍五入到 2 位小数，越界率抛 `ValueError`。保留现有行为与现有单元测试。约定终点为本地变更、测试结果、双轴审查与逐项验收；无需 Git 提交。任务资料默认保存在副本内 `docs/tasks/`。

新执行者只获得本请求与工程入口。观察任务身份/规格/计划/派发、红绿测试、真实代码变化、独立审查 Standards/Spec、验收逐项证据、最终交付和恢复入口。单独再以 `zh-review` 检查缺失条件的输入边界。
