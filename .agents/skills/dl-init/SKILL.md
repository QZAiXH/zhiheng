---
name: dl-init
description: 双层循环项目初始化。首次接入或修复接入时，安装固定版本的项目级 Matt Pocock 技能，生成或增补 AGENTS.md，初始化或恢复 OpenWiki；保护已有内容并记录中断进度。
---

# 接入项目

主 Agent 在目标项目执行初始化，完成后交回 [double-loop](../double-loop/SKILL.md)。接入状态与研发运行、OpenWiki 引擎状态分别保存。依赖安装是本技能的授权范围；初始化不自动提交用户代码。正文与项目指令使用中文。

## 步骤

1. 确认目标目录，读取适用指令、现有 AGENTS.md / CLAUDE.md、清单、脚本与文档规则。定位 Git 顶层；非 Git 项目可在调用本技能时建立仓库，无首个提交则记录 `needs_git_baseline`。技能包自身不因生成技能而接入业务流程。
2. 先运行 [项目助手](scripts/project_init.py) 的 `status`。接入记录有效时只检查当前必要能力；已完成的安装、指令与 Wiki 不重复生成。有变化或中断时，按 [安装与恢复](references/onboarding.md) 补齐对应阶段。
3. 探索实际可用的 skill-installer 和 OpenWiki 入口。OpenWiki 入口缺失时先按 [项目集成](references/wiki.md) 接入成熟工具，再用助手 `prepare` 在目标项目安装 [固定清单](../double-loop/assets/project-manifest.json) 中的上游技能，并保证本包九个技能完整可读。保留 checkout、许可证与内容指纹。已有同名目录内容匹配则复用，冲突则保留并报告；缺项可先补齐。阶段交接使用依赖记录中的绝对路径，避免同名全局技能影响选择。
4. 读取上游 `setup-matt-pocock-skills` 和 `writing-for-agents`，适配项目指令与必要的领域、tracker 文档。按 [指令文件所有权](references/agents.md) 生成有项目事实依据的中文正文，再用助手 `instructions` 增补 AGENTS.md。目标明确是 AGENTS.md；既有 CLAUDE.md 规则可引用并保持一致。已有 tracker 沿用，否则使用本地规格与任务，不自动创建远端 Issue。
5. 按 [Wiki 首次接入与恢复](references/wiki.md) 检查项目级集成。主 Agent 根据仓库规模、研究难度和宿主能力动态推荐 Wiki Host 的模型、强度与新上下文；复用仍有效的确认，或并入首次执行配置集中确认。新 Host 串行完成原生生命周期，记录真实 finish complete / begin noop，或明确的 reload / 阻塞状态。
6. 运行 `verify`，核查安装内容、指令区块、Wiki 回执、源码漂移与 Git 基线；另从宿主工具清单核查调度与 MCP 能力。全部满足才能交回总控；无初始提交时，需求讨论可继续，进入 worktree 执行前按已有授权建立基线。不能把模拟回执、文件存在或安装成功等同于 Wiki 完成。

## 收尾

持久保留项目接入记录、依赖指纹、项目指令和 Wiki 回执。助手正常退出时清理自己创建的 staging；异常退出遗留物按 [安装与恢复](references/onboarding.md) 核对后清理。安装好的技能、原始 checkout、用户文档和 OpenWiki 状态属于后续运行依赖，不作为任务草稿删除。

完成说明列出接入状态、实际目标、版本、Wiki 结果和剩余阻塞。新安装的技能在宿主重新发现后可见；若 MCP 需重新加载，保存 `awaiting_host_reload`，待下一次调用恢复，不以额外模型或旁路文件写入伪装完成。
