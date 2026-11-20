# zhiheng · 双层循环开发技能

用同一张工单把需求、代码和验收结果连起来。外环确认要做什么、怎样算完成，再按证据决定结单、返工或重新设计。内环围绕当前工单改代码、跑测试，把代码版本和实际结果交回外环。

## 安装

在支持 `codex plugin` 的 Codex CLI 中运行以下命令，可安装本仓库 `main` 上的技能包。

```sh
codex plugin marketplace add QZAiXH/zhiheng --ref main
codex plugin add zhiheng@zhiheng-local
codex plugin list --marketplace zhiheng-local --json
```

安装完成后，确认 `zhiheng@zhiheng-local` 已启用。本修订的插件版本为 `0.3.0`，包含 6 个技能。通过本地仓库安装的用户可将原仓库更新到目标修订，再执行 `codex plugin add zhiheng@zhiheng-local`。旧版 `zh` 总入口由 `double-loop` 接替。

只在单个项目中使用时，也可以从本仓库根目录把 6 个技能一起复制到目标项目，保留它们之间的相对路径。

```sh
project_dir=/path/to/your/project
mkdir -p "$project_dir/.agents/skills"
cp -R plugins/zhiheng/skills/. "$project_dir/.agents/skills/"
```

## 接入项目和修改设置

在目标项目中调用 `$setup-harness`，选择 GitHub Issues、GitLab 或本地 Markdown。选择 GitHub Issues 后，再决定完成工单时是否要打开 PR 并等这次 PR 的 CI/CD 通过。技能把选择写入项目的工单指南，和你确认测试命令、模型分工及适用的 OpenViking 绑定，再预览项目说明和指南的改动。

下次调用会读取已有选择。旧 GitHub 项目只需补答缺少的 PR 选项。配置齐全且项目情况相同时，技能直接报告当前设置。也可以说“改为 PR 交付”或“改用本地工单”，核对差异后原地更新指南，保留手写内容。

## 日常怎么用

接入后，在项目中说“完成 #42”。总调度从原工单的记录接手。有需求没定就从设计开始，已准备好就开发，已有交付版本就直接验收。

| 你的请求 | 技能入口 | 得到什么 |
| --- | --- | --- |
| 接入项目或修改交付方式 | [`setup-harness`](plugins/zhiheng/skills/setup-harness/SKILL.md) | 项目入口、工单位置、交付方式、验证命令和模型分工 |
| 完成这张工单 | [`double-loop`](plugins/zhiheng/skills/double-loop/SKILL.md) | 调度各阶段，将验收结果和下一步记回原工单 |
| 先讨论需求，把验收条件写清楚 | [`plan-feature`](plugins/zhiheng/skills/plan-feature/SKILL.md) | 规格、验收例子，以及需要拆分时的子工单和依赖 |
| 这张工单只做开发 | [`implement-ticket`](plugins/zhiheng/skills/implement-ticket/SKILL.md) | 本地任务分支、提交、测试与审查交接，工单保持打开 |
| 只提交本工单，或提交并开 PR | [`commit-pr`](plugins/zhiheng/skills/commit-pr/SKILL.md) | 复用或创建本工单的提交，按请求关联代码仓库中的 PR |
| 只给这次交付出验收报告 | [`accept-delivery`](plugins/zhiheng/skills/accept-delivery/SKILL.md) | 按验收条件列出证据和待处理项，工单保持原状态 |

单张工单独立交付时，开发后分别审查项目规范（`Standards`）和需求规格（`Spec`），验收时复用同一版本的审查结果。多张工单一起交付时，在集成版本上做一次完整审查，并验证父规格中的业务例子。[独立审查规程](plugins/zhiheng/skills/accept-delivery/references/independent-review.md)

开发和集成都在独立的任务分支与 worktree 中进行。本地交付验收后，原工单记录分支、提交和验证结果，分支留给你合入。PR 交付验收后，还要等当前提交适用的 CI/CD 通过，再结单并把 PR 留给你合并。项目确实没有适用的远端检查时，工单记录判断依据及本地验证结果。达到交接点后，从原工单核对证据，再清理本次创建且可以安全移除的 worktree。

## 本地验证

从本仓库根目录运行以下回归测试。测试使用 Python 3.9+、Git、临时仓库和可控的服务响应，覆盖项目身份、重复接入、工作区恢复与清理，以及 PR 检查。

```sh
for suite in plugins/zhiheng/skills/*/tests; do
  python3 -B -m unittest discover -s "$suite" -v || exit 1
done
```

项目接入技能附带上游原件及其 MIT 许可证。[来源与版本](plugins/zhiheng/skills/setup-harness/upstream/ORIGIN.md) · [许可证](LICENSE)
