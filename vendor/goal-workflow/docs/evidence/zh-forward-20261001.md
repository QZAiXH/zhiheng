# zh 新上下文演练

日期：2026-10-01 UTC。

## 方法

在全新模型上下文中明确加载临时仓库内已安装的 zh/SKILL.md，提出普通研发请求：增加 divide(a,b)，零除抛 ValueError，并补 unittest；指定 local 模式、main 目标，虽然配置 remote 也不得访问网络或 GitHub。仅提供任务与技能路径，没有提供预期答案或诊断。

这属于技能路由与拒绝不完整环境的演练，不是实际 Codex CLI 自动发现、模型执行或端到端开发通过。

## 实际观察

- 完整 17 组件已通过统一安装器放在同级目录
- 模型沿 zh 增强入口读取依赖与初始化合同，尝试显式离线锁定依赖
- 缺少本地缓存 wheel，环境中也没有要求版本的 filelock；初始化返回 ready:false / blocked
- 模型未用系统其他版本替代锁定依赖，没有篡改 ready 标志或绕过 P0
- 明确保留未完成状态，没有生成 divide 实现、测试或交付成功声明
- Git 跟踪文件与 main 基线未变；仅创建了被忽略的不完整工具 .venv
- 未调用网络、GitHub API 或 push

## 结论边界

已观察到：zh 统一入口的技能加载与 local 模式选择在此场景中遵守环境门槛，能给出缺失依赖这一具体下一步。

尚未证明：实际 Codex CLI 的自动技能发现、正常实现、独立模型审查、取消或恢复。这些必须由实际宿主验收记录支撑，不能从本演练外推。

系统 CI 使用 GitHub 标准公开仓库运行器，覆盖 Ubuntu、macOS Apple Silicon 与 Intel；具体通过/失败以当前提交的 Actions 结果为准。运行器标签依据 [GitHub 官方文档](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)。
