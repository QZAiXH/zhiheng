# 外部依赖与首次接入

本包是薄编排层。复用 [mattpocock/skills](https://github.com/mattpocock/skills) 的方法和现有 OpenWiki，不内嵌上游正文、不重造 Wiki 引擎、不加载 harness-workflow。

## 配置

首次用 [dl-init](../../dl-init/SKILL.md) 自动生成目标项目的 `.workflow/dependencies.json` 和接入记录。安装清单与固定版本见 [project-manifest.json](../assets/project-manifest.json)。两个路径由环境探索取得，填写绝对路径：

- `mattpocock_root`：上游仓库 checkout 根，保留它自己的引用、脚本和许可证。
- `mattpocock_revision`：已核对版本。样例固定本包创建时核验的上游提交；换版本需重新核对方法和路径，更新本地记录，不自动跟随 main。
- `openwiki_skill`：现有 OpenWiki 的 `SKILL.md` 路径。示例不绑定当前机器用户目录。
- `installed_skills`：初始化新增的项目目录和完整内容指纹；子 Agent 按这些绝对入口读取，避免宿主同名全局技能干扰。

辅助脚本 `preflight --dependencies <文件>` 检查 Git 版本、上游文件、安装内容和 OpenWiki 入口；旧 checkout-only 配置仍兼容。它不检查账户模型权限或 OpenWiki MCP 在线情况；总控从实际工具清单核对这些能力。

dl-init 复用成熟 skill-installer 安装到目标项目 `.agents/skills/`，在 `.agents/vendor/mattpocock-skills/` 保留固定 checkout 与许可证，并接入项目级 OpenWiki。版本或内容冲突保留原文件；安装是首次接入动作，不在每次任务重复执行。[配置样例](../assets/dependencies.example.json) 仍可用于旧项目的手动迁移。本包生成过程不实际安装业务依赖。

## 阶段按需读取

| 阶段 | 相对上游根的入口 |
|---|---|
| 需求 | `skills/engineering/grill-with-docs/SKILL.md`、`skills/productivity/grilling/SKILL.md` |
| 术语与决策 | `skills/engineering/domain-modeling/SKILL.md` |
| 设计与拆分 | `skills/engineering/to-spec/SKILL.md`、`skills/engineering/to-tickets/SKILL.md` |
| 可选调研与设计方法 | `skills/engineering/research/SKILL.md`、`skills/engineering/codebase-design/SKILL.md` |
| 实现与修复 | `skills/engineering/implement-spec/SKILL.md`、`skills/engineering/tdd/SKILL.md`、`skills/engineering/diagnosing-bugs/SKILL.md` |
| 审查 | `skills/engineering/code-review/SKILL.md` |
| 交付与复盘 | `skills/engineering/pr/SKILL.md`、`skills/engineering/retro/SKILL.md` |
| 项目接入与指令 | `skills/engineering/setup-matt-pocock-skills/SKILL.md`、`skills/productivity/writing-for-agents/SKILL.md` |

这些入口和所需引用是执行方法来源。不要仅列出名字就声称已使用，也不要在没有加载方法时自造同名替代流程。

## 适配规则

- 上游 `disable-model-invocation` 表示手动入口：本包读其文档并在阶段适配中执行方法，不直接由模型触发该手动技能。引用路径始终相对上游目录解析。
- 上游要求的测试边界和拆分确认提前到需求讨论；后续只有实质新决策才询问。
- 默认用本地运行资料跟踪规格和任务，已有项目 tracker 规则则沿用；不为缺少上游 tracker 文档而强制创建远端 Issue。
- 上游实现的全局审查扩展为任务级和集成级独立审查，模型与上下文由本次矩阵约束。上游 `code-review` 的内部两轴调度也必须显式落实同一审查配置。
- `pr` 仅提供描述方法，Git 和 GitHub CLI 才执行交付。OpenWiki 继续遵守它自己的完整生命周期与状态所有权。

来源核验：2026-10-07，上游提交 `6fd947921b935b7e1e69293a200400f0fdd5c15f`，使用 Git `ls-remote` 取得。课程依据是已核验的《Agent 驾驭工程之美》双层循环、独立验证、上下文检查点、知识固化与状态分区章节，不宣称读取了尚未发布的全部章节。
