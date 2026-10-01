---
name: note-it
description: "记录任务实现中的决策、偏离、取舍和未决问题。用于 note-it、实现笔记；支持 GitHub Issue 报告和本地非数字稳定任务 ID，按单一产物映射增量维护中文 HTML。"
---

## Harness / Codex CLI 入口（优先路由）

当仓库存在 `.harness/config.json`，或当前请求明确使用本增强计划时，进入此分支。先定位实际安装的 `harness-init/SKILL.md` 并读取其 `references/workflow-contract.md`；配置缺失时先初始化，不能猜测模式。记录实际加载路径和版本，不能同时加载同名原版与增强版。

保留下文四类记录。先从任务合同读取模式、稳定 ID 和单一产物映射。local 默认 docs/task-<task-id>.html，不要求数字 Issue、GitHub URL 或 PR，标题/文件重命名仍更新同一产物；github 保留 docs/issue#XXXX.html。ID 重复、路径冲突或越界先阻塞。
正文中文，HTML lang=zh-CN；local 将模板元信息改成任务文件链接和 task_id，不虚构 Issue 链接。安全转义来自任务的文本和属性值。事实附代码/测试/规范依据；候选/冲突/未验证推测不得固化。重要决策链接 ADR。文件已有内容默认增量保留。

在此分支执行对应工作后返回。下文是上游非 Harness 独立流程的参考；不要把它的默认 GitHub 操作、状态写入、自动合并或工具假设混入本分支。Codex 使用 `$技能名` 或明确请求加载技能，不假设存在 Claude 的 Skill 工具或 `/goal`。


# Implementation Notes

After completing implementation and review/fix for an Issue, capture a running implementation notes file that documents how the implementation diverges from or interprets the spec.

## Triggers

Use when:
- After `/goal` implementation and `/review-it` are both complete
- User says "记录笔记", "implementation notes", "note-it", "/note-it"
- Before `/ship-it` (as a final checkpoint)
- Any time the user wants to capture design rationale

## The Job

1. Determine the Issue number from context (branch name, `/goal` target, or user input)
2. Review the implementation against the Issue spec / PRD
3. Generate an HTML notes file at `docs/issue#XXXX.html`
4. Present a summary to the user

## Notes Structure

The HTML file must cover these four categories. If a category has nothing to report, write "None" with a brief explanation.

### 1. Design Decisions
Choices made where the spec was ambiguous or silent:
- What was the ambiguity?
- What choice did you make?
- What was the rationale?

### 2. Deviations
Places where you intentionally departed from the spec:
- What did the spec say?
- What did you implement instead?
- Why was the deviation necessary or better?

### 3. Tradeoffs
Alternatives you considered and why you picked what you did:
- What were the viable alternatives?
- What were the pros/cons of each?
- Why did the chosen approach win?

### 4. Open Questions
Anything you'd want confirmed or revised:
- What assumption are you unsure about?
- What should the user verify?
- What might need follow-up?

## Output

- **Format:** HTML
- **Location:** `docs/`
- **Filename:** `issue#XXXX.html` (where XXXX is the zero-padded Issue number, e.g., `issue#0042.html`)

## HTML Template

Use this exact HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Implementation Notes — Issue #XXXX</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #FAF9F6;
      color: #1a1a1a;
      padding: 2.5rem 2rem;
      line-height: 1.7;
    }
    .container { max-width: 800px; margin: 0 auto; }
    h1 { font-size: 1.375rem; font-weight: 700; margin-bottom: 0.25rem; }
    .meta { color: #8B8680; font-size: 0.8125rem; margin-bottom: 2rem; }
    h2 {
      font-size: 1rem;
      font-weight: 600;
      margin-top: 2rem;
      margin-bottom: 0.75rem;
      padding-bottom: 0.375rem;
      border-bottom: 1px solid #E8E4DE;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .dot {
      width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    }
    .dot.design { background: #5B8A72; }
    .dot.deviation { background: #D97757; }
    .dot.tradeoff { background: #4A6FA5; }
    .dot.question { background: #D4A843; }
    .item {
      background: #FFFFFF;
      border: 1px solid #E8E4DE;
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 0.75rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .item h3 { font-size: 0.875rem; font-weight: 600; margin-bottom: 0.375rem; }
    .item p { font-size: 0.8125rem; color: #4A4540; margin-bottom: 0.375rem; }
    .label {
      display: inline-block;
      font-size: 0.6875rem;
      font-weight: 500;
      padding: 0.125rem 0.5rem;
      border-radius: 4px;
      margin-right: 0.375rem;
    }
    .label-design { background: #F5F8F6; color: #5B8A72; border: 1px solid #5B8A72; }
    .label-deviation { background: #FFF5F0; color: #D97757; border: 1px solid #D97757; }
    .label-tradeoff { background: #F0F4F8; color: #4A6FA5; border: 1px solid #4A6FA5; }
    .label-question { background: #FDF8F0; color: #D4A843; border: 1px solid #D4A843; }
    .none { color: #B0AAA4; font-style: italic; font-size: 0.8125rem; }
    .footer {
      text-align: center; margin-top: 2.5rem; color: #B0AAA4;
      font-size: 0.6875rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Implementation Notes</h1>
    <p class="meta">Issue <a href="{{ISSUE_URL}}">#{{ISSUE_NUMBER}}</a> &mdash; {{ISSUE_TITLE}} &mdash; {{DATE}}</p>

    <h2><span class="dot design"></span> Design Decisions</h2>
    <!-- One .item per decision, or .none if none -->

    <h2><span class="dot deviation"></span> Deviations</h2>
    <!-- One .item per deviation, or .none if none -->

    <h2><span class="dot tradeoff"></span> Tradeoffs</h2>
    <!-- One .item per tradeoff, or .none if none -->

    <h2><span class="dot question"></span> Open Questions</h2>
    <!-- One .item per question, or .none if none -->

    <p class="footer">Generated by goal-workflow /note-it</p>
  </div>
</body>
</html>
```

## Example Item

```html
<div class="item">
  <h3><span class="label label-design">Decision</span> Used interface-based polymorphism instead of switch</h3>
  <p><strong>Ambiguity:</strong> The spec said "handle different types" without specifying how.</p>
  <p><strong>Choice:</strong> Defined a <code>Handler</code> interface with per-type implementations.</p>
  <p><strong>Rationale:</strong> Adding new types requires no changes to existing code (Open/Closed Principle). A switch would grow unboundedly.</p>
</div>
```

## How to Determine the Issue Number

1. If the user provides it directly (e.g., `/note-it #42`), use it
2. If on a branch named `feat/issue-42-*` or `fix/issue-42-*`, extract `42`
3. If the last `/goal` target was `#42`, use `42`
4. Otherwise, ask the user: "Which Issue number should I use for the notes file?"

## Edge Cases

| Scenario | Handling |
|----------|----------|
| No Issue number found | Ask the user to specify |
| `docs/` directory does not exist | Auto-create it |
| Notes file already exists for this Issue | Ask: "Update existing notes or overwrite?" — default to update (append new items) |
| No deviations or open questions | Write "None — implementation followed the spec as written." |
| Spec/PRD file not found | Note in Open Questions: "No PRD found at tasks/prd-*.md — verify against original requirements." |

## Checklist

Before saving:
- [ ] Issue number identified
- [ ] All four categories reviewed (even if some are "None")
- [ ] Design decisions explain rationale, not just what was done
- [ ] Deviations clearly contrast spec vs implementation
- [ ] Tradeoffs mention specific alternatives considered
- [ ] Open questions are actionable (user can answer yes/no or give direction)
- [ ] HTML is well-formed and renders correctly