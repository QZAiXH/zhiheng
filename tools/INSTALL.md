# 安装、升级与回退

统一入口为 `$zh`。完整安装为七个 zh 入口加十个增强组件；项目内和用户级均使用 Codex 的 `.agents/skills` 布局。

## 新安装

安装脚本需要 Python 3.11+；增强运行环境另由 uv 按锁文件安装。下面只复制技能与自包含资产，不修改业务代码、凭据、checkpoint，也不执行技能。

```bash
# 用户级：写入 ~/.agents/skills
python3 tools/install-harness.py --destination "$HOME" --dry-run
python3 tools/install-harness.py --destination "$HOME"

# 或项目级：写入目标项目的 .agents/skills
python3 tools/install-harness.py --destination /path/to/project
```

--destination 必须是已存在的项目目录或用户 home，不能传 `.agents/skills` 本身。现有同名未托管目录、用户改过的托管文件、未恢复事务或活动 workflow checkpoint 都会使安装安全停止。返回成功只证明文件布局已安装；请在实际 Codex 会话确认 `$zh` 发现与加载来源。

完整增强工作流使用统一安装器，旧 `tools/install.py install` 不再用于此版本，因为它只会安装七个入口而遗漏执行依赖。旧 `restore` 保持可用，操作历史见[旧安装与恢复说明](INSTALL-legacy.md)。

## 升级和回退

```bash
python3 tools/install-harness.py --destination "$HOME" --action upgrade
python3 tools/install-harness.py --destination "$HOME" --action rollback
```

升级先核对安装清单与文件指纹，保存可验证的上一代，再替换受管技能。回退从本地已验证备份恢复前一代，不撤销已经发生的代码提交、PR、合并或任务变更。实际执行生成的专用工具 .venv 与 Python 缓存不当成用户代码改动，升级/回退会保留已有工具环境；之后仍需 uv sync --locked 与能力重验，不能沿用旧验证。

## 已安装旧七技能版本

旧版与新增受管集合不是同一份安装清单，不能仅凭同名目录自动接管。选择以下一种：

1. 在新的项目级技能目录安装本增强集合，在该 Codex 会话检查有效加载源；不要同时启用用户级原版与项目级同名增强版
2. 用旧版原始备份和恢复工具审查旧安装，保留本地改动，再明确迁移到增强集合

遇到用户修改、未知版本或 checkpoint 时先保留文件并对账，不自动覆盖或删除旧技能。此限制保护已有内容，不代表旧任务已迁移。

## 选择性安装与单一入口

```bash
# 仅诊断/初始化资产；不宣称安装了完整 zh 工作流
python3 tools/install-harness.py --destination /path/to/project --skills harness-init
```

选择任一 zh 入口会自动包括完整协作依赖，日常仍用 `$zh`。单独安装增强组件时补足 harness-init。升级不能静默增删已管理技能集合；改变集合需要明确的新安装/迁移。

## 运行前核验

依实际技能加载位置读取 harness-init 的说明，用其 assets/project 的 uv.lock 安装工具。配置 local/github、限额、检查命令、目标分支和持久证据；完成原生 Serena 接入与 Codex P0 探针后再执行任务。能力收据和实际证据未齐时阻塞，不靠 ready:true 放行。

macOS、Linux 与 WSL 需要分别实际验证原生锁、文件系统和停止路径。Windows 原生、网络共享文件系统等未验路径不自动支持。WSL 优先使用其 Linux 文件系统工作区。真实模型/平台未验证的项目不能靠模拟报告解锁交付。

## 执行环境与权限

worktree 是代码工作目录/分支的隔离，不是容器或操作系统安全边界。多数 Git refs 与默认仓库配置仍在多个 worktree 之间共享，见 [Git 官方说明](https://git-scm.com/docs/git-worktree)。共享开发环境可用于可信的专用开发机；仍需区分任务端口、项目依赖和测试数据库，并保留锁、证据和目标分支核验。

Codex 宿主决定文件/网络权限，安装技能不会改变个人权限配置。应显式选择并实际验证权限档，参见 [Codex 官方权限说明](https://learn.chatgpt.com/docs/permissions)。正常 workspace 档可能保护 Git 元数据；不能从控制器可写 Git 推断模型也可写。扩大权限前必须明确影响范围，worktree 不能保护工作目录之外的个人数据。

- 模型提交路径：只在实际宿主已证明具备所需 Git 写能力时使用
- 控制器提交路径：模型保留既定沙箱；按本次批准的文件名单，由控制器执行受限提交。该路径有自身仓库策略限制和验证要求，不能据此假定支持所有 Git hooks、filters 或签名配置

换用共享环境不代表其它审核限制消失。无论哪种路径，都不能把尚未执行的检查标记为通过；当前版本的真实与模拟覆盖范围以验收报告为准。
