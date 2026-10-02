# Harness 验收追踪与可行性报告

快照日期：2026-10-01 UTC。依据：用户提供的集成计划 v0.5 第 7 节；首版宿主为 Codex CLI；用户指定保留 `$zh` 为主入口，目标平台为 macOS + Linux/WSL（不承诺原生 Windows）。此报告是滚动记录，不能替代最后一次发行物冻结后的复跑。

## 当前可选 Controller 提交：仅普通功能子集完成

### 2026-10-02 已派发实现者角色分流

实际 Mac 的 `a453a35` 已通过免费门禁与 fresh live P0，业务实现读取技能/Serena、修改代码并运行 5 项单元测试 exit 0，但模型会话达到 90 秒限制后被停止，改动未提交，没有业务独审/C/D。不能据超时推断发生递归控制器调用或模型提交。

本次只修正普通实现提示与技能入口歧义：已派发执行者优先处理给定 task/worktree，修改/测试后返回，不重启 run/probe/任务循环或创建工作树；controller_commit 不 stage/commit/发布，model_commit 保留旧提交职责。知识和 walkthrough 回传候选说明，未明确授权路径不另写文件。源分支已存在报错改为真实手动停靠说明；没有新增脏实现 resume 入口，recover 不会自动续跑，超时 blocked 门禁不变。

[源码差异](evidence/implementation-role-workflow.patch)与[普通回归日志](evidence/implementation-role-focused.log)：4 项纯 prompt/静态分流测试及既有明确允许 workflow 16 项，共 **20/20 通过，0 跳过，6.505 秒**。原生业务检查/假审阅只属既有普通 fixture；没有新增模型/网络/Mac操作，没有读审提交安全恢复实现或执行暂停用例。该修复不是已确认的超时根因，也不承诺 90 秒完成。运行时/技能字节变化须按新绑定重新验证；旧实机收据不改写。


### 2026-10-02 core.autocrlf 标量优先级修正

实际 Mac 在用户批准的新测试仓库 local=false 后，原检查仍逐来源拒绝被覆盖的 global=input；本轮免费前置正确阻止模型调用，旧实机收据保持 blocked。最小修复只使 core.autocrlf 使用同一有序配置读结果的最后值，缺失按 false。有效 input/true/未知仍拒绝；其它策略、全来源 raw 哈希、来源文件指纹和提交前后漂移检查原样保留，没有新增 Git 读取或修改用户配置。

[精确源码差异](evidence/autocrlf-scalar-priority.patch)仅涉及此选择函数和一次判定。[6 项纯数据回归](evidence/autocrlf-scalar-pure-tests.log)全部通过，0 跳过，0.081 秒；测试通过 AST 仅提取小纯函数，没有导入/执行完整检查脚本、policy_check 或任何原生命令。新增普通测试模块为 `test_autocrlf_scalar_priority`。静态比较确认除此两处文本外 Controller 模块完全不变；原暂停 28 项清单未变，独立安全复核仍未完成。没有模型、网络或 Mac 操作；本次不能标为原生配置兼容性或完整工作流实机通过。


### 2026-10-01 P0 免费前置检查顺序修正

实际 Mac 的旧 `e2af15b` 快照先完成四次真实宿主演练，之后才在 Controller 原生兼容性检查发现继承的 `core.autocrlf=input`，最终收据 blocked，没有业务 H/C/D。该原始收据保持不变；不能因宿主演练已过而忽略转换策略。

本次将已有 Controller 兼容性/CAS、项目 IO、原生 Serena 及 GitHub 基础能力检查排到模型调用之前，复用结果各执行一次，不重置累计预算或扩大权限。 模型名称与调用预算的纯参数合法性先于任何原生探针检查，保留既有具体报错。原模拟 Codex 协议的两项成功夹具显式 mock 免费前置条件，以隔离原有协议断言；缺模型夹具加强为连版本调用都没有发生。确定性必需项失败时报告 `host_dispatch.skipped_due_to_prerequisite`、零调用，并保留原能力 blocked；私有仓库可选自动合并规则缺失不误挡基础流程，host/semantic/activation 未知不形成前置循环。已调度但没有返回报告的宿主调用数标为未知，不伪造零调用。 该费用门禁仅覆盖已经可观测的免费前置条件，不能承诺所有无法 ready 的情况都零费用：model_commit 的模型 Git 写权限仍未知且只读演练无法补齐，未提供 operator semantic 接受证据也会使最终收据 blocked。现有接口未单独确认用户接受部分能力演练的成本取舍。

补充模型参数诊断优先级后，本轮只运行 11 项新增纯 mock 调度回归，以及明确选定的既有普通 P0/能力接线和模拟 Codex 协议测试，共 **68/68 通过，0 跳过，21.952 秒**。[日志](evidence/p0-order-allowed-regressions.log)、[执行清单](evidence/p0-order-allowed-tests.json)、[P0 源码差异](evidence/p0-dispatch-order.patch)。没有真实模型或网络调用，暂停 28 项与受阻独立审查未运行。新增 mock 只验证调度和报告，不能替代修订后实机 P0 或完整双模式验收；旧历史平台及功能证据仍对应其原快照。


### 2026-10-01 初始化夹具后台维护竞态

快照 `2238b5b` 的 Mac ARM core 普通分片出现两项初始化测试失败：dry-run 在调用 initializer 前读取完整目录快照时，`.git/objects/maintenance.lock` 已消失；保留用户配置测试也只观察到该空锁消失。准备阶段 baseline commit 启动 Git 自动后台维护是高可信归因，但没有进程 trace，因此不声称已经直接追踪到创建锁的进程。

最小修正仅对测试 baseline commit 命令附加 `-c maintenance.auto=false -c gc.auto=0`。生产代码、用户/仓库持久配置、完整快照读取与相等断言均未改变，没有忽略错误或删除锁。[本轮明确选择的 test_init_project 模块日志](evidence/initializer-maintenance-fixture-focused.log)记录 Linux 普通回归通过；新夹具字节仍待 Mac CI 复跑，不能用旧平台结果替代。

### 2026-10-01 Mac 普通夹具路径修正

发行快照 `3e0f0ec` 的 Mac ARM 普通 local/GitHub 分片有 7 项停在提交日志匹配断言。夹具用临时目录的非 canonical 路径，与 Controller 规范路径逐字比较；这些用例此前已通过实际 H、父提交、干净工作区及改动范围断言，但后续交付链未因此视为通过。本次只将测试辅助返回值改为 `resolve()`，并补充失败时的 source/argv 诊断；生产运行时完全未改，原有提交数量和证据断言全部保留。

新增 2 项纯 mock/data 路径回归，与明确选定的 local tiny、GitHub tiny 普通链共 4 项通过，0 跳过；[本轮日志](evidence/controller-fixture-canonical-focused.log)。Mac 最新字节仍待真实平台复跑。允许清单现为 39 项，暂停仍为 28 项，共 67 项；没有执行暂停用例或重新开展受阻审查。下文 37 项及其 45 个输入指纹均是修正前的历史快照证据，不能作为本次新夹具字节的完整通过证明。


