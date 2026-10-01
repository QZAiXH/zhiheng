# GitHub 算术夹具人工平台验收摘要

结论：三组同业务基线的 native Git/GitHub/Actions 人工操作验收完成。4 个测试 PR 已合并到专用隔离分支，4 个测试 Issue 已按 completed 关闭。未执行产品自动合并入口，未生成真实 P0 收据；不能据此宣称真实 Codex 宿主核心 CLI E2E 或 strict/queue 服务端门禁验收通过。

## 共同基线与运行方式

- 仓库： https://github.com/QZAiXH/zhiheng
- 共同 GitHub 夹具基线：`e1154cc0f6a51c909efb59f9a8bfbbeba801d31a`，业务标识 `goal-harness-arithmetic-v1`
- 与本地 `tests/harness/test_cli_e2e.py` 共用 pending solution、RUN_TESTS、spec 字节及 HOST 业务断言；逻辑文件 SHA-256 见 `arithmetic-baseline-manifest.json`。GitHub 夹具位于 `.goal-harness-fixture/`；这里复用确定性夹具实现，不是真实 Codex 实现/审查宿主。
- 操作证据：真实 `gh 2.46.0`，实际 GitHubAdapter 读取，真实 Actions 检查，拉取真实 PR merge candidate 后再次运行本地业务测试。
- 合并方式：人工/operator sandbox，fresh H/T 与实际成功检查核对后 `gh pr merge --squash --match-head-commit H`；没有 `--admin`、保护规则修改或绕过产品自动门禁。目标未配置 strict，故不能提供原子目标分支门禁证明；合并后通过实际 D/tree/可达性对账补验结果。

## H / T / C / D

H=PR 源提交；T=验收时独立读取的实际目标分支；C=真实 GitHub 测试合并提交；D=实际 squash 交付提交。

### 小功能 add
- PR：https://github.com/QZAiXH/zhiheng/pull/7
- Issue：https://github.com/QZAiXH/zhiheng/issues/4，closed/completed
- CI：https://github.com/QZAiXH/zhiheng/actions/runs/36816230422，success
- H：`9a0d72aa29cdbe1b6ce46699b2de726c9393b260`
- T：`e1154cc0f6a51c909efb59f9a8bfbbeba801d31a`
- C：`3a7cd1ea0b30022326360c2fb94fa4aaa6b8040b`
- D：`fa121b94508f98f5d0a26bf337216bca8b487342`
- C.tree = D.tree：`6b803fad67bc33f41c28a966f35d812ad575322f`
- D 可达于实际目标：`True`；实际适配器 reconcile：`delivered` / verified_delivery=true

### 显式异常 divide
- PR：https://github.com/QZAiXH/zhiheng/pull/8
- Issue：https://github.com/QZAiXH/zhiheng/issues/5，closed/completed
- CI：https://github.com/QZAiXH/zhiheng/actions/runs/36816238379，success
- H：`fb54ddb24548b31ff101dd9f16f2bd35ea6ffddd`
- T：`e1154cc0f6a51c909efb59f9a8bfbbeba801d31a`
- C：`708cfa58f6d7f744939d5a0651d6865f312f507a`
- D：`9549531a13d24aa2094eebaa6f5169c5632de91e`
- C.tree = D.tree：`513c555da091c89d3b001290e55b5f05f2e1074a`
- D 可达于实际目标：`True`；实际适配器 reconcile：`delivered` / verified_delivery=true

### 依赖组：前置 add
- PR：https://github.com/QZAiXH/zhiheng/pull/9
- Issue：https://github.com/QZAiXH/zhiheng/issues/6，closed/completed
- CI：https://github.com/QZAiXH/zhiheng/actions/runs/36816247821，success
- H：`73f4ce2ff452b9fe79c1601144b3854a91d04320`
- T：`e1154cc0f6a51c909efb59f9a8bfbbeba801d31a`
- C：`8c82bea3c065c1d4967bd12c06038bc9b5d0a207`
- D：`04dbb2b708ad9b5138351d71269271f46a864f38`
- C.tree = D.tree：`da30bcf1f6072d634654e839102300ae9c1271d6`
- D 可达于实际目标：`True`；实际适配器 reconcile：`delivered` / verified_delivery=true

### 依赖组：后续 double_sum
- PR：https://github.com/QZAiXH/zhiheng/pull/11
- Issue：https://github.com/QZAiXH/zhiheng/issues/10，closed/completed
- CI：https://github.com/QZAiXH/zhiheng/actions/runs/36818832255，success
- H：`bc8f25dd556f2c3ee435ea387242a5313e0abfbe`
- T：`04dbb2b708ad9b5138351d71269271f46a864f38`
- C：`41f1705de8eadb9f5289226f42928fd768241b29`
- D：`f689606da6a6ebabea92a69c9df26ceb6ea7d79b`
- C.tree = D.tree：`82eaeb85e12952f30857f70e1abd5fb558030c84`
- D 可达于实际目标：`True`；实际适配器 reconcile：`delivered` / verified_delivery=true

## 依赖与重复操作证据

- Issue #10 原生 blocked_by #6；适配器读取 `source=native`，正文依赖与原生依赖去重为一个前置任务。
- 实际交付前，无 delivery 记录、只有 closed Issue 或只有 verified 状态，局部确定性 predicate 均拒绝释放；这些 negative-state 输入是本地断言，未伪装成远端已发生的状态。
- 对共同 pending 基线尝试确定性 dependent 实现，明确失败 `dependency absent from baseline`，工作树保持干净。
- PR #9 实际 D/tree/目标可达性验证后，才允许 dependent 从 D9 开始；Issue #6 关闭后，真实原生依赖仍可读取，只有真实 verified delivery 记录才能让 predicate 通过。
- 最终 D9=`04dbb2b708ad9b5138351d71269271f46a864f38` 是 D11=`f689606da6a6ebabea92a69c9df26ceb6ea7d79b` 的实际 Git 祖先，原生 git merge-base --is-ancestor 返回 0。
- 真实 GitHubAdapter.ensure_pr 首次创建 dependent draft PR #11；第二次返回同一 #11，未产生重复 PR。证据 `dependent-pr-created.json`。
- PR #7 合并请求返回过程出现拒绝/EOF，未盲目重试；随后只读对账确认已合并，再验证 D/tree/可达性。

## 未完成边界

- 算术验收结束时 Smoke #2 曾保持待批状态；后续已获单独批准并完成严格保护平台验收，见 `strict-platform-acceptance.md`。这不改变本报告算术组使用人工未保护隔离目标的边界。
- 本轮不改 main，不扩展新测试，不自动清理分支或 Issue。
- 本报告不建立真实 Codex P0/core CLI E2E、产品自动合并、queue/等待型 auto-merge 验收；strict平台场景另见后续独立报告。

## 原始证据索引

- `arithmetic-summary.json`：汇总及全部 refs/CI/Issue 状态
- `arithmetic-checks.json`：实际适配器 PR/目标/C/tree/检查结果
- `manual-pr{7,8,9,11}-delivery.json`：实际交付核对及适配器 reconcile
- `arithmetic-run-*.json` / `.log`：实际 Actions 结果及 source/target/candidate 日志
- `arithmetic-dependencies.json`、`dependency-after-delivery.json`：释放前后证据
- `manual_merge_one.sh`、`manual_verify_delivery.py`：具体命令与核对逻辑
- `arithmetic-issues-final.json`：4 个 Issue 最终 closed/completed
