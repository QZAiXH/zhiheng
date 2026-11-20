# 工单指南

工单使用 `github.com/QZAiXH/zhiheng` 的 GitHub Issues。父规格与各实施切片各用一张 Issue。PR 关联原 Issue 并提供代码差异与交付证据。

| 操作 | 命令 |
| --- | --- |
| 核对仓库与 Issues 状态 | `gh repo view github.com/QZAiXH/zhiheng --json nameWithOwner,url,hasIssuesEnabled` |
| 列出待处理工单 | `gh issue list -R github.com/QZAiXH/zhiheng --state open` |
| 读取原工单、评论或关联父规格 | `gh issue view <number> -R github.com/QZAiXH/zhiheng --json number,title,body,labels,comments,state,url` |
| 创建父规格或子工单 | `gh issue create -R github.com/QZAiXH/zhiheng --title '<title>' --body-file <file>` |
| 在原工单追加证据或决定 | `gh issue comment <number> -R github.com/QZAiXH/zhiheng --body-file <file>` |
| 验收通过并留下结论后关闭工单 | `gh issue close <number> -R github.com/QZAiXH/zhiheng` |

在工单正文记录目标版本或 Git 修订、范围、可观察的验收例子与检查命令。保存创建后返回的工单 URL。优先使用原生子工单和阻塞依赖。需要用正文关联时填写 `Part of #<parent>` 和 `Blocked by: #<number>`，跨仓库使用完整工单 URL。优先遵循目标修订的[规格与工单约定](../../plugins/zhiheng/skills/plan-feature/references/ticket-and-spec.md)。