用户已明确批准模型编辑/测试、Controller 限定任务分支提交的可选分工。`controller_commit` 已实现；缺失模式仍保留 `model_commit` 兼容，新初始化模板显式推荐前者。没有关闭模型 sandbox、扩大其 writable roots，或把 worktree 当作 OS 安全边界。

- **普通功能 37 项通过**，不是无筛选全量验收：28 项普通单元/CLI 接线测试通过，21.923 秒；另 9 项端到端夹具通过，0 跳过，770.826 秒。[28 项日志](evidence/controller-commit-functional-28.log)、[9 项日志](evidence/controller-commit-functional-9.log)、[汇总](evidence/controller-commit-functional-summary.json)
- 9 场景包含 local 三组、GitHub 三组、两项数据保留反例与原生知识三任务链。Git、Serena、产品 CLI 和检查进程为真实执行；模型、语义审阅、GitHub 与网络运输明确模拟。11 次 Controller source commit 已核对，5,542 个归档日志指纹及 837 个能力原始日志绑定已核验；未新增真实模型或外部平台操作
- 45 个相关技能/包/夹具输入在本轮前后 SHA 完全相同：[运行前指纹](evidence/controller-commit-functional-input-sha256.json)、[运行后指纹](evidence/controller-commit-functional-input-sha256-after.json)、[零漂移](evidence/controller-commit-functional-drift.json)。Controller 模块 SHA256：`09715226c3add4294701a364cf3e329a23aaaa283bfe9ddec9284ac29e015fc5`
- **另 28 项保留但暂停，独立安全复核未完成。** [精确允许/暂停清单](evidence/controller-commit-test-scope.json)当前记录四个新增模块共 67 项，仅允许 39 项；该次历史执行为 37 项。测试源与断言没有删除或弱化；本轮通过不能证明暂停边界通过，也不能标为生产安全或整个计划完成
- 新协议拒绝不支持的 hooks/filters/signing、特殊索引/文件和范围外修改；提交身份、literal allowed_paths、固定父提交/tree、原生 expected-old CAS、未知结果及索引恢复均保留记录。实现工作区使用受限 no-checkout/raw-blob 初始化；这不等价于完整 Git checkout/commit 语义。仓库含特殊策略时保持 blocked

### 原生知识写回与后续加载的实际范围

同一普通 local 夹具先完成业务交付 D，再单独审批依赖该 D 的知识任务。知识候选引用 D 中已提交的 `solution.py`、`tests/test_business.py` 和原任务 walkthrough，使用原生 Serena 写 topic、更新 core 链接，再由 Controller 提交并重新检查/审阅、交付知识 D。第三个业务任务的新 worktree 在修改前原生读取 core→topic，其 HEAD 等于知识 D，且无关记忆保留。

候选生成/语义审阅是确定性模拟；记忆内容仅总结实现和已提交测试的断言定义，明确测试源文件不是历史测试执行凭据。没有用需求 SPEC、尚未提交的未来报告或已过期 CI 产物证明“已测试通过”。该链证明原生 promotion/持久来源/后续读回，不证明真实模型总结质量、知识收益或真实两模式 P5。

### 目前应怎样运行回归

在 `zhiheng` 发行仓库根使用 `tools/run-harness-tests.py`，以锁定 Python 分别运行 `--suite core`、`--suite local`、`--suite github`、`--suite knowledge`。`--list` 只用于 collection/分组核对；存在暂停项时 `--suite all` 拒绝执行。不要无筛选执行全部 unittest，也不要把暂停项转交其他环境运行。

启动器仅为合成 fixture 测试进程显式选择 `GIT_CONFIG_NOSYSTEM=1`、`GIT_CONFIG_GLOBAL=os.devnull`，保留临时仓库本地配置并记录环境；不编辑用户配置文件，不更改生产 Git 策略。普通功能分片可分别通过，但汇总仍须标示暂停项和独立复核未完成。

模型侧 Git 权限不能从 Controller IO/CAS 探针推断；`model_commit` 当前缺实际权限证据时 live P0 保持 blocked。新模式仍须当前宿主自身证据；旧快照 receipt 不可移用于新字节。受限提交会对新增范围外缓存停靠，不擅自清理用户文件。只读提交对账仍需原任务/配置绑定及查询预算；预算耗尽或配置更换时保留事实并转人工，不重置预算或重发提交。

以下 406/400/365 等均为**历史快照结果**，不覆盖当前新增协议，更不能抵消暂停项。选入本文的新日志只来自合成 fixture，未包含用户 Mac 原始日志；[公开材料检查记录](evidence/controller-commit-public-artifact-scan.json)保留来源与指纹。

## Mac 实机当前状态（按快照区分）

