# 项目指令与文档所有权

先读取固定 checkout 中 `skills/engineering/setup-matt-pocock-skills/SKILL.md`、它所引用的模板，以及 `skills/productivity/writing-for-agents/SKILL.md`。本技能适配上游的常规询问：项目本地安装已确定；tracker 默认本地并沿用既有规则；明确生成 AGENTS.md。只有实际的范围或规则冲突需要用户决策。

主 Agent 根据项目证据写简短中文正文，再交给助手合并。建议包含：项目目标与主要结构指针、适用语言和用户约束、能从 manifest / CI / 现有文档确认的验证入口、tracker / 术语 / ADR 文档的条件指针，以及首次接入、正常研发、恢复时的技能入口。直接可查的命令配置优先引用其源文件，命令尚不存在就说明待建立，不虚构构建、测试或 lint 命令。

需要 tracker 或领域约定且项目尚无文档时，按上游实际模板生成 `docs/agents/issue-tracker.md` 与 `docs/agents/domain.md`；已有等价规则则引用它们。仅写已有事实和已确认约定，不为了满足模板制造空术语表、ADR 或测试规则。本地任务记录服从 [运行协议](../../double-loop/references/runtime.md)。这些持久规范保留在 Git，OpenWiki 用来解释实际机制和链接决策依据。

区块所有权：

```text
用户原有内容（保留）
<!-- DOUBLE-LOOP:START -->
初始化拥有的中文项目指令
<!-- DOUBLE-LOOP:END -->
用户其余内容（保留）
<!-- OPENWIKI:START -->
仅由 OpenWiki 引擎维护
<!-- OPENWIKI:END -->
```

助手只替换自己拥有且指纹匹配的区块，周围字节保留，包括已有 OpenWiki 区块。区块缺失、重复、损坏或被用户修改时保留文件并报告，不整份覆盖。首次创建后中断的写入意图支持重试。项目已有 AGENTS.md 的自然语言无需强制改写为中文；新生成正文使用中文。

AGENTS.md 不保存具体推荐模型、推理强度或长期固定矩阵。它指向 double-loop 的动态推荐规则。不同模型和上下文的本次选择分别保存于单次运行配置；首次 Wiki Host 配置放在接入回执。安装来源、所有权与绝对路径属于接入记录，避免塞进始终加载的项目指令。
