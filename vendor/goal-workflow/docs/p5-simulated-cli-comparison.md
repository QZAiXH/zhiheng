# 同基线双模式 CLI 夹具比较

## 结论与范围

2026-10-01，local 三个业务场景均通过；GitHub 五项测试（同样三个业务场景、私有仓库人工交接、运输隔离）全部通过、0 跳过，耗时 365.598 秒。两侧实际执行 Git、业务测试、Serena 和产品 CLI；实现/审查宿主是确定性模拟程序，GitHub 平台与网络运输也被模拟。

这是 **local 与 GitHub 模拟控制路径的单次观测**，不是上游原版与增强版的生产收益比较，也不证明真实 Codex 双模式 P5 已完成。共享执行环境、检查数量和负向/恢复步骤不同，不能把差值解释为性能提升或退化。模型 token、生产 API 费用和真人投入均未知，没有节省比例。

## 相同输入与输出

两个模式使用完全相同的初始化夹具、原生 Serena 完成后的基线 Git tree：

`dda1a16112298ec8a81f0bd0c8fc0577bab07e7d`

README、初始业务代码、SPEC、业务测试 runner、模拟宿主的 SHA256 全部一致。逐任务生成的 `solution.py` 和 `tests/test_business.py` 字节也一致。完整指纹和测量汇总见 [机器可读证据](evidence/p5-cli-comparison.json)。

## 实测指标

时间包含设置与测试主体，不包含证据归档/清理；受控耗时是持久 checkpoint 的累计值。

| 场景 | local 墙钟秒 / 受控秒 | GitHub 模拟墙钟秒 / 受控秒 | 受控命令 local / GitHub | CLI 调用 local / GitHub |
|---|---:|---:|---:|---:|
| 微小功能 | 31.662 / 18.273 | 71.945 / 40.642 | 84 / 382 | 9 / 28 |
| 异常路径 | 27.571 / 16.171 | 68.494 / 38.782 | 64 / 381 | 5 / 26 |
| 前后依赖 | 39.883 / 24.208 | 160.196 / 90.414 | 136 / 764 | 12 / 52 |

模拟实现/独立审查进程分别为每侧 1/1、1/1、2/2。local 异常场景的实现进程由夹具直接调用，未计入 Controller 命令数；其审查受控，因此不能隐去这个差别。local 依赖例实际制造交付完成但 checkpoint 尚未推进的边界，再调用一次 reconcile；GitHub 各例包含 pending 意图与重复只读对账。额外恢复开销没有统一单独计时，不能宣称已测生产故障恢复成本。

私有仓库例另外观测 64.461 秒墙钟、38.860 秒受控耗时、316 条受控命令、22 次 CLI 调用。实际模拟 HTTP 403，保留 PR/CI 和人工停靠；模拟外部人工合并仍执行真正的本地 Git 更新，随后由产品 fetch、tree、祖先关系、Issue 完成与 closeout 对账。没有自动绕过服务器保护。

## 实际穿过的产品路径

`run → push-source → create-pr → checks/wait-checks → verify → ready → merge → reconcile → complete-issue → closeout`

- 创建的 PR 默认 draft；未 ready 的合并请求被拒且不留下虚假未知意图；ready 要本次授权
- 依赖任务在前序未实际交付时不创建实现分支；交付后后序 T 精确等于前序 D
- PR 复用、pending 检查、缺授权、提前关闭 Issue、改动 P0 日志、重复交付/Issue 对账均有负向或恢复断言
- 新的模拟 GitHub P0 读探针实际运行受控协议子进程，严格模式 16 次、人工停靠模式 13 次；212 份归档原始能力日志的 SHA256 已复核

## 严格保留的模拟边界

所有收据保持 `simulation_only`，真实宿主与语义缺口没有被抹去。仅测试 runner 对临时目录、已提交模拟 marker、唯一指定 fixture URL/自有 bare remote 的 scope 作窄注入，并显式允许该模拟交付；原始收据完整性、配置/代码绑定、日志哈希、授权、检查、意图/CAS 和 Git 交付验证仍运行。正式 CLI 没有这条绕过入口，未注入时会拒绝。

Git shim 仅把明确目标映射到临时 bare remote，原生 Git 的 hooks、对象、引用、fast-forward 与祖先检查仍执行；`GIT_ALLOW_PROTOCOL=file` 再禁止实际网络运输。第一版映射的缺陷曾触发网络安全拒绝，已停下并修成绝对本地路径，最终隔离测试确认另一 URL 在原生 Git 前被拒。最终测试没有真实模型或 GitHub 请求。

可复现测试：`tests/harness/test_cli_e2e.py`、`tests/harness/test_github_cli_e2e.py`；后者 helper 位于 `tests/harness/fixtures/github_cli_fixture.py`。运行必须显式指定固定 Serena 的 `HARNESS_TEST_SERENA` 和 `HARNESS_TEST_SERENA_PYTHON`，使用项目锁定环境；缺依赖而 skip 不能视为通过。

真实 Mac 的 CLI/原生 Serena 观测、真实 GitHub CI/保护规则/人工交付另列于 [验收报告](harness-acceptance.md)。旧 Mac P0 收据仍为 blocked；修复编号输出解析后的离线回放不被转换成新的 live ready 收据。
