# 可选 Controller 提交职责

`host.commit_mode` 只有 `model_commit` 与 `controller_commit` 两个值。已有配置省略时仍按 `model_commit` 解释；库不会自动扩大 Controller 的写权限。新 `goal-harness init` 草稿明确推荐 `controller_commit`，但 `ready` 仍是 false，任务路径和验收合同仍须另行明确并批准。普通 `harness_check scaffold` 的兼容默认不变。

## 范围配置与模型边界

在已经批准的 bundle 中明确配置：

```json
{
  "config": {"host": {"commit_mode": "controller_commit"}},
  "tasks": [{
    "id": "task-arithmetic",
    "allowed_paths": ["src/calculator.py", "tests/test_calculator.py", "docs/arithmetic.md"]
  }]
}
```

这里只展示新增字段，不能作为完整可执行 bundle。保留完整 SPEC、AC、source/target、检查、知识与报告映射。

- `allowed_paths` 是 1..500 个唯一、精确、仓库相对的文件名；需要新增的文件也须逐个列出
- 不接受目录授权、通配符、Git pathspec magic、绝对路径、`..`、符号链接、Git 元数据或 Controller 状态文件；NFC/大小写折叠后碰撞也拒绝
- 不从 `git status`、任务描述、report mapping 或模型提议自动推断/补全授权。报告、知识和 ADR 若需要修改，也必须事先列入实际批准范围
- 此模式下模型只在现有 sandbox 中修改允许的文件并测试，绝不执行 stage/commit，也不改 index、HEAD、ref、Git config/hooks 等元数据。旧技能中要求模型提交的通用步骤在此模式下由 Controller 接管
- 不关闭或放宽 sandbox，不增加绕过权限参数，不声称模型获得 Git 写权限。`model_commit` 模式保留旧责任划分，但仍受真实能力门禁约束

这里的提交范围控制是框架协议与事实审计，不是新增的 OS 安全边界，也不把任意可配置宿主当作可信隔离层。实际 Codex `workspace-write` 对 common Git 目录的保护需要独立宿主证据；原生 CAS 不能证明该隔离。模拟 host 只是受信测试替身，不证明恶意宿主无法改写 Controller 证据。

路径/任务、检查、模式或合同发生变更，必须按正常合同批准与证据过期规则处理，不能在失败后扩大允许范围使检查变绿。

## 受限的原生实现

这是审计后构建精确对象并更新限定任务引用的受限能力，不等同于任意项目的 `git commit`。

1. 启动模型前检查任务 source 是当前隔离工作区的明确分支，与 target 不同；要求 HEAD/index/工作区符合初始干净状态，保存 task/config、父提交、允许路径和元数据快照
2. 实现工作区的 Serena 原生注册、已提交 SPEC/core 和知识就绪检查仍在模型启动前完成。提交分工不代替知识就绪，也不更改相关失败边界
3. 模型停止后重新审计内容与 Git 元数据，只接受授权文件的精确字节。禁止模型自行 stage/commit、修改 hooks/config/index/ref 或引入范围外改动
4. 在同一个运行锁、Controller 执行监督和累计预算下构建 blob/tree/commit，对明确 task source ref 以实际父 SHA 作 expected-old CAS。不会更新用户 target 分支，不使用 force/reset/clean，不覆盖工作区内容
5. 持久记录 actor、operation ID、source、父 SHA、tree/commit、改动路径和内容指纹；成功提交成为后续候选的实际 H，再走原有组合验证、独立审查、修复预算和交付门禁

原生 policy preflight 在任何提交写入前拒绝不受支持的活动 hooks、内容 filters、签名要求、外部 diff/merge/editor 等执行型配置，以及特殊 index/链接/内容转换策略。不会偷偷禁用 hook、签名或内容转换来伪装支持。遇到拒绝应停靠说明，不自动修改项目或个人 Git 配置。

显式自定义 `core.hooksPath` 也拒绝。通过原有策略检查后，只有受控 mutation 命令临时传入 Controller 自有的空 hooks 目录作为竞态保护；该目录必须是当前 UID 拥有、真实且空、权限精确为 0700，并在任务工作区之外。此参数不写入 repo/global 配置，也不修改原有目录权限。原始 hooks/policy 在操作前后仍核对；并发插入 hook 不会被执行或视为成功，若 CAS 已发生则保留事实并只读对账，绝不重试提交。

## 受限实现工作区初始化

