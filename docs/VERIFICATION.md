# 验证状态与边界

当前包有九个技能、15 个固定上游依赖和 56 项隔离回归。历史记录和独立回执见[完整验证记录](../.agents/skills/double-loop/references/validation.md)。

| 验证 | 证据与范围 |
|---|---|
| 29 项接入回归 | 本地 Git fixtures；安装复用/冲突、区块保护、写入中断、源码漂移、Wiki 回执、reload 和 Git 基线 |
| 27 项研发状态回归 | 模型配置、依赖图、检查点、证据过期、知识门槛、引用保护与清理恢复 |
| 独立首轮 31 项 | 固定 upstream 的真实 clone 与官方安装器安装，用户内容、九技能包与许可证检查 |
| 独立修复复验 15 项 | 损坏 JSON 对象诊断、排除否定规则、规格漂移与临时状态噪声 |
| 独立最终补验 18 项 | 成熟 OpenWiki CLI 的真实 Codex 项目级集成；入口、重复准备、用户配置与全局配置保护 |
| npx 完整安装 | Skills CLI 1.7.1 在空白项目真实安装发布前本地技能源；九个目录与源内容指纹一致，许可证、53 处包内引用与两个助手入口通过，见[回执](verification/npx-install.json) |
| 技能契约检查 | 清单、frontmatter、界面元数据、许可证、文件引用和公开材料 |

各轮回执对应不同代码版本，记录各自指纹；新增文档不能将早期结果改写为最终版本全量实测。独立验证过程中发现的 JSON 数组记录异常已修复并复验。

## 复现

```bash
uv run --with-requirements requirements-dev.txt python -B tools/check_repository.py
uv run --with-requirements requirements-dev.txt python -B tools/run_checks.py --group all
```

可通过 `--group core`、`local`、`github`、`knowledge` 单独运行对应回归。CI 在 Linux、macOS 两类系统与三种 runner 验证同一代码；完成情况以 [GitHub Actions](https://github.com/QZAiXH/zhiheng/actions/workflows/verify.yml) 中具体提交的结果为准。

## 外部执行边界

模型、Wiki 回执与 PR 状态在回归中明确模拟。真实上游安装与 OpenWiki 集成已在独立临时项目执行；真实多模型业务任务、Wiki 原生生成全流程和业务 PR 端到端交付仍待目标项目验证。文件存在、配置通过或请求模型已记录，不等于外部调用真实完成。

公开历史材料会替换本机私人路径和测试机定位路径。原件校验指纹保留，公开副本的变换及新指纹见[脱敏清单](../.agents/skills/double-loop/references/verification/publication-redaction.json)。这些定位标签不是可执行环境配置，旧归档验证脚本只用于追踪当时步骤。
