# 技能包验证记录

日期：2026-10-07。当前九个中文技能已通过 skill-creator 的 quick_validate 校验，技能及使用说明的文件引用、界面元数据均有效。技能创建阶段未读取 harness-workflow，未对本目录初始化业务接入、安装业务依赖、生成 Wiki 或提交代码。真实外部安装只在独立临时项目执行，全局配置保持不变；仓库发布是后续独立操作。

## 初始化增量验证

[本轮回归记录](verification/initialization-regression.json)：29 项项目接入测试和 27 项研发状态测试全部通过。新增覆盖固定清单、15 个上游技能和完整九技能包安装、兼容复用与冲突保护、AGENTS 与 OpenWiki 区块字节保留、接入记录损坏、部分安装与写入中断恢复、项目级 OpenWiki 入口切换、排除规则、源码/规格漂移、reload 检查点，以及无初始提交的 readiness 区分。

测试使用隔离 Git fixtures；安装器、Wiki、模型和 PR 回执按场景明确模拟。真实外部验证另见独立回执：

- [初轮 31 项行为检查](verification/init-forward/independent_receipt.json)：真实 clone 固定 upstream 与官方 skill-installer 项目级安装，核对 15 项内容、九技能包、许可证与用户文件保护；另发现数组接入记录报 Python 回溯。
- [修复后 15 项复验](verification/init-forward/independent_current_receipt.json)：上述诊断问题已修复，结构化错误、ignore 否定规则、持久规格漂移与运行中间状态排除通过。
- [最终项目级集成 18 项补验](verification/init-forward/independent_final_receipt.json)：使用成熟 OpenWiki 0.7.0 CLI 真实安装 Codex 项目集成；项目级入口切换、精确排除、重复安装/准备、已跟踪源码可见、用户其他 MCP 与全局配置保护通过。未调用 Wiki 生成或模型。

独立验证未读取生成者测试作为预期答案。回执包含各自被测版本、来源指纹与边界，不把旧版本的所有场景说成在最终版本重跑。[归档索引](verification/init-forward/archive.json) 映射验证定位到留存日志与脚本。公开副本已替换私人路径与临时机定位标签，原始指纹和公开指纹分别见[脱敏清单](verification/publication-redaction.json)，不将变换后的副本称为原件。Wiki 中文参数与活动运行语言冲突另外从已安装 OpenWiki 0.7.0 原生 protocol / repository-run 源码核验，仅属静态依据。

当前确定性代码 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `dl-init/scripts/project_init.py` | `9c102ac7f3877aa498b4a6db6ae3214d31fd3f4d724ddbfbf11962820483ebbf` |
| `double-loop/scripts/workflow_state.py` | `89c23b7ec3d7be077377cc2999b1670b65ba1a7d6a1e16b2c38df4a6de1e5fad` |
| `double-loop/scripts/dependency_contract.py` | `3348388c0026aed1610c9e91449e35f526693d1b75eaa98d4f2b409853981666` |

初始化源码变化后应按实际影响复验并更新记录。模型三方互异与 fresh context 为静态规则和配置测试；真实多模型业务调用、Wiki 生命周期与 GitHub 发布仍待目标项目运行。

## 先前基础技能验证（历史版本）

以下记录对应新增 dl-init 之前的八技能版本；其历史代码指纹与原始回执保留用于追踪，不替代上方当前版本验证。

### 确定性测试

[测试脚本](../scripts/test_workflow_state.py) 在隔离临时 Git 仓库运行，26 项全部通过。覆盖模型配置约束、任务依赖、源码与被忽略的规格变更、用户文件保护、知识维护门槛、引用保护、路径边界，以及初始化、配置替换和删除中断恢复。当前机器大小写不敏感路径场景实际运行通过。

复现命令见 GitHub [使用说明](https://github.com/QZAiXH/zhiheng/blob/main/使用说明.md)。解析器版本由 [requirements.txt](../scripts/requirements.txt) 固定，通过 uv 隔离环境安装，没有修改系统 Python。

该历史版本辅助脚本 SHA-256：

```text
9d870fcfa6e568cc8b91e0c06b00e1e9a00580ea740186e4a2a9e8e7ee303bad
```

### 独立前向验证

独立 Agent 未读取生成者测试作为预期答案，使用自己的临时仓库验证。其发现的规格指纹遗漏、绝对/括号/大小写路径引用误删和初始化中断问题已修正并复验；最终版本在所测场景中无剩余阻塞缺陷。

- [基础八组回执](verification/report.json)：真实 unittest 红 → 绿、配置与任务图、知识门槛、文件所有权及状态恢复。
- [引用与硬中断复验](verification/extra-final-report.json)：普通与引用式链接、绝对路径、括号、HTML、repo://、Claims、大小写等价路径、文档符号链接及初始化中断。
- [被忽略输入复验](verification/ignored-inputs-final-report.json)：即使 .workflow 被 Git 忽略，规格和任务变更仍使证据过期，临时交接与 scratch 不触发过期。

回执中的临时仓库路径是验证当时的定位记录；业务规范和 Wiki 不应引用这些临时路径。验收摘要与原始回执已复制到本包，生成者的测试临时仓库由测试框架清理；独立验证临时目录在逐文件核对归档内容后移除，Python 编译缓存已清理。

### 实际验证边界

三种不同模型与 fresh context 的调度规则已静态核对，配置拒绝行为已实测；未运行真实多模型业务任务。OpenWiki 与 PR 成功状态在测试中为明确标记的模拟数据，未访问真实写入服务或创建 PR。

首次真实使用通过 dl-init 接入固定依赖与 OpenWiki，并核查当前宿主模型、上下文、Wiki 写入和 GitHub 能力。上述历史静态或隔离测试不代表完整外部业务流程已通过。