- **350f178**：真实四项 P0 全部 verified，新 live capability receipt 为 ready。此前 **4c4f131** 因编号读取解析误报的旧 receipt 仍为 blocked，未覆盖或伪改旧记录；两次实际执行与收据不能混写。
- 随后第五次实现模型真实读取 `$zh`、共享路由与 `zh-implement`，但新 implementation worktree 尚未注册 Serena，原生 memory read 被阻塞；H=T，无业务改动、无 D。新增自动注册修复已通过真实原生五项及406整套，尚未以真实模型重验成功闭环。
- 免费官方 workspace sandbox 探针中 `git add` 因 common Git目录 `index.lock: Operation not permitted` 失败，`git commit` 未执行。用户随后批准了可选 Controller 限定提交职责；当前普通功能子集见上文，真实模型＋新提交协议闭环尚未重验。未更改权限或绕过sandbox。
- d538856 的 [Actions 36830812570](https://github.com/QZAiXH/zhiheng/actions/runs/36830812570)：Linux 与 ARM 成功；Intel 后续出现两项 fixture 失败（已退出进程的清理竞态、原生知识假host诊断/预算不足以归因）。当前仅修测试清理与显式原生步骤预算，普通本地 4+5 项已通过，未把旧 Intel 失败改写为通过；新版平台普通分片待验。

- 另有免费官方 workspace sandbox 组件检查：在预先准备/注册的临时 fixture 中，原生 maintenance/core/topic 读取及一条项目 memory 写入/读回共 5 次 exit 0，stderr 为空、字节相等，总 3.007 秒；未新增模型调用或 writable roots。它仅证明该已准备环境的记忆读写权限，不证明安装、首次注册、LSP/MCP 启动或真实模型知识闭环。原 receipt/checkpoint 未更改。

## 历史工作区原生知识修复冻结验证（406 项）

**406/406通过，0跳过，948.933秒，167文件SHA零漂移。** [完整日志](evidence/final-406-tests.log)、[输入指纹](evidence/final-406-input-sha256.json)、[零漂移](evidence/final-406-drift.json)。新增实现worktree在启动宿主前由Controller监督原生Serena注册与已提交spec/core就绪检查；真实原生五项验证实现/审查两工作区读取maintenance/core/topic/nested、恢复注册字节保留、错误阻断宿主。宿主仍明确模拟，无新真实模型调用。

本轮同时通过local三组、GitHub四业务＋两运输隔离（共六项），Mac TMPDIR别名回归包括拒绝任意remote别名。以下400/365记录为更早快照；406及其指纹仅证明当时版本，不包含当前可选提交协议；真实P0/P5边界仍照下文，测试数不能替代实际模型/平台验收。

## 前次冻结验证

**此前实现完整400/400通过，0跳过，649.989秒；163个代码/脚本/测试/docs文件SHA零漂移。** 开启固定真实Serena，覆盖最新ready、编号读取解析、首次wait预算、GitHub五项CLI夹具及local三组场景。[完整日志](evidence/final-400-tests.log)、[输入指纹](evidence/final-400-input-sha256.json)、[零漂移](evidence/final-400-drift.json)。运行结束后仅追加本报告和证据副本；没有新增真实模型或网络操作。

此400项证明当时的分层实现与隔离模拟整链；真实Mac已有四步及P0部分分项，旧4c4f131整体P0收据仍blocked，新350f178 live收据已ready；实际GitHub人工平台验证另列。完整真实双模式P5和原版/增强成本收益对比仍未完成，不能宣称整个源计划全部验收通过。

## 结论

已实现并在隔离夹具中验证若干核心控制、证据、Git、安装及原生 Serena 接缝。当前不能称 P0–P5 完成：云端真实 Codex 启动受阻，用户 Mac 上 Codex 0.159.2 / gpt-6.1-sol low 的真实实现、独立审查、exact-session续接和fresh-context交接四步已执行成功；真实 GitHub 人工平台三组任务与严格保护正向合并已验，但产品自动控制器结合真实模型的两模式完整P5、知识语义闭环及成本对比尚未完成；350f178实机P0 ready后的第五次实现仍阻塞。单元通过、模拟平台或结构就绪不等于完整流程可用。

## 证据等级

- **R**：真实本地 Git / 子进程 / 文件系统 / 锁；对象是临时夹具，不是用户项目
- **N**：固定 Serena v1.7.0 原生 CLI；不是 Codex MCP 激活，也不证明语义 onboarding 完成
- **M-host**：真实进程执行，但模型/审查响应或 P0/知识接缝是明确模拟的夹具；具体哪些被模拟以测试文件说明为准
- **M-gh**：模拟 gh/API 响应或适配器回调，没有访问或修改真实 GitHub
- **G**：真实授权 GitHub 沙盒及实际 gh 适配器；明确区分单项探针与完整模式验收
- **S**：Schema、静态结构、指纹或解析检查；不证明工具真的执行过
- **B-host / B-gh**：真实宿主/真实平台被明确阻塞
- **U**：尚未执行或没有足够证据

表中测试缩写均指 `tests/harness/test_<文件>.py` 的 `test_<方法>`。测试通过只适用于对应列出的范围；每行的剩余缺口不会因为某个相关单元测试通过而关闭。

## 同基线双模式模拟 CLI 补充验收

[详细比较](p5-simulated-cli-comparison.md)及[精确输入/输出指纹与指标](evidence/p5-cli-comparison.json)：相同基线 tree、SPEC、模拟HOST、业务tests与逐任务输出字节；local三组通过，GitHub三组业务＋私有review-only＋运输隔离共5/5通过、0跳过。真实Git/Serena/产品CLI，模型、GitHub响应与网络运输明确模拟。模拟路径实际穿过 run→push-source→create-pr→checks/wait→verify→ready→merge→reconcile→Issue→closeout；依赖后序T=前序D，未交付不建后续分支。

独立审查测试注入：仅允许已提交marker的唯一临时仓库/fixture URL/自有bare及显式simulate_delivery；原始能力checker、收据绑定/原始日志哈希、授权、CI、证据、CAS、真实Git tree/祖先仍运行。原版生产CLI在相同模拟remote场景拒绝，不会得到live ready。Git运输强制file协议，拒绝其他目的地；212份能力日志归档SHA已核实。此为分层模拟控制链，不是完整真实Codex双模式P5。

新增 ready unknown只读对账、首次wait持久预算、metadata exact C合并与D≠C拒绝均有focused回归；Mac原生nl输出兼容采用成功读取命令按文件顺序完整消费输出，独立10项拒绝缺行、额外行、错序、伪读。离线回放不改旧blocked P0收据。

## 实际运行记录

**此前第六冻结回归：365/365 通过，0 跳过，292.201 秒，151 文件 SHA 零漂移。** 已覆盖最后显式 `--disable multi_agent` 与 handoff 精确 cwd/测试 argv/实际 review 日志引用补丁，以及真实固定 Serena、三组本地 CLI 夹具和 D/C metadata门禁。见[最终日志](evidence/final-tests-tests.log)、[输入指纹](evidence/final-tests-input-sha256.json)、[零漂移](evidence/final-tests-drift.json)。后续只追加本报告与证据副本，没有更改实现/脚本/测试。仍不能把分层365项等同于365个真实模型/平台场景。

产品 4c4f131 的 [实际 Actions 36821405306](https://github.com/QZAiXH/zhiheng/actions/runs/36821405306) 六个job全部成功。最后host补丁产品62745d5已推送，[该快照Actions 36822258293](https://github.com/QZAiXH/zhiheng/actions/runs/36822258293)六job全部成功；后续ready/parser/wait/GitHub E2E字节尚未推送CI；外层28项已通过。该CI与真实模型P0/P5是不同验收层。


- 第五冻结轮：**365/365 通过，0 跳过，282.847 秒**，固定真实 Serena 已启用；[完整日志](evidence/freeze-fifth-tests.log)、[148 个输入文件 SHA](evidence/freeze-fifth-input-sha256.json)、[零漂移复核](evidence/freeze-fifth-drift.json)。包含 D/C metadata 最后修复的三分支回归与三组本地 CLI 场景。随后 host argv 明确关闭 multi_agent 与 handoff 精确测试命令/审查日志已补齐；上方最终第六轮重新覆盖全部新字节。

### 用户 Mac 真实宿主四步

实际 Codex 0.159.2，gpt-6.1-sol，low。四个实际模型进程 exit 0：实现修复 calculator.py 并实际复跑两测试；独立审查另会话；返回确切原会话恢复两项 AC；新上下文读取交接与代码并跑测试。耗时依次 29.167 / 30.474 / 18.141 / 49.534 秒，合计 127.317 秒。完整 17 项安装与原生 Serena 版本、注册、记忆读写、引用检查也实际通过。

这次交接被新会话指出缺精确测试命令和审查日志定位，脚本已补齐并完成fake回归及最终整套验证，没有再付费重复该四步；语义 onboarding、宿主激活、原生取消及完整 P0/P5 不能由四步 exit 0 推导。后续原生P0分项：start verified 12.947秒、review blocked 20.396秒（模型正确指出110≠90，nl逐字读取识别误报）、resume verified 18.744秒、cancel verified 23.709秒；18个PID+出生时间确认停止，第二次检查零遗留。这是旧4c4f131记录：receipt保持blocked，parser最初仅离线回放通过；后续350f178重新真实执行四项全部verified并生成新live ready，详见本报告顶部。17 skills在repo enabled；Serena五memory经操作员语义核对、codex context MCP激活及读回通过，后续第五次实现已证明模型读取$zh及路由；未证明完整业务闭环或模型MCP调用。公开 review usage 为 0 不代表零费用，resume usage 为累计；诊断中各步有输出记录 input/cache/output 为 53934/43904/344、35700/30336/350、19749/17792/60、99711/90752/631，并另有零输出响应，不能相加作为精确账单。


- 第四冻结轮：**362/362 通过，0 跳过，348.256 秒**，真实固定 Serena 环境启用；[日志](evidence/freeze-fourth-tests.log)、[141 输入文件 SHA](evidence/freeze-fourth-input-sha256.json)、[零漂移](evidence/freeze-fourth-drift.json)。随后修复 commit-sensitive 任务最终 D≠C 即使同树也不能交付的边界，新增三项模拟平台回归，平台门禁 15/15 通过；因此第四快照不是该最后修复的全套证明，第五/最终第六轮才覆盖。
- 第三冻结轮 312/312 通过，但独立真实 CLI 夹具复跑发现 checkpoint 临时文件与 git status 竞态。已改同文件系统 Git common-dir 原子 staging；确定性暂停 mkstemp 回归确认内部临时文件不可见、用户未跟踪文件仍可见。另补 ignored 用户文件碰撞不能被交付覆盖。
- 真实监督覆盖 Controller 子进程、gh、可变 Git、native Serena；Git/gh 父控制器被杀后，遗留子进程阻止接管的实际进程回归已运行。


- 第二冻结轮：**301 项 unittest 执行通过、0 跳过，243.813 秒**，真实固定 Serena 环境开启；[日志](evidence/freeze-second-tests-20261001.log)、[113 个输入文件 SHA-256](evidence/freeze-second-input-sha256-20261001.json)、[零漂移复核](evidence/freeze-second-drift-20261001.json)。这仍是分层测试集合，不是 301 个真实模型/平台场景。随后发现并继续修复 gh/可变 Git 操作需统一进程监督的接缝，最终版本仍需再验
- 本地小功能、异常路径、前后依赖三组完整 CLI 夹具包含真实 Git、P0组件收据、Serena、验证、授权交付和 closeout；宿主实现/审查是明确模拟，不能代替真实 Codex 任务验收

- 独立聚合运行：2026-10-01，163 个 unittest 执行通过、0 跳过，47.292 秒，见 [完整日志](evidence/independent-tests-20261001.log)。该运行早于随后候选注册/串行入口等修改；不能作为最终冻结版本的测试证明，发行前须重跑。
- 云端稳定 CLI 实际失败日志：[socket 检查阻塞](evidence/codex-stable-cloud-blocker.log)。可在受支持本机运行 [宿主验收脚本](codex-host-acceptance.md)。

- 独立审查新增：runtime_audit、local_audit、workflow_audit、cli_audit；发现并推动修复了跨 worktree 崩溃接管、短父进程遗留子进程、psutil 回收导致超时退出码丢失、崩溃预算清零、旧 JUnit 假绿、交付对账信任被改证据、GitHub 入口缺锁及未知结果误记 observed 等问题。
- 本地组合失败测试真实建立两条分支，分别通过，再验证组合失败且目标引用不变；无 gh 测试在只含 Git 的 PATH 下运行，配置 GitHub remote 仍走 local。
- 原生 Serena 日志中的“12 tests”包含继承导致的重复：7 个独立方法，只有两个专门原生集成场景（生命周期与复制项目注册），不能写成 12 个独立原生场景。测试明确断言 `host_activated=False`、`onboarding_completed=False`。
- 原生测试需要显式设置 HARNESS_TEST_SERENA 与 HARNESS_TEST_SERENA_PYTHON。未设置时跳过是未运行，不能计通过。
- 实际 Codex：本环境 alpha 0.159.0-alpha.7 和官方 npm 稳定版 0.159.3 均进行了正常 read-only `exec` 探针。版本/help 可用；会话启动在 sandbox helper 处失败：`app-server socket directory must be a user-owned directory with mode 0700`。稳定版使用单独 CODEX_HOME/TMPDIR/XDG_RUNTIME_DIR 仍失败，未绕过安全设置，未复制凭据。这是云端阻塞记录；用户 Mac 的真实四步已成功，完整 P0证据另列，不能以版本/help成功替代。
- GitHub：用户已授权 QZAiXH/zhiheng 沙盒 Issue/分支/PR/合并。早期连接器写入 403 是历史结果；正常 gh 路径随后实际创建 Issue #1 / draft PR #2，观察失败 CI → 修复后通过、缺失检查阻断、任务/PR 身份和无保护规则识别。实际目标分支前进而 REST PR.base.sha 仍旧的情况被观察，并由真实目标 SHA 对账判 stale。后续用户已批准测试分支严格保护，真实最终 D、树和祖先已核实。merge_group/队列仍未实测。实现代码的 draft PR #3 与其 OS Actions 是另一条发布测试，不能算 GitHub 模式任务 E2E。

原生清理/重命名/只读补充实测日志：[4 项真实原生测试](evidence/durable-cleanup-20261001.log)。第五项受管项目拒绝无 Controller 的原生调用在后续聚合中验证，不能混入这份较早的四项日志。

已使用运行环境的安装升级/回退实测：[10 技能与原 .venv 保留](evidence/install-used-runtime-20261001.log)。pyvenv.cfg SHA-256 前后相同；这验证文件安装生命周期，不证明 Codex 实际技能调用。


### 真实 GitHub 单项证据

- 沙盒任务：[Issue #1](https://github.com/QZAiXH/zhiheng/issues/1)、[测试 PR #2](https://github.com/QZAiXH/zhiheng/pull/2)
- 故意失败：[CI 36813986425](https://github.com/QZAiXH/zhiheng/actions/runs/36813986425)；修复后通过：[CI 36814509361](https://github.com/QZAiXH/zhiheng/actions/runs/36814509361)
- [实际适配器结果与 SHA 记录](evidence/github-live-summary-20261001.json)：gh 2.46.0，失败/缺失检查阻断、空依赖读取、PR定位、严格规则 unsupported、实际基线移动后旧证据 stale
- 实现发布：[draft PR #3](https://github.com/QZAiXH/zhiheng/pull/3)，此前快照 89751aff8dd22c43d55a4d98d3ef2a10a48dfce9；[初次 macOS/Linux Actions](https://github.com/QZAiXH/zhiheng/actions/runs/36814910293) 尚不能作为最终冻结版本结果，后续更新可能替代该 run


### 与本地相同业务基线的真实 GitHub 夹具

基线 `goal-harness-arithmetic-v1`，GitHub 起点 e1154cc0f6a51c909efb59f9a8bfbbeba801d31a。确定性业务实现，原生 GitHub/CI、人工授权操作；不冒称实时 Codex 开发或产品全自动门禁。

- [人工平台验收](evidence/github-manual-platform-acceptance.md)、[H/T/C/D 记录](evidence/github-arithmetic-summary.json)：PR #7 小函数、#8 异常、#9 前置、#11 后续均已合并，C.tree=D.tree 且 D 可达实际目标，Issue 原生关闭；前置 D 成为后续基线并完成后续验证
- ensure_pr 重复调用复用 PR #11；PR #7 不确定合并响应仅只读对账，未盲重试。原生依赖关系即使前置 Issue closed 仍保留，放行依据是实际交付基线
- [严格保护验收](evidence/github-strict-platform-acceptance.md)、[汇总](evidence/github-strict-summary.json)：PR #2 真实 BEHIND → BLOCKED → CLEAN，最后无绕过的 SHA 约束 squash 合并。C=5497e1dcc34c854376e26228c0216cb398ee6914，D=f58f193260de47d850c7eb97512f8b06b4da49bc，同树 b952d2798258e2b79139dc6635b3dff02f8605fe；D 祖先核实、Issue #1 closed，main 未变
- 负例只观察平台状态与实际失败 CI/适配器结果，没有在 BEHIND/BLOCKED 时发送 merge API；不能写成实际服务器拒绝了一次危险合并请求。真实 merge queue/merge_group 未演练

### 免费私有仓库兼容

`review_only` 允许能力满足后的实现、受控源分支发布、PR 与当前 CI 证明，自动合并停靠人工。规则接口 403 表示不可读取，不冒充没有规则；无规则不阻断全部工作流。7 项模拟私有/403/无规则测试验证能力分层与原生规则权威，未新建外部私有仓库；布尔 rules_verified 不能伪造规则，也不要求用户手填才能使用真实可用规则。

### 真实平台 CI 历史（按快照区分）

实际 Actions run 36815004527：
- [macOS job 110218123308](https://github.com/QZAiXH/zhiheng/actions/runs/36815004527/job/110218123308)：270 项，10 失败 + 26 错误。包括 `/var` 与 `/private/var` 的系统临时目录别名触发产物路径门禁/断言差异，错误路径后的 host_drills 字段传播，以及 GNU timeout/setsid 缺失。两条 CLI journal 测试还是新增能力门禁后的模拟夹具未更新。
- [Ubuntu job 110218123456](https://github.com/QZAiXH/zhiheng/actions/runs/36815004527/job/110218123456)：270 项，仅两条相同的 CLI journal 夹具失败
- 两 OS 的环境/依赖安装及外层 zh 28 项测试通过；这不能抵消底层 Harness suite 失败
- 首轮独立 Linux 聚合也记录了 [270 项中两条失败](evidence/freeze-first-tests-20261001.log)，212.537 秒、0 跳过。两条夹具已在聚合后显式模拟所测能力边界并单独通过，但必须以后续整套重跑为准。该轮还记录一个测试文件变动，[源窗口差异](evidence/freeze-first-drift-20261001.json)，生产 runtime/skill 文件未变

后续 41e15a2 的 run 36818013457：Mac ARM 与 Intel完整 Harness 通过，三平台 review helper 通过；Ubuntu 312 项仅三个 CLI E2E 暴露上述 staging 竞态。[38ba94c2c71aa95ed444b589d7deb884466f4794 的实际 Actions 36820151613](https://github.com/QZAiXH/zhiheng/actions/runs/36820151613)：6 个 job 全部 completed/success，Linux、ARM Mac、Intel Mac 完整 runtime 与 review 聚焦皆通过；此为 snapshot4，不含随后 D/C metadata 最后修复。WSL 未独立实测；最终发行快照须以对应 Actions 为准。

## P0–P6 范围与退出条件

| 阶段 | 当前范围 | 状态/剩余退出条件 |
|---|---|---|
| P0 | 固定源版本、环境与工具探针、CLI 能力与原生知识入口 | 部分；云端真实 Codex 受阻；用户 Mac 实现/审查/续接/新会话四步已验，原生停止分项已验、操作员语义核对已做；350f178新live P0 receipt已ready，模型已读$zh/路由，MCP实际调用与真实业务闭环未证实，GitHub 普通读写/CI 已探针验证；严格规则与人工受保护合并已验；未建立两模式真实任务基线与工期测量 |
| P1 | review helper 退出码、审查失败分支、依赖与文档路由 | 隔离回归已运行；真实 Codex独立review四步探针已验；完整修复循环待验；原生平台依赖及人工交付链已验 |
| P2 | 初始化、自包含资产、合同、运行/状态锁、限额、报告定位 | 隔离控制与安装测试；实际 Codex 技能发现/加载、完整 onboarding 和环境声明仍待验 |
| P3 | 共享串行入口、本地候选/检查/审查门禁、GitHub 适配、证据 | 真实 Git + 模拟 host/platform；真实两模式模型任务闭环与交付前知识语义更新仍待验；本地可选 push 已在真实 bare remote 夹具验证 |
| P4 | 崩溃、遗孤、CAS、对账、预算、持久依据 | 本地故障测试已运行；真实宿主取消已验；平台未知操作与清理后知识完整组合场景待验 |
| P5 | 安装升级/回退；同tree与业务字节的双模式三组CLI模拟链及指标 | 模拟链已通过且有单次local/GitHub耗时与命令数；真实Codex双模式、原版/增强收益及成本/人工对比未完成，P5仍未通过 |
| P6 | 并行 graph、资源隔离与组合验证 | 后续可选，依赖 P5；本次不启动，不计为已实现 |

## 原计划第 7 节逐项追踪

以下保留源场景和必须观察结果，逐行映射当前证据。全部状态均为“限定范围已验证 / 部分 / 未运行”的细分，不存在一栏泛化“全部通过”。

### 共享和模式验收（24 行）

| ID | 原计划场景 | 原计划必须观察结果 | 实际测试 | 等级 | 证据边界/待办 |
|---|---|---|---|---|---|
| A01 | 测试进程返回非零 | 原始失败被保留；任务不取得 verified 状态，不进入交付成功分支；有服务器合并检查时该检查失败 | `runtime_audit.test_failed_command_preserves_exit_code; review_helper.test_nonzero_tests_preserved; local_audit.test_failed_combination_check_does_not_move_target; github-live-summary-20261001.json` | R+G | 本地原始失败保留/目标不动已验；真实沙盒 CI failure 被实际 adapter 判 blocked；完整双模式交付链另验 |
| A02 | 审查修复轮数耗尽仍有 Blocking 问题 | 转为 blocked，保存发现与下一步；不会继续走通过分支 | `workflow_audit.test_blocking_review_never_verifies; workflow_audit.test_exhausted_review_attempts_never_fallthrough` | M-host | 固定审查响应验证门禁；真实 Codex 审查/修复循环未验 |
| A03 | 必需检查被跳过、报告缺失或测试意外执行零条 | 验收不完整；不能凭其他检查为绿而通过 | `local_audit.test_zero_skipped_and_missing_reports_fail; local_audit.test_stale_successful_junit_cannot_certify_new_command; contracts.test_tool_zero_evaluation_blocks` | R+S | 真实命令/XML 与结构门禁已验；业务测试覆盖需逐任务确定 |
| A04 | 验证后源提交、目标基线、规范或检查配置变化 | 旧证据被判过期，重新验证受影响部分及最终组合 | `local_audit.test_target_moves_and_old_evidence_is_rejected; local_audit.test_stale_spec_checks_and_environment_fail; workflow_audit.test_reissued_capability_receipt_cannot_revive_old_task_evidence; github-live-summary-20261001.json` | R+M-host+G | 实际本地/远端目标漂移、合同/观察环境绑定拒绝已验；真实 GitHub 合并/队列最终竞态仍待验 |
| A05 | GitHub 原生依赖或本地文件依赖尚未完成 | 两种模式分别验证：依赖任务不启动，能说明具体阻塞来源 | `tasks.test_missing_dependency_never_silently_dropped; github.test_native_plus_body_closed_and_cross_repository; cli_e2e.test_dependency_handoff_then_native_delivery_boundary_reconciliation` | R+N+M-host+M-gh | 本地完整串行夹具验证依赖未交付不得启动、交付进入基线后续跑；宿主模拟。真实原生依赖、人工前后置交付与基线释放已验；产品模拟CLI全链已验，真实模型自动链未验 |
| A06 | 依赖在首批分页外、已关闭、不存在或成环 | 分别查询并解释；不漏读、不自动删除约束，closed 不直接等同交付成功 | `github.test_pagination_filters_prs; github.test_cycles_block_even_closed; tasks.test_cycles_and_self_dependencies; tasks.test_missing_dependency_never_silently_dropped` | M-gh+R | 分页/closed/缺失/环在夹具中验证；真实 API 分页未验 |
| A07 | GitHub 创建 PR 成功后进程中断 | 恢复时核对并复用已有 PR，不重复创建 | `github.test_create_recovery_reuses_pr_after_timeout; cli_audit.test_unknown_return_value_blocks_repeat_mutation` | M-gh | 模拟已成功但响应超时与重复阻断；完整模拟CLI PR复用已验；真实创建后中断未验 |
| A08 | 本地提交成功或可选推送成功后进程中断 | 恢复时核对已有提交和引用，不重复生成提交或误报交付 | `local_audit.test_successful_remote_push_with_old_intent_is_reconciled; local_audit.test_nonnumeric_id_candidate_and_authorized_ff_delivery; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget` | R | 真实本地 bare remote 已成功但保留旧 intent 的恢复已验；精确引用对账复用并更新 observed，不重推 |
| A09 | 目标分支已合入但 checkpoint 未更新 | 查询实际 Git/平台状态，正确推进，不重复合入 | `cli_e2e.test_dependency_handoff_then_native_delivery_boundary_reconciliation; workflow_audit.test_cli_reconcile_is_idempotent_after_actual_delivery; workflow_audit.test_cli_reconcile_cannot_promote_tampered_evidence` | R+N+M-host | 真实本地 Git已交付但checkpoint未更新的CLI对账、重复对账和假证据拒绝已验；真实平台合并尚未发生 |
| A10 | checkpoint 损坏或发生过期修订号回写 | 不覆盖有效状态；明确报告冲突或进入恢复流程；运行互斥另按下表验收 | `runtime_audit.test_stale_revision_and_attempt_cannot_write; runtime_audit.test_mode_mismatch_and_corruption_preserve_checkpoint` | R | 隔离真实 CAS/坏文件保留已验 |
| A11 | 重新打开会话，只提供交接文件 | 能复原验收条件、决策理由、未决问题和下一步，无需重读整段聊天 | `用户Mac真实四步：fresh-context交接读取代码并运行tests` | 真实host | 两项AC新会话恢复已验；当次指出精确测试命令/review日志定位缺口，脚本已修且模拟回归通过，未再付费重演该四步 |
| A12 | 提出无证据或与现有规范冲突的知识候选 | 保留候选与冲突，不能直接写成永久事实 | `knowledge.test_temporary_untracked_external_and_traversal_rejected; workflow_audit.test_native_not_ready_cannot_reach_checks_or_review` | R+M-host | 持久依据结构拒绝已验；规范冲突的模型语义判定未验 |
| A13 | Serena 重命名、断链及只读记忆 | 验证原生引用更新及只读项边界；断链报告进入验收失败，不能只看 CLI 退出码 | `durable_cleanup.test_native_rename_propagates_mem_reference; durable_cleanup.test_guarded_native_edit_and_rename_preserve_neighbors; durable_cleanup.test_native_tool_readonly_boundary_is_respected; knowledge.test_native_lifecycle_preservation_and_broken_reference` | N+R | 原生 rename 引用传播、受控 edit/rename、只读拒绝和断链转换均实测；不宣称对直接文件编辑形成权限隔离 |
| A14 | 重复初始化或项目已有维护模板 | 已有模板和记忆不被覆盖；全局与项目模板的有效来源明确 | `init_project.test_user_config_is_preserved_and_needs_review; knowledge.test_native_lifecycle_preservation_and_broken_reference` | R+N | 重复初始化/自定义维护模板保留已验；个人全局模板优先级仍需实际宿主确认 |
| A15 | 新工作区读取已交付知识 | 注册/激活已有项目后读取入库记忆与 ADR，文件保持原样；不依赖原机器的个人全局记忆或缓存 | `durable_cleanup.test_cleanup_then_clean_clone_keeps_native_knowledge_and_sources; knowledge.test_copied_native_project_requires_registration` | N+R | 真实干净 Git clone、全新 Serena home 注册/core/ADR/报告字节与持久引用已验；Codex 新会话语义读取仍被宿主阻塞 |
| A16 | 知识依据已改变但引用仍有效 | 语义复核发现不一致并更新/撤回结论；引用检查通过不能代替该复核 | `knowledge.test_durable_reference_binds_actual_git_commit_and_bytes; workflow_audit.test_mutated_check_log_invalidates_evidence` | R | 字节漂移可检出；有效链接下事实矛盾的语义复核未验 |
| A17 | 技能、依赖锁文件或运行环境变化 | 预检识别差异，旧验证不会被直接沿用 | `capabilities_audit.test_actual_skill_instruction_edit_expires_receipt; capabilities_audit.test_host_script_and_config_changes_expire_receipt; capabilities_audit.test_installed_code_or_dependency_fingerprint_drift_is_rejected; contracts.test_every_binding_component_rejects_drift` | R+S | 真实 SKILL.md/宿主脚本/配置漂移拒绝已验，代码/锁摘要比较通过模拟漂移验证；真实宿主升级全过程待验 |
| A18 | 全新安装、选择性安装、重复初始化、升级回退 | 入口可用、版本可追溯、用户修改保留、恢复旧版本后状态兼容性明确 | `install.test_full_chain_install_copies_only_packages; install.test_selective_harness_is_self_contained; install.test_upgrade_and_rollback_verify_manifest_and_backup; install.test_user_edit_blocks_upgrade_and_rollback` | R | 隔离安装测试已验；真实安装后 uv 可用；已用过的 .venv/lib64 符号链接回归已修复，实际 10 技能升级/回退成功且 pyvenv.cfg 哈希不变。Codex 真实发现/调用、旧 checkpoint 迁移兼容另行验收 |
| A19 | 本地仓库没有 remote、没有 gh、没有 GitHub 凭据 | 完整跑通任务、依赖、实现、验证、交付和恢复，不调用 GitHub API | `cli_e2e.test_tiny_function_real_run_validate_deliver_closeout; cli_e2e.test_exception_path_explicit_validate_then_deliver_closeout; cli_e2e.test_dependency_handoff_then_native_delivery_boundary_reconciliation; local_audit.test_local_github_remote_does_not_require_gh_or_push` | R+N+M-host | 本地无remote三类CLI夹具跑通实现/验证/交付/恢复/closeout，宿主实现/审查模拟，原生Serena与Git实际执行；真实Codex仍阻塞 |
| A20 | 本地模式配置了指向 GitHub 的 remote | 仍按 local 执行，不查询 Issue/PR/CI；默认不推送 | `local_audit.test_local_github_remote_does_not_require_gh_or_push; init_project.test_default_local_never_uses_remote_or_gh` | R | PATH 无 gh 且 remote 指向 GitHub 的本地候选/检查/交付已验；不执行 push |
| A21 | GitHub 认证或必需检查查询失败 | 保持失败或阻塞，不自动切换 local，不将未知结果当作通过 | `github.test_native_query_failure_not_fallback; github.test_timeout_and_malformed_fail_closed; github.test_checks_exact_sha_skipped_missing; workflow_audit.test_github_local_checks_alone_never_mark_generic_verified` | M-gh | 模拟认证/查询/未知结果及 GitHub 本地验证不提前标 verified 已验；真实 gh 已验证失败/通过/缺失检查；早期403已解决。平台查询失败/未知路径仍由模拟补充 |
| A22 | 恢复时配置模式与 checkpoint 不一致 | 拒绝混用进度，明确指出匹配配置或新建运行的路径 | `runtime_audit.test_mode_mismatch_and_corruption_preserve_checkpoint; contracts.test_mode_mismatch_and_no_inference` | R+S | 真实 checkpoint 模式不符拒绝已验 |
| A23 | 本地任务文件被重命名或验收内容改变 | 稳定 ID 仍可定位；要求改变时重建输入并使相关旧证据失效 | `tasks.test_rename_keeps_id_and_reports_but_refreshes_source_path; workflow_audit.test_task_change_invalidates_evidence; reports.test_local_nonnumeric_rename_stable` | R+M-host | 稳定 ID/源路径更新/要求指纹失效已验；完整任务改名后续跑未验 |
| A24 | 本地模式显式启用向指定 remote 推送 | 验证过的提交推送到配置位置，并核对远端引用；不使用托管平台 API | `local_audit.test_explicit_local_push_uses_actual_bare_remote_and_reuses_commit; local_audit.test_successful_remote_push_with_old_intent_is_reconciled` | R | 真实本地 bare Git remote、显式授权、目标引用核对、重复复用与漏写 checkpoint 对账已验；未测试外部网络认证/服务商传输 |

### 六项补充验收（17 行）

| ID | 补充项 | 原计划场景 | 原计划必须观察结果 | 实际测试 | 等级 | 证据边界/待办 |
|---|---|---|---|---|---|---|
| B01 | 补充 1 | 新项目只生成 `memory_maintenance`，记忆列表非空且引用检查无错 | 知识仍未就绪；执行原生 onboarding 指引后，实际写入并读取 `core` 与必要主题才通过 | `knowledge.test_maintenance_only_is_not_core_readiness; knowledge.test_native_lifecycle_preservation_and_broken_reference; workflow_audit.test_missing_native_knowledge_config_refuses_without_mock` | N+R+M-host | 模板不等于就绪、原生写读已验；Codex 执行完整 onboarding 未验 |
| B02 | 补充 1 | 重复 onboarding；已有项目从干净副本注册 | 保留已有知识和规则；不依赖个人全局记忆；缺必要入口或读取失败时明确阻塞 | `knowledge.test_native_lifecycle_preservation_and_broken_reference; knowledge.test_copied_native_project_requires_registration` | N | 模板保留/副本注册已验；必要主题语义充分性待实际宿主 |
| B03 | 补充 1 | 单模块任务与跨模块任务分别启动、续接新会话 | 先提供名称和入口，再按需读正文；单模块任务不默认加载无关主题，跨模块任务可扩展读取；两者的强约束和验收条件完整 | `workflow-contract.md 与 knowledge.md 静态要求；无成功模型读取轨迹` | S+B-host | 单/跨模块按需读取、新会话强约束完整保留未执行 |
| B04 | 补充 2 | 两个入口同时从同仓库或其关联 worktree 启动 | 只有一个进入有副作用执行；另一个不修改 Git、不创建 PR，也不启动第二个执行者 | `runtime_audit.test_live_controller_blocks_related_worktree; init_project.test_common_lock_excludes_another_worktree; cli_audit.test_active_controller_prevents_github_mutation` | R+M-gh | 真实 filelock/关联 worktree 互斥已验；GitHub 写操作仅模拟回调 |
| B05 | 补充 2 | 控制进程退出但子进程仍在写文件；随后尝试恢复 | 先识别并停止旧执行；无法确认停止就 blocked。PID 被复用时不误杀无关进程，不删除锁文件强行接管 | `runtime_audit.test_orphan_record_blocks_recovery_from_related_worktree; runtime_audit.test_reused_pid_identity_is_not_owned; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget` | R | 真实 SIGKILL+遗孤+接管阻断+预算保留已验；不误认 PID 出生身份 |
| B06 | 补充 2 | 已结束的 attempt 迟到回传结果；持锁期间人工修改 Git 引用 | 旧结果不能推进状态；人工改动被交付前复核识别，锁不被误当作全局写保护 | `runtime_audit.test_stale_revision_and_attempt_cannot_write; local_audit.test_target_moves_and_old_evidence_is_rejected; workflow_audit.test_cli_reconcile_is_idempotent_after_actual_delivery` | R+M-host | 迟到回写/外部引用变化/已交付重复对账均验证；重复对账不会把有效 delivered 降为 blocked |
| B07 | 补充 3 | 验证通过后，源不变而目标分支前进；或 PR head 改变 | 原验证不能直接用于交付；GitHub 由严格检查/队列和 head 约束阻止过期交付，本地重建并验证候选 | `local_audit.test_target_moves_and_old_evidence_is_rejected; github_platform_gate.test_stale_pr_base_cannot_hide_actual_target_branch_advance; github-live-summary-20261001.json` | R+M-gh+G | 真实远端 branch ref 前进而 PR.base 快照滞后已观察；对账 stale。最终 wrapper 实际 ref 查询回归已加入；真实严格保护 BEHIND/BLOCKED/CLEAN 及正向合并已验；负例未发送 merge API |
| B08 | 补充 3 | 两条分支各自通过但组合测试失败 | 两种模式都阻止成功交付；本地目标引用保持原值，保存组合失败证据 | `local_audit.test_failed_combination_check_does_not_move_target` | R | 两分支单独命令通过、真实组合命令失败且目标不变已验；GitHub 组合场景未真实执行 |
| B09 | 补充 3 | GitHub 使用合并队列；或 squash/rebase 改变最终 SHA | 核对真实受检对象和必要 `merge_group` 结果；排队不算完成；实际交付可关联已验证内容，否则重新验证或阻塞 | `github.test_merged_queue_requires_merge_group_evidence; github.test_delivered_commit_not_target_reachable_is_blocked; github.test_source_target_delivery_semantics` | M-gh+G | 真实 squash D/tree/祖先已验；commit-sensitive D≠C拒绝有独立模拟回归；真实 merge_group/rebase 尚未验 |
| B10 | 补充 3 | 本地交付前目标工作区变脏或不能快进；人工合入内容与候选不符 | 保留用户文件且不强制改引用；实际合入事实单独记录，未核实内容不解锁下游 | `local_audit.test_dirty_target_is_preserved; local_audit.test_target_moves_and_old_evidence_is_rejected; workflow_audit.test_cli_reconcile_cannot_promote_tampered_evidence` | R+M-host | 脏目标保留、引用漂移、假证据阻断已验；真实人工非等价合入仍需场景 |
| B11 | 补充 4 | 本地任务使用非数字 ID、修改标题或重命名任务文件 | note-it、walkthrough、交付报告持续定位同一任务和产物；不请求 Issue 号，不执行 gh，不生成假 PR 链接 | `reports.test_local_nonnumeric_rename_stable; tasks.test_rename_keeps_id_and_reports_but_refreshes_source_path; local_audit.test_local_github_remote_does_not_require_gh_or_push` | R | 非数字 ID/改名报告映射/无 gh 已验 |
| B12 | 补充 4 | 两任务重复 ID/输出路径；GitHub 原有报告继续更新 | 本地预检报告冲突；GitHub 的 `docs/issue#XXXX.html`、原 walkthrough 与 Issue/PR 链接保持兼容 | `reports.test_duplicate_and_path_collision; reports.test_github_legacy; contracts.test_casefold_and_ancestor_report_collisions` | R+S | 本地冲突和 GitHub 原格式报告已验；真实 Issue/PR 链接平台访问不在此测试内 |
| B13 | 补充 5 | 测试或审查不退出、派生子进程；执行中收到取消 | 限额触发或取消后停止派发与交付，保存证据，并在支持的停止路径中确认本次执行及子进程退出 | `runtime_audit.test_timeout_preserves_failure_and_budget; runtime_audit.test_sigint_cancels_owned_execution_and_records_reason; runtime_audit.test_short_parent_cannot_leave_unobserved_same_group_child; review_helper.test_review_timeout_is_failure` | R+M-host | 真实本地超时/SIGINT 取消/子进程清理已验；Mac真实取消18 PID+birth确认停止且再次零遗留已验；此为独立P0分项，旧整体receipt仍blocked |
| B14 | 补充 5 | CI/队列长期 pending；多次恢复或重试 | 到总等待/尝试上限后停止等待并保存原因，恢复不重置已消耗预算；未取得通过证据不交付 | `runtime_audit.test_budget_survives_new_controller; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget; contracts.test_github_wait_limits_required` | R+S | 本地预算/恢复及产品CLI模拟CI pending累计wait已验；真实CI/队列长期pending循环未验 |
| B15 | 补充 5 | PR 创建/合并请求超时，或取消时远端操作已执行 | 查询真实结果再更新状态；不重复操作，不将“本地已停止等待”表述为“远端已取消” | `github.test_create_recovery_reuses_pr_after_timeout; github.test_authorized_merge_pending_then_timeout_reconciled; cli_audit.test_unknown_return_value_blocks_repeat_mutation` | M-gh+G | 模拟创建/合并超时与未知阻断已验；真实人工 PR #7 不确定响应只读对账已验，真实远端撤销未验 |
| B16 | 补充 6 | 候选知识只有临时日志、会消失的提交或即将到期的 CI 链接 | 持久化必要依据并核实后才固化；归档未完成则保留候选，不能靠引用检查无错绕过 | `knowledge.test_temporary_untracked_external_and_traversal_rejected; knowledge.test_durable_reference_binds_actual_git_commit_and_bytes` | R | 临时/未入库/外链-only 拒绝和提交证据已验；已有外部持久归档迁移未演练 |
| B17 | 补充 6 | 清理 `.harness/runs/`、模拟 CI 产物到期，再从干净仓库副本读取 | 记忆、ADR 和必要报告仍可访问并支持结论；本地场景无需 GitHub；不能访问的必需依据有明确复核结果 | `durable_cleanup.test_cleanup_then_clean_clone_keeps_native_knowledge_and_sources` | N+R | 实际删除 runs 与模拟到期 CI 目录，再真实 clone、原生注册/read core、校验 ADR/报告字节；缺失引用明确拒绝。语义结论支持度仍非模型实测 |

## `$zh` 外层集成

已独立审阅 zhiheng-current 的七个 `$zh*` 路由与共享 harness-integration 合同：旧资料保留为来源，增强流程只用一个 checkpoint/锁/知识写入口。统一安装器把七个入口和十个增强组件作为 17 项安装；任一 zh 选择自动补齐完整依赖，不覆盖未知同名技能。

[外层仓库测试日志](evidence/zh-wrapper-tests-20261001.log)：28 项通过（22 原独立流程回归 + 6 统一安装/依赖检查），6.674 秒。该日志使用刷新前 vendor 快照，发行前仍需按最终 vendor 复跑；并不证明真实 Codex 已发现 `$zh`。另有[新模型上下文显式加载演练](evidence/zh-forward-20261001.md)：在 local+无网络要求下因缺锁定依赖缓存而阻塞，未绕过能力门槛、未改 tracked 文件、未调用 GitHub；属于路由/拒绝门禁证据，不是 CLI 自动加载或正常开发通过。

## 目标平台边界

Linux/WSL 使用 POSIX 原生锁/进程与本地文件系统；历史版本的 Linux 及 macOS ARM/Intel 曾在实际 Actions 通过，WSL 未独立执行。当前可选提交协议的新版平台普通功能子集需按明确允许清单单独验收，暂停项不计通过。macOS首轮失败保留历史，修复后的真实rerun与Mac用户宿主四步成功分列；原生停止已分项验证，350f178新live P0 receipt已ready，业务实现仍因原生worktree/提交权限边界未完成。单纯模拟 sys.platform 或分支覆盖不得写为 macOS 实测。`$zh` 是对外主入口；goal-workflow 上游技能作为内部流程组件，不改变用户已选入口。

## 继续验收需要的条件

1. 用户Mac真实四步及17安装已通过，350f178原生P0 live ready及取消已验证，模型已读$zh/路由；用户已批准可选提交职责方案；还需完成新协议真实实现/交付闭环，不能更改权限；不重跑已完成昂贵四步，也不放宽系统安全策略。
2. 已授权 GitHub 沙盒 QZAiXH/zhiheng 的普通 gh 路径已工作；不需再次登录或选择仓库。测试分支严格保护、人工实际合并、D与受检内容关联和Issue收尾已验；真实merge queue/merge_group尚未验，如需修改队列规则须单独授权。不要把实现 PR #3 的 Actions 当完整模式验收。
3. 同基线双模式模拟三组与文件/时间/命令数已记录；继续完成真实模型/平台两模式及原版/增强首次通过率、返工、人工、耗时和成本比较，不把模拟差值当生产收益。
4. 发行前冻结文件、保存允许功能子集的日志和版本指纹，再按明确清单复跑；暂停项和独立安全复核未完成不得隐藏。安装/升级/回退测试在临时目录中成功不证明用户已有安装或历史 checkpoint 已迁移。
5. 尚未有证据的功能应继续实现/测试，或明确记录阻塞并请求所需帮助；不能以手册描述、schema 合格、模拟返回或原生组件探针充当 P5 发布证明。
