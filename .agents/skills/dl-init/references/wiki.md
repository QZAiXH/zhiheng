# OpenWiki 首次接入与恢复

## 集成与 Host

读取当前环境实际 OpenWiki SKILL.md，检查原生 begin / submit_plan / next_page / submit_page / finish 工具可调用。已有 CLI、skill 和有效集成直接复用。集成缺失时用成熟 CLI：

```text
openwiki integrations list --project <Git顶层>
openwiki integrations install codex --project <Git顶层>
```

安装限定项目配置，不修改全局 Codex 配置。当前 CLI 不保证支持 `--version` 或子命令 `--help`，探索优先读已安装包的 README / package.json；需要网络核实时只查官方来源。安装后工具尚未在当前宿主出现，记录 `awaiting_host_reload` 和结果，下一次调用再检查，不反复安装或伪造成功。

入口尚不存在时，在本地准备阶段先完成这项集成，给 prepare 提供可读路径。项目级安装返回本地 `.agents/skills/openwiki/SKILL.md` 时优先使用它，并以该路径运行或重跑 prepare，更新依赖入口与排除规则；已完成的上游安装直接复用。完成所有规则变更后才开始 Wiki 生成。

主 Agent 依据源文件规模、架构不确定性、资料质量与可用能力动态推荐一个 Wiki Host 配置。没有预置模型。配置包含实际模型 ID、支持的 effort、`context: fresh`、推荐理由、能力来源和用户确认依据。仍有效的既有确认可复用；新增选择并入一次集中确认，用户没回复不视作授权。

实际调用新 Agent 时用 `fork_turns: "none"`，显式传 `model` 与 `reasoning_effort`，交接目标根、当前版本、必要规范与原生工具入口。Host 亲自研究并串行写每页，遵守 OpenWiki 不委派 page / research / review 子 Agent 的要求。它与设计、实现、审查的三模型互异要求是不同约束；Wiki 可复用适合的模型。

## 生命周期

1. 从 Git 确定精确绝对根。先完成依赖、项目文档与排除规则，再开始生成；生成期间冻结业务源码。
2. 首次无 Wiki 用 `openwiki_begin({root, mode: "init", language: "zh-CN"})`；已有 Wiki 用 `mode: "update"`。先核对当前工具签名；此语言参数已从 OpenWiki 0.7.0 原生协议核验。有活动运行时接续原生返回的队列，完整保留引擎状态，不破坏性重建。
3. begin 返回 noop 时保留具体回执和无需更新依据。planning 时 Host 从源码研究仓库机制，提交有证据的计划；首次必须包含 quickstart，不规划引擎生成的 index。
4. Host 循环 next_page → 当前页与源码研究 → 写分配页面 → submit_page，通过后再取下一页，按 begin 返回的中文语言配置写作。已有其他语言活动运行时，原生恢复拒绝切换语言；记录实际 conflict，提出结束旧运行后中文 update 的方案并取得适用授权，不改引擎字段或把英文页冒充中文完成。
5. next_page complete 后调用 finish，只有 finish complete 才记录成功。源漂移使计划失效时再次 begin / plan，然后继续生命周期。
6. 引擎负责 Claims、索引、运行状态、来源和 `OPENWIKI` 指令区块；Host 仅编辑原生分配的页。助手只读检查 quickstart 与区块，不代写 Wiki。

已有 Wiki 若缺少 OpenWiki 指令区块，交引擎按其当前接入/更新机制修复。noop 但结构未就绪不能算首次接入完成。空仓库缺乏可证实事实时，记录无法生成事实页的原因，继续建立有授权的项目内容；不填造 Claims。

## 保存真实回执

Host 将实际结果交总控，后者通过助手 `wiki --input` 保存。JSON 成功记录必须含：

- `root`：本项目 Git 顶层绝对路径。
- `status`：`complete` 或 `noop`；`operation` 分别为 `openwiki_finish` 或 `openwiki_begin`。
- `tool_response`：原始调用响应对象，至少包含匹配的 status；`evidence`：调用标识、结果与实际模型回报情况的中文说明。
- `host`：`model`、`effort`、`context: "fresh"`、`rationale`、`capability_evidence`、`confirmed: true`、`confirmation`。

尚需 reload 或真正能力阻塞时保存 `status: awaiting_host_reload` / `blocked`、root 和具体 evidence，不填写成功响应。测试夹具必须明确标记模拟，绝不能用其初始化真实项目。

助手独立保存回执内容指纹与源文件指纹；源文件、用户项目指令或依赖变化后，由 Host 验证是否需要 update。助手的接入记录不是 OpenWiki 原生状态，也不取代引擎验证。
