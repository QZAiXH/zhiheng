# 贡献指南

欢迎贡献技能指令、使用文档、可复现的行为案例和确定性助手修复。请先搜索已有 Issues；问题报告包含仓库提交、系统与 Python / Git / 宿主版本、所用技能、预期结果、实际结果和最小复现步骤。

## 本地验证

Fork 并克隆仓库，从 main 建立 `feat/…`、`fix/…` 或 `docs/…` 分支。准备 Python 3.12、Git 与 uv，然后从仓库根执行：

```bash
uv run --with-requirements requirements-dev.txt python -B tools/check_repository.py
uv run --with-requirements requirements-dev.txt python -B tools/run_checks.py --group all
git diff --check
```

回归使用临时 Git 项目与明确标记的模拟安装器、Wiki、模型和 PR。涉及真实上游安装、MCP 或 GitHub 发布时，用独立测试项目验证，说明实际副作用和证据类型；不要把模拟成功当成外部流程已通过。

## 修改约定

- 技能和用户文档使用中文；优先复用成熟开源能力，保持本包作为薄编排层。
- 依赖入口与版本以 `project-manifest.json` 为源，不在多个脚本重复维护清单。
- 动态模型由主 Agent 根据需求与实际能力推荐。保持设计、实现、审查三个不同模型以及新上下文规则。
- 接入、单次研发和 Wiki 引擎分别维护状态。修改文件保护或清理行为时，覆盖具体失败场景和中断恢复。
- 变更技能目录结构时核对全部相对链接和九技能完整安装；新增技能目录应附带 LICENSE。
- 说明变更解决的具体问题、最终行为与验证边界。采用中文 Conventional Commits，例如 `fix(init): 保留用户修改的项目指令`。

公开日志前移除令牌、私人路径与未获授权公开的业务材料。历史证据需要脱敏时保留原始版本指纹，并明确公开副本的变换和新指纹。

## CI 与合并

main 的现有保护要求 PR 和 15 个必需检查。本次改版保留这些检查名称，实际执行新包的四组回归与仓库契约检查；名称中的历史前缀只是保护规则的兼容标识。

三种 runner 为 `ubuntu-latest`、`macos-latest`、`macos-15-intel`。每种 runner 执行 core / local / github / knowledge 四组回归及 review 仓库检查。分组必须完整覆盖现有测试且互不重复；没有真实账户的 CI 不做模型、Wiki 和 PR 外部调用。
