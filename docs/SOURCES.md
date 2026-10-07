# 方法、依赖与许可来源

本项目提供中文阶段编排、接入保护与确定性状态助手。方法采用上游文档，Wiki 与平台操作采用现有能力。

| 来源 | 用途 | 当前选择 |
|---|---|---|
| [mattpocock/skills](https://github.com/mattpocock/skills/tree/6fd947921b935b7e1e69293a200400f0fdd5c15f) | 需求、设计、拆分、TDD、诊断、审查、复盘与项目指令方法 | 固定 `6fd947921b935b7e1e69293a200400f0fdd5c15f`；接入时安装，保留 upstream checkout 与许可证 |
| [OpenWiki](https://github.com/langchain-ai/openwiki) | 项目知识检索和原生页面生命周期 | 复用目标环境安装；0.7.0 项目集成和协议已核验，不强制替换有效版本 |
| [OpenAI Skills](https://github.com/openai/skills) | 官方 skill-installer 与 skill-creator 方法 | 复用宿主提供的入口，项目级安装明确传入 `--dest` |
| [Vercel Skills CLI](https://github.com/vercel-labs/skills) | 发现与安装本仓库完整技能包 | `npx skills@latest add`；项目级 Codex 安装使用 `--skill '*' --copy`，发布前实测 |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) | Markdown 引用解析 | 辅助脚本固定版本见 requirements.txt |
| [PyYAML](https://github.com/yaml/pyyaml) | 仓库 frontmatter / 元数据 / CI YAML 检查 | 开发依赖固定版本见 requirements-dev.txt |
| Python 标准库、Git、GitHub CLI | 状态、依赖图、文件指纹、仓库及 PR 操作 | 使用当前环境的成熟实现 |

各阶段入口及上游方法适配规则见[依赖说明](../.agents/skills/double-loop/references/dependencies.md)，安装清单由 [project-manifest.json](../.agents/skills/double-loop/assets/project-manifest.json) 统一维护。

设计参考了《Agent 驾驭工程之美》已核验章节中的双层循环、独立验证、上下文检查点、知识固化与状态分区。本仓库是独立实践；不包含课程全文，也不声明覆盖尚未核验的全部章节。

本仓库沿用 MIT 许可，保留原有 Matt Pocock 版权声明并补充项目声明。每个技能目录均附 LICENSE；运行时安装的第三方包继续遵循它们各自许可。本包不内嵌上游技能正文或重造 Wiki 引擎。
