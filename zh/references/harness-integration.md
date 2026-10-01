# 执衡统一入口与增强引擎

日常入口保持 `$zh`，原七个 zh 技能仍按职责使用。底层复用固定 goal-workflow 基线的增强技能和自包含 harness-init 资产，避免同时运行两个任务循环。

## 安装位置与读取

从实际技能加载路径定位同级 `harness-init/SKILL.md`，读取它的 `references/workflow-contract.md` 与相关 helper-contract/knowledge 文档。不要根据聊天猜安装位置，不混用原版同名技能。缺少依赖时停止并提示从本仓库用 `tools/install-harness.py` 安装完整增强集合，不能退回无保护的旧自动合并路径。

源代码存于仓库 `vendor/goal-workflow/`；安装时把七个 zh 入口和十个增强组件放在同一技能目录。选择性安装 harness-init 用于诊断仍自包含，但不能据此宣称全部 zh 工作流已安装。

## 职责路由

- zh-context → harness-init 的原生 Serena 入口与 P0；读取并保留已有 .zhiheng 资料，以 Serena 作为本增强流程唯一可写项目记忆源
- zh-plan → prd / 可选 prd-to-spec、to-design(MADR) / to-issues
- zh-implement、zh-debug → loop-it 的受控串行实现与修复
- zh-review → review-it 独立检查与 Blocking/Warning/Info 门禁
- zh-finish → note-it / walkthrough / ship-it / 实际交付对账与收尾

只加载当前阶段和相关资料；完整验收/强约束始终保留。复杂任务的独立上下文必须实际可用，不能把技能切换当作会话隔离。

## 原有资料与状态

保留现有规则、文档、.zhiheng/PROJECT.md 和已完成任务记录，不自动删除或迁移。知识迁移先核实内容和持久依据，再通过原生 Serena 受控写入；旧文件可以保留作为只读来源/导航。MADR 沿用项目已有 ADR 目录。

本增强任务只由公共 Git 目录锁、受控 Controller 和主 worktree 的 .loop-state.json 推进。下方旧版 task.py 可以用于明确的旧任务独立用法，不能同时为同一增强任务维护另一份权威进度。升级/回退不撤销已经发生的 Git/平台操作，恢复必须对账。

## 可用性与权限

目标为 Codex CLI on macOS、Linux、WSL；每种 OS 必须有自身实际能力和停止路径证据，Linux 测试不能计作 macOS 通过。WSL 使用其实际本地 Linux 文件系统；原生 Windows、未核实共享文件系统不自动纳入范围。

保持明确 local/github 模式；通过当前安装入口的 --help 使用实际命令。能力收据、验收合同和真实工具结果决定能否运行/交付，ready 布尔值和模型声明不能替代证明。模拟宿主/平台须明确标记，不能升级成真实通过。

默认交付到 verified 停靠；是否 push、创建 PR、merge、关闭 Issue 由本次具体授权与配置共同限制。现有安全权限保持有效，缺权限时找用户协助，不换途径绕过。