仅 `controller_commit` 模式使用受限初始化：先把目标固定为实际 T，确认只含支持的普通文件/执行位且没有内容转换策略，再由原生 `worktree add --no-checkout` 和 Git 对象/索引命令准备工作区。按已验证对象的原始字节逐文件无覆盖落盘，并核对最终索引/tree/内容与固定 T 一致。对象批量读取、文件数、总字节和时间均有界；未支持的 checkout 语义不会被模拟为成功。失败或策略漂移保留已存在的分支/工作区用于核对，不重试创建或强制清理。旧 `model_commit` 初始化保持原行为。

受限协议对自身相关 Git 命令显式关闭 fsmonitor、自动签名等执行型能力作为检查后竞态防线，仍先拒绝预存特殊策略，且不写 repo/global 配置；配置变化即阻断。此范围是提交与实现工作区准备。现有候选合并/交付的原生 Git 流程不构成抵抗任意同 UID 并发写者的安全沙箱，不能把这些检查宣传成整个系统的 OS 隔离。

## 未知结果与恢复

先保留操作日志、原始输出和已有对象；对象创建、引用 CAS 或 index 同步结果未知时，不重发本次提交，不以新的 operation ID 绕过未决状态，也不删除锁强行接管。

```sh
goal-harness commit-reconcile --bundle <bundle> --run <run-id> --task <task-id> --operation <operation-id>
goal-harness commit-recover-index --bundle <bundle> --run <run-id> --task <task-id> --operation <operation-id> --authorize
```

`commit-reconcile` 只核对实际对象、ref、index、工作区与已有操作的对应关系；允许在能力收据过期时查询事实，不重新授予执行/验证/交付权限。CAS 未被证明或状态不匹配保持 blocked，不重试 ref 写入。

只有实际 ref 已指向本次精确 commit、内容和策略仍匹配，而 index 同步尚未完成时，才可显式授权 `commit-recover-index`；它要求新鲜能力收据，只完成已证明提交的 index 同步，不创建新 commit、不重试 CAS、不改工作区文件。先按照现有 `recover` 流程证明旧进程均已停止，不能把停止等待等同于 Git 写入已撤销。

## P0、费用与证据限制

`controller_commit` 模式新增必需能力 `controller_commit`：先检查实际仓库的原生策略，再在新建的隔离 Git 仓库中执行真实 blob/tree/commit 构建、成功的 expected-old CAS、错误 expected-old 被拒绝且引用不变、后续正确 CAS 和引用清理。所有子命令都归实际项目 Controller 监督并消耗其现有预算；不增加模型调用，不访问网络，不触碰用户分支。隔离仓库使用自己的合成身份和空模板，不更改实际项目策略。

stdout/stderr、结构化证明及 SHA 保留在 capability receipt 引用的归档中；成功且停止已确认才删除隔离目录，失败或未知则保留目录和证据。预算不足会阻断，不创建新 Controller 来清零项目预算。

探针的 `host_boundary` 独立保留 `status: not_observed` 与证据缺口说明，不会因为 CAS verified 或一个声明布尔值而升级，也不为此新增不可完成的付费模型前置探针。

这项免费探针只证明 Controller 在该环境的原生对象/ref 操作，不证明模型拥有 Git 权限、不证明真实任务完成，也不证明实际宿主中的“模型修改 → Controller 提交 → 独立审查”整链已成功。实际仓库/实现工作区政策与范围仍须在每次提交前检查。

`model_commit` 模式新增 `model_git_commit` 未验证项：现有 Controller 文件写入、隔离 CAS、版本/help 和只读宿主演练均不足以证明模型沙箱可 stage/commit。当前 P0 不为此调用额外付费模型；在没有实际受支持的模型提交证据前，live receipt 保持 blocked。隔离 simulation 的旧模型模式仍可用于明确模拟的测试，不能作为真实交付许可。

两种模式仍需要原来的真实 start/review/resume/stop、知识和授权语义审阅等证据。更新实现、技能、配置或模式会使旧 receipt 过期。历史 350f178 的 ready 仅记录旧字节和当时已测能力，不能证明模型 Git 权限，也不能直接授权新提交分工。

## 当前验证边界

新增提交分工的原生功能和模拟 CLI 回归，与真实宿主验证分别记录。独立安全复核目前未完成；作者测试或常规回归通过不能替代独立复核，也不能据此宣称生产安全已经证明。
