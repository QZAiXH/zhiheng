# 仓库协作约定

回答、技能正文、说明与提交描述使用中文。成熟 GitHub / npm / Python 方案可直接复用时优先复用，保持本包为薄编排层。

先读 README.md 与使用说明.md；修改阶段行为时读取对应 SKILL.md 及其条件引用。技能源在 `.agents/skills/`，依赖与九技能清单以 `double-loop/assets/project-manifest.json` 为准。此仓库自身的发布操作不等同于初始化业务项目。

模型建议由主 Agent 按当次难度、风险和宿主能力动态推荐；设计、实现、审查使用三种不同模型与新上下文。OpenWiki Host 串行处理页面，引擎控制状态由 OpenWiki 维护。用户明确的授权与目标优先于技能默认交付边界。

仓库验证入口为 `tools/check_repository.py`、`tools/run_checks.py --group all`；依赖由 `requirements-dev.txt` 固定，在 uv 隔离环境运行。行为测试用临时项目；真实外部验证与模拟结果分别记录。修改清理、所有权、状态或模型配置约束时补充实际失败场景。

提交前核对相对引用、许可证、公开材料脱敏和 `git diff --check`。不读取或复用 harness-workflow；CI 保留的历史检查名仅用于兼容分支保护。
