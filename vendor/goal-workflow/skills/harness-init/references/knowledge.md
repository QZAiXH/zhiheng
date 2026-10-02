# 知识组件与固定来源

## Serena

目标版本 v1.7.0，完整上游发行包：https://github.com/oraios/serena/tree/v1.7.0
记忆规范：https://github.com/oraios/serena/blob/v1.7.0/docs/02-usage/045_memories.md
原生维护模板：https://github.com/oraios/serena/blob/v1.7.0/src/serena/resources/memory_maintenance.md
onboarding：https://github.com/oraios/serena/blob/v1.7.0/src/serena/tools/workflow_tools.py

通过实际可用 MCP/CLI 激活或注册项目，执行原生 onboarding 的指引，并实际写入/读取 core 与必要主题。取得指引、初始化维护模板、非空列表不等于就绪。尊重现有项目和个人模板，记录有效来源，不盲目覆盖。首版只有 Serena 是可写知识源。

引用分析只解决 mem: 断链。必须使用固定版本的分析输出而非只看退出码；保持工具与直接文件操作的权限边界描述准确。逐层加载而非默认全文灌入；知识依据语义是否真实由独立审查核实。

## MADR

固定版本 4.0.0，模板：https://github.com/adr/madr/blob/4.0.0/template/adr-template.md
推荐路径与说明：https://github.com/adr/madr/blob/4.0.0/README.md

优先沿用项目 ADR 目录；没有时 docs/decisions。使用随包保留的上游模板，正文中文化，保留背景、驱动因素、候选、决策理由、后果和确认方式。状态按上游约定记录；替代旧决策时链接 successor/superseded。只保留一份正文，Serena 记忆与设计报告链接它。

## 长期证据

验证前完成拟入库知识和说明；用仓库相对链接、版本、命令及结果摘要支撑。结果依赖完整外部输出时先核实项目现有归档可访问性和保留策略。没有可靠长期依据则留在候选，不晋升。清理 runs/模拟 CI 到期后，在干净副本重新注册和读取知识验证；保留未验证语义的明确标签。

## 已有知识的显式维护

适配器提供 `update_memory` 和 `rename_memory`：调用者必须先读实际内容并给出 SHA-256 前像及已核实的持久依据。更新仅应用明确的新正文，不自动合并语义；重命名复用 Serena 原生引用传播。变动后逐字核对预期修改，保留其他记忆及项目配置。

这两条路径使用固定 Serena 包的 tool-context 写入边界，拒绝受影响的只读项及全局记忆；不能据此声称原生 CLI 直接写文件或其他 shell 访问获得同样保护。原生引用正确仍不代表事实正确，语义审查结果需单独保留。受 Harness 管理的项目必须通过持锁 Controller 执行原生调用，进程身份、超时与消耗纳入统一执行记录；无 Controller 的调用仅作为未管理临时仓库的组件探针。
