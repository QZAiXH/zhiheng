# 来源与改写范围

本集合按本地 zh-skills 设计重新组织，不是上游工作流的原样实现。所有七个技能一起安装，跨技能引用均指向安装目录的相邻技能，不需要运行时下载。

上游：[mattpocock/skills](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7)，固定提交 `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`。版权及 MIT 许可完整保存在每个技能的 `LICENSE`，来源为该提交的根 `LICENSE`，Copyright (c) 2026 Matt Pocock。

| 实际查看文件（相对上游根） | 本地采用与改写 |
| --- | --- |
| skills/engineering/wayfinder/SKILL.md | zh 的渐进规划、决定索引和未细化范围；改为本地按任务记录，去掉固定 tracker 和每会话一个 ticket |
| skills/engineering/domain-modeling/SKILL.md | zh-context 的术语澄清、代码对照和按需记录决定；复用项目已有知识，不强制新文件布局 |
| skills/productivity/grilling/SKILL.md | zh-plan 的按依赖追问与主动查明事实；只处理影响下一步的决定，不穷尽设计树 |
| skills/engineering/to-spec/SKILL.md | zh-plan 的需求、验收与决定综合；不强制长用户故事、额外接缝审批或 tracker 发布 |
| skills/engineering/to-tickets/SKILL.md | zh-plan 的可验证行为切片、依赖及兼容迁移；不要求固定 ticket 格式或远端写入 |
| skills/engineering/implement/SKILL.md | zh-implement 的有界实现和反馈；提交权限取决于本次任务，不强制 TDD 与重复全量测试 |
| skills/engineering/tdd/SKILL.md | verification.md 的行为边界与非同构测试；TDD 可选，不采用强制逐测试红绿与接缝重复审批 |
| skills/engineering/diagnosing-bugs/SKILL.md | zh-debug 的症状反馈、缩小复现、假设检验及回归；不固定假设数量，无复现时如实限制结论 |
| skills/engineering/code-review/SKILL.md | zh-review 的需求与规范两个维度、固定候选；小任务单独立会话完成，不照搬一律双会话或通用坏味道硬规则 |

旧本地 zhiheng：保留外层进度、执行/验收分离、onboarding、知识筛选及恢复理念。已检查旧 `init_project.py` 与 `close_task.py` 的用途，但未复制代码、空模板、平台限制或控制器。新工具只做 Git/记录与安装的确定性检查。完整旧技能随迁移保留到发现目录之外的备份。

课程依据为用户提供的《Agent 驾驭工程之美》阅读笔记的概括；采用外层 PDCA、反馈、知识分层与状态连续性，不声称 Bubblewrap、固定模型或每次新执行者属于课程要求。
