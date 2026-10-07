# 阶段技能与双层循环

```mermaid
flowchart TD
    P["接入检查：dl-init<br/>状态与当前宿主能力"]
    Q["首次本地准备：dl-init<br/>skill-installer + setup-matt-pocock-skills + writing-for-agents"]
    A["需求讨论：dl-discover<br/>grill-with-docs + grilling + domain-modeling"]
    B["动态推荐并集中确认配置：double-loop"]
    C["外层 Plan：dl-plan<br/>to-spec + to-tickets"]
    D["独立设计审查：dl-review"]
    E["外层 Do：dl-execute<br/>implement-spec + Git worktree"]
    subgraph INNER["内层循环：每个任务"]
        F["任务与约束：dl-execute<br/>按需查询 OpenWiki"]
        G["实现：dl-execute + tdd"]
        H["检查与独立审查：dl-review<br/>code-review + 测试 / 类型 / Lint"]
        I["诊断与修复：dl-execute + diagnosing-bugs"]
        F --> G --> H
        H -->|失败| I
        I --> H
    end
    J["外层 Check：集成验收<br/>dl-execute + dl-review"]
    K["外层 Act：调整计划<br/>double-loop + dl-plan"]
    L["知识固化：dl-knowledge<br/>domain-modeling + OpenWiki + retro"]
    M["交付：dl-deliver<br/>pr + Git + GitHub CLI"]
    N["落盘核验与清理：dl-deliver"]
    R["首次 Wiki / 待办恢复：dl-init + OpenWiki<br/>已确认的动态模型，新上下文 Host"]
    P -->|已初始化| A
    P -->|缺项或变化| Q
    Q --> A
    A --> B
    B -->|接入已完整| C
    B -->|Wiki待办| R
    R -->|完成，Git基线就绪| C
    C --> D
    D -->|修订| C
    D -->|通过| E
    E --> F
    H -->|通过并集成| J
    J -->|还有任务| E
    J -->|调整计划| K
    K --> C
    J -->|整体验收通过| L
    L --> M --> N
```

设计审查必须在任务执行之前完成；形成任务图后可再次由独立审查检查依赖与验收覆盖。知识维护后产生实质代码变化则回到验证，不能把它当作纯收尾跳过检查。一次需求的模型与上下文配置在开始时集中确认，默认终点是 PR。

单独调用 dl-init 时只集中确认其 Wiki Host 配置；由总控首次接入时把它合并到需求后的矩阵，避免重复询问。已初始化项目只核查状态及本次实际能力；源码变化交 OpenWiki 更新，活动队列由原生 begin 恢复。
