# 严格保护 GitHub 平台验收

结论：仅在已批准测试分支完成原生 strict 保护状态与成功交付实测。实际平台负例为 BEHIND / BLOCKED，修复后为 CLEAN；随后人工无绕过合并，D 内容与测试候选一致。不是产品自动 CLI 或真实 Codex 宿主 P0/E2E 验收。

## 范围和设置

- PR：https://github.com/QZAiXH/zhiheng/pull/2
- Issue：https://github.com/QZAiXH/zhiheng/issues/1
- 唯一保护设置变更：`goal-harness/smoke-base-20261001`
- required context=`goal-harness-smoke`，strict/up-to-date=true，enforce_admins=true；GitHub绑定该检查app_id=15368。
- main 前后仍为 `fb1935376a450c0956b0388e5ff01d223faefac6`、protected=false。
- 已批准的测试分支保护保留启用，没有自动删除测试记录或放宽设置。

## 真实负例和修复

1. 旧源 `8cf9c8df8e21426004f6a1b2b3f3f3eb24ea6cd9` 的旧CI仍成功，实际目标已前进至 `bc35041bfd3b180a884ec0925f3d3db9171396f2`；GitHub=BEHIND，适配器旧证据=stale。PR.base曾仍返回旧值，使用独立branch ref发现真实T。
2. 源纳入当前T后，提交故意边界错误 `e767f4b5464f6b22905dd5c18b3d1874d078d855`；真实CI failure，GitHub=BLOCKED，适配器checks=blocked/fail。
   CI：https://github.com/QZAiXH/zhiheng/actions/runs/36819931696
3. 修复后实际CI success，GitHub=CLEAN；实际GitHub候选拉取后本地2个测试亦通过。
   CI：https://github.com/QZAiXH/zhiheng/actions/runs/36820139287
4. 只有第3阶段通过后才发起授权人工合并。负例阶段没有发送可能产生交付的merge请求，因此不把平台状态观察冒充一次实际被拒绝的merge API调用。

## 最终 H / T / C / D

- H：`1b545cee7393bd52f328c7c132e620c4e2f18a09`
- T：`bc35041bfd3b180a884ec0925f3d3db9171396f2`
- C：`5497e1dcc34c854376e26228c0216cb398ee6914`
- D：`f58f193260de47d850c7eb97512f8b06b4da49bc`
- C.tree = D.tree：`b952d2798258e2b79139dc6635b3dff02f8605fe`
- 实际目标tip：`f58f193260de47d850c7eb97512f8b06b4da49bc`
- D 可达于实际目标，原生git祖先检查成功；实际GitHubAdapter.reconcile=delivered、verified_delivery=true。
- 合并前再次读取规则、实际T、源H、CLEAN和当前源检查；使用 `gh pr merge 2 --squash --match-head-commit H`，没有admin绕过、auto-merge排队或伪造能力收据。

## 证据

- `strict-summary.json`：完整汇总
- `strict-protection-request.json` / `strict-protection-enabled.json`：批准范围设置及真实返回
- `strict-behind.json` / `strict-failure.json` / `strict-pass.json`：实际适配器与平台读取
- `strict-ci-{failure,pass}.json` / `.log`：原生CI结果与H/T/C日志
- `strict-delivery.json`：D/tree/祖先/实际目标/规则/main对账
- `strict_manual_merge.sh` / `strict_verify_delivery.py`：执行与核对步骤
- `strict-issue-final.json`：收尾Issue状态
