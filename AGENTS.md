<!-- harness-memory:begin -->
## 双层循环开发

- 需求与设计从同一张工单开始。阅读原工单、讨论和关联父规格，确认目标版本、范围、依赖和验收例子。[工单指南](docs/agents/issue-tracker.md) · [领域与规范](docs/agents/domain.md)
- 开发按目标修订的 [README 本地验证](README.md#本地验证) 和[领域与规范指南](docs/agents/domain.md)核对规则。从仓库根目录用 Python 3.9+ 运行 `python3 -B -m unittest discover -s plugins/zhiheng/skills/setup-harness/tests -v`。用 `viking://resources/qzaixh-zhiheng` 下的 `find` 查找并用 `read` 核对原文，按[项目知识指南](docs/agents/project-knowledge.md)确认适用版本。
- 在原 GitHub Issue 评论中记录交付修订或差异、实际命令与结果、规则 URI 和 Git 来源（如有）、待验证的验收项及审查证据。外环 `Check` 核对证据所属版本，`Act` 追加接受、返工或待验证的决定并更新工单状态。[交付证据](plugins/zhiheng/skills/accept-delivery/references/delivery-evidence.md)
- “完成 #42”、只做开发或新建验收报告走 `$double-loop`，按[项目模型路由](docs/agents/model-routing.md)派发。遵循显式调用的技能和用户指定的停止点。解释和总结直接回答。
<!-- harness-memory:end -->
