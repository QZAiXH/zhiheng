# zhiheng · 双层循环开发技能

用同一张工单把需求、代码和验收结果连起来。外环确认要做什么、怎样算完成，再按证据决定结单、返工或重新设计。内环围绕当前工单改代码、跑测试，把代码版本和实际结果交回外环。

## 安装

在支持 `codex plugin` 的 Codex CLI 中运行以下命令，即可从本仓库的 `main` 安装全部 5 个技能。

```sh
codex plugin marketplace add QZAiXH/zhiheng --ref main
codex plugin add zhiheng@zhiheng-local
codex plugin list --marketplace zhiheng-local --json
```

安装完成后，`zhiheng@zhiheng-local` 应显示 `0.2.0`、已安装并启用。已经通过本地仓库安装 `0.1.0` 的用户，可在原仓库的 `main` 分支执行 `git pull --ff-only`，再执行 `codex plugin add zhiheng@zhiheng-local`。旧版 `zh` 总入口由 `double-loop` 接替。

只在单个项目中使用时，也可以从本仓库根目录把 5 个技能一起复制到目标项目，保留它们之间的相对路径。

```sh
project_dir=/path/to/your/project
mkdir -p "$project_dir/.agents/skills"
cp -R plugins/zhiheng/skills/. "$project_dir/.agents/skills/"
```

## 第一次接入项目

在目标项目中打开 Codex，选择 `setup-harness`，告诉它工单放在哪里。例如，“给这个项目接入双层循环，工单用本地 Markdown。”它会找到现有的项目说明和测试命令，和你确认各阶段使用的模型与推理档位，再预览要写入 `AGENTS.md` 或 `CLAUDE.md` 的内容。工单也可以放在 GitHub 或 GitLab，使用 OpenViking 的项目在这一步绑定项目知识库。

## 日常怎么用

接入后，在项目中说“完成 #42”。总调度从原工单的记录接手。有需求没定就从设计开始，已准备好就开发，已有交付版本就直接验收。

| 你的请求 | 技能入口 | 得到什么 |
| --- | --- | --- |
| 给项目接入双层循环 | [`setup-harness`](plugins/zhiheng/skills/setup-harness/SKILL.md) | 项目入口、工单位置、验证命令和模型分工 |
| 完成这张工单 | [`double-loop`](plugins/zhiheng/skills/double-loop/SKILL.md) | 调度各阶段，将验收结果和下一步记回原工单 |
| 先讨论需求，把验收条件写清楚 | [`plan-feature`](plugins/zhiheng/skills/plan-feature/SKILL.md) | 规格、验收例子，以及需要拆分时的子工单和依赖 |
| 这张工单只做开发 | [`implement-ticket`](plugins/zhiheng/skills/implement-ticket/SKILL.md) | 可核对的代码版本、测试结果和开发交接 |
| 只给这次交付出验收报告 | [`accept-delivery`](plugins/zhiheng/skills/accept-delivery/SKILL.md) | 按验收条件列出证据和待处理项，工单保持原状态 |

单张工单独立交付时，开发后分别审查项目规范（`Standards`）和需求规格（`Spec`），验收时复用同一版本的审查结果。多张工单一起交付时，在集成版本上做一次完整审查，并验证父规格中的业务例子。[独立审查规程](plugins/zhiheng/skills/accept-delivery/references/independent-review.md)

## 本地验证

在本仓库根目录运行项目身份工具的单元测试。测试需要 Python 3.9+，使用临时目录和模拟服务响应。

```sh
python3 -B -m unittest discover -s plugins/zhiheng/skills/setup-harness/tests -v
```

项目接入技能附带上游原件及其 MIT 许可证。[来源与版本](plugins/zhiheng/skills/setup-harness/upstream/ORIGIN.md) · [许可证](LICENSE)
