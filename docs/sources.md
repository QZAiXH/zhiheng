# 来源与改造

本包依据工作区《软件开发Harness技能系列需求与设计.md》确认的 I-01—I-07 独立编写。技能正文使用英文，协议中的中文状态值是固定的数据格式。方法来源固定为 `mattpocock/skills` 插件 `1.3.2`、提交 `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`。

三张来源表分别承担不同职责：

- [上游采纳清单](upstream-adoption.tsv)：26 项固定来源的路径、行号、SHA-256、用途、实际落点与改造说明；25 项方法和资源改写或合并，根 [LICENSE](../LICENSE) 原文保留。
- [内部依赖清单](upstream-dependencies.tsv)：源技能之间的引用及其在当前包中的实际落点。
- [来源登记](upstream-provenance.tsv)：调查项、第三方依赖、当前处理、历史观察与待核事项分别列出。

改写后的方法按职责放入 [17 个技能入口](../README.md#选择入口)及其共享资源。`grilling`、`research`、`domain-modeling` 分别进入讨论、研究、领域阶段；`codebase-design`、`prototype` 进入架构、原型阶段；`to-spec`、`to-tickets`、`implement`、`tdd`、`diagnosing-bugs`、`code-review`、`handoff`、`retro` 等分别进入相应阶段或共享规则。`zh-init`、`zh-verify`、`zh-deliver`、`zh-release` 与 [本地 Python 工具](../skills/zh/scripts/harness.py)按本包需求编写。`skill-creator`、`harness-engineering`、`writing-for-agents` 是编写和审查依据，不是目标项目运行依赖。

工具依赖以 [requirements.txt](../skills/zh/scripts/requirements.txt) 为准：`PyYAML>=6.0.3,<7` 用于 YAML 解析，`markdown-it-py==4.3.0` 用于 Markdown 链接解析，后者的传递依赖 `mdurl~=0.1` 在历史检查中解析为 `0.1.2`。Python 3.11+ 和 `PATH` 中的 Git 由环境提供。第三方 Python 包由使用者安装在独立工具环境，不随技能源码或安装包分发；三表记录了来源、版本策略和许可。

构建时只将完整 `skills/`、插件元数据和根许可复制到 `dist/zhiheng/`，并生成逐文件指纹清单。详见[包清单](package-inventory.md)。本地 I-07 审计曾核对固定上游 26/26 个指纹、53 个技能文件、17 个入口和生成包及实际安装缓存的 56 个文件；原始运行记录在开发工作区的 `docs/evidence/` 和 `docs/reviews/`，不作为源码仓库分发内容。本仓库的可复现检查入口见[验证记录](verification.md)。
