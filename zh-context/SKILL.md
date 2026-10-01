---
name: zh-context
description: Initialize or refresh durable project context when asked to onboard a project or investigate and save its context. Map code, command evidence, terminology, and decisions; read-only investigation stays read-only and existing knowledge is preserved.
---

## 执衡 Harness v0.5（默认研发路径）

先读 [统一增强流程](../zh/references/harness-integration.md)。它把现有 zh 入口接到固定 goal-workflow 增强实现；以下步骤适用于本版研发任务，执行后返回，不与原版状态/知识写入并行运行。

项目知识接入使用 Serena v1.7.0 的原生注册/onboarding/读写与渐进记忆入口，重要决策复用 MADR。已有 .zhiheng/PROJECT.md、项目规则与文档先作为证据来源读取并保留，不删除，不再建立与 Serena 并行可写的知识源。只有维护模板或非空列表不能宣称 onboarding 完成。项目尚未通过 P0 时明确保存缺口。

下文保留原协作经验和独立用法。若与增强合同的状态、知识、执行和交付机制冲突，以当前任务的增强合同为准；用户授权和项目规则始终优先，技能文本不会扩大权限。


# 项目上下文

输入是项目、相关任务范围及已有知识；输出是足以支持下一步的项目地图、命令证据、术语/决定指针和知识缺口。独立调用只完成上下文工作，不启动实现、提交或合并。

## 选择接入或调查

明确要求初始化／接入项目上下文，或调查并保存上下文时，按 [项目接入流程](references/project-onboarding.md) 调查、保存必要知识并维护入口指针。这份授权涵盖必要的上下文文档与指针维护，沿用已有范围和按复杂度确认的方式，不重复索要同一授权。这里的初始化默认建立项目知识；明确要求 Git、应用或数据库初始化时按该请求处理，不能把它们当作上下文接入。

仅询问如何接入、了解项目或要求只读调查时，说明方法或回传事实，不创建文档、入口或任务状态。接入不是每次开发的必经步骤，也不引入独立初始化技能或脚本。

上下文文档接入不自动创建开发 worktree、提交或合并；实际产品改动才进入 [工作区开发规则](../zh/references/workspaces.md)。不能由接入推导出 `git init`、依赖安装、数据库迁移、外部服务配置或启用旧钩子的授权；另有明确授权的操作按其范围执行。非 Git 项目也可调查并按要求保存上下文，不伪造公共 Git 目录或开发任务状态。

## 核实与维护知识

读取适用 `AGENTS.md`，优先复用 `.zhiheng/PROJECT.md`、现有领域词汇和决策记录。按任务追到相关代码、配置、入口和检查命令；不要全库倾倒。仓库能查明的事实自己核实，用户决定与代码冲突时明确指出差异。

命令区分“配置声明”“实际通过”“失败”“环境阻塞”，记录环境和来源。只读调查无需初始化开发 worktree；是否运行会产生实际外部影响的命令按已有授权判断。

术语有歧义且影响设计时用具体场景澄清，术语和实现细节分开。仅对真实且持久的取舍保存理由与来源；不把每个细节都变成 ADR。新发现先标为候选，验证后再写入项目知识。

需要持久上下文时才创建或更新已有知识文件，保留原内容，避免空模板及重复规范。任务进度、日志及恢复遵循 [记录规则](../zh/references/records.md)。普通调查可直接在对话回传，不为此写入项目规范或安装钩子。
