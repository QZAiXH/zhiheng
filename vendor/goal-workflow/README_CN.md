# goal-workflow

## Codex CLI Harness 增强版（开发与验收中）

本分支依据 2026-09-30 v0.5 计划增强上游 `b06ab3c1c147dcf7ef8dd62a8927cd506d098135`，第一宿主为 Codex CLI。保留原技能链，新增 `harness-init`，固定 `local` / `github` 模式；执行控制、真实检查、组合基线、恢复和知识接入分别验收。当前可用能力与未完成实测必须以验证报告为准，不把本节或模拟通过视作 P5 发布验收完成。

- [共享运行合同](skills/harness-init/references/workflow-contract.md)
- [Serena / MADR 固定来源与知识边界](skills/harness-init/references/knowledge.md)
- Codex 技能使用 `$harness-init` / `$loop-it` 等入口；下方 `/...` 是上游 Claude 使用示例，不能据此假设 Codex 存在 `/goal` 或 Claude 的 Skill 工具
- 默认在 verified 停靠，推送/合并/部署不能仅由技能文本推导授权


[English](./README.md) | 简体中文

一套 AI 驱动的研发工作流，从需求到代码交付，全程在 Claude Code 中完成。

```
/prd  →  /prd-to-spec (可选)  →  /to-issues  →  /loop-it (→ /goal → /review-it → /note-it → /walkthrough → /ship-it)×N
```

<p align="center">
  <img src="docs/workflow.png" alt="Goal Workflow 信息图" width="800">
</p>

## 安装

```bash
npx skills add smallnest/goal-workflow
```

## 技能列表

| 命令 | 说明 |
|------|------|
| `/prd` | 生成 PRD 需求文档 |
| `/prd-to-spec` | 将 PRD 转化为技术设计方案（可选） |
| `/to-design` | 从 PRD 生成设计提案（Go proposal 风格） |
| `/to-issues` | 将 PRD/SPEC 拆解为 Issue 并创建卡片 |
| `/loop-it` | 批量实现所有 Issue，支持检查点恢复 |
| `/graph` | 把任务/PRD 转成依赖图并并发实现各节点 |
| `/goal` | 端到端实现 Issue（Claude Code 内置） |
| `/review-it` | 自动化代码审查与迭代修复 |
| `/understand` | 将本次（AI）新生成的改动变成可交互的审阅网页 |
| `/ship-it` | 提交、PR、合入、关闭 Issue |
| `/note-it` | 为 Issue 记录实现笔记 |
| `/walkthrough` | Phase-2 走查文档：变更摘要、验证证据、可视化证明、评审门禁 |
| `/humanize-it` | 文档去 AI 味改写 |
| `/article-icons` | 为文章配内联 SVG 图标 |
| `/listenhub-tts` | ListenHub 文本转语音 |
| `/insight-diagram` | UML 与架构图生成 |
| `/design-it` | 把需求转成自包含的 HTML 设计文档 |
| `/code-to-spec` | 逆向生成项目规格文档 |
| `/refactor` | 专家级代码重构（Fowler 目录） |
| `/modern-go` | Go 代码现代化改造（35+ 条规则） |
| `/smell` | 检测架构反模式、代码坏味道和复杂度热点 |

## 文档

完整使用指南：[docs/index.html](docs/index.html)

## 许可证

MIT