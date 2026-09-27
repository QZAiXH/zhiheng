---
name: zh-context
description: Build or refresh grounded project context, terminology, verified commands, and decision pointers for onboarding or unfamiliar code. Preserve existing project knowledge and distinguish facts from assumptions.
---

# 项目上下文

输入是项目、相关任务范围及已有知识；输出是足以支持下一步的项目地图、命令证据、术语/决定指针和知识缺口。独立调用只完成上下文工作，不启动实现、提交或合并。

读取适用 `AGENTS.md`，优先复用 `.zhiheng/PROJECT.md`、现有领域词汇和决策记录。按任务追到相关代码、配置、入口和检查命令；不要全库倾倒。仓库能查明的事实自己核实，用户决定与代码冲突时明确指出差异。

命令区分“配置声明”“实际通过”“失败”“环境阻塞”，记录环境和来源。只读调查无需初始化开发 worktree；是否运行会产生实际外部影响的命令按已有授权判断。

术语有歧义且影响设计时用具体场景澄清，术语和实现细节分开。仅对真实且持久的取舍保存理由与来源；不把每个细节都变成 ADR。新发现先标为候选，验证后再写入项目知识。

需要持久上下文时才创建或更新已有知识文件，保留原内容，避免空模板及重复规范。任务进度、日志及恢复遵循 [记录规则](../zh/references/records.md)。普通调查可直接在对话回传，不为此写入项目规范或安装钩子。
