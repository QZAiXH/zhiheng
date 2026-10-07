---
name: dl-knowledge
description: 双层循环的知识维护阶段。将验收后的仓库机制提炼到 OpenWiki，归档长期决策和可复用经验，并记录临时材料的稳定替代位置。
---

# 知识提炼与维护

接收已验证代码、验收证据、决策候选和草稿清单。总控按已确认的知识阶段配置创建新上下文；该 Agent 作为 OpenWiki host 串行消费队列，不创建页面、研究或审查子 Agent。

1. 读取 [知识归档规则](references/knowledge.md)，按 [依赖配置](../double-loop/references/dependencies.md) 定位 domain-modeling、openwiki、retro。只加载此次相关材料。
2. 核对代码与测试，把可复用的事实机制、边界、失败语义和排障方法提炼为候选。长期取舍进入 ADR，业务需求和验收原件仍保留。
3. 沿用现有 OpenWiki：Git 根 → begin → 必要时 submit_plan → next_page / submit_page → finish。中文语言与活动队列冲突按 [原生接入规则](../dl-init/references/wiki.md) 处理。noop 可记无需更新；只有 finish 返回 complete 才记更新完成。状态与 Claims 由 OpenWiki 管理。
4. Wiki 生成期间源码稳定；来源漂移时按 OpenWiki 重做计划，暂缓并行代码修改。事实引用保留的源码、测试或持久文档，不能只引用待删草稿。
5. 保存真实工具回执，检查知识与源码一致；把草稿对应的稳定替代路径记入清单。复盘保存有依据的改进建议，不扩大功能或自动修改全局技能。
6. 文档或配置变化后运行适用检查，交总控确认最终验收仍覆盖最终代码，再进入交付。

完成条件：知识更新完成或明确无需更新，ADR 与证据落盘，每份待清理知识草稿有核验后的替代位置。删除由 [dl-deliver](../dl-deliver/SKILL.md) 执行。
