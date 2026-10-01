# 在你的 Codex CLI 环境完成真实宿主验收

云端实际尝试过 alpha 0.159.0-alpha.7 与官方稳定版 0.159.3；二者在模型会话启动前均被 sandbox helper 的 socket 目录检查阻塞。版本/help 可运行不代表模型或技能可执行。不要关闭 sandbox、放宽 socket 权限或复制认证文件来绕过该错误。

## 需要什么

- 已通过正常流程登录、可在当前机器使用的 Codex CLI
- Linux/macOS，或 Windows 的 WSL；Python 3 和 Git
- 普通用户权限即可；不需要 GitHub 仓库或账号，不需要改用户配置
- 模型步骤会消耗正常 Codex 额度，并创建一个用于精确续接的测试会话

## 先只准备夹具

在此增强仓库根目录运行：

```bash
python3 scripts/codex-host-acceptance.py
```

此命令创建并保留一个新的临时 Git 仓库，放入故意有错的加法函数、两条验收测试及最小宿主探针技能。它实际确认初始测试失败；不启动 Codex、不使用模型、不修改你的项目或全局设置。

## 再运行真实模型步骤

```bash
python3 scripts/codex-host-acceptance.py --run-models --timeout 180
```

如需指定已安装的 CLI 路径：

```bash
python3 scripts/codex-host-acceptance.py --run-models --codex /absolute/path/to/codex --timeout 180
```

每次自动创建一个全新夹具；可用 `--output /new/nonexistent/path` 指定新目录。脚本不会删除产物。单个模型步骤超时 180 秒，超时即保存输出、停止本次进程组并退出，不继续后续步骤。不能将这种进程组停止描述成所有可能后台/远端工作都已取消。

实际步骤：

1. 记录 CLI 版本与帮助，在 repo-local `.agents/skills` 加载一个最小探针技能；它不是完整 Harness 技能验收
2. 用普通 `workspace-write` sandbox 修复夹具，仅允许更改 calculator.py；随后由脚本重新运行真实单元测试，确认其他文件未被改动
3. 单独运行 Codex `exec review --uncommitted`，用 `read-only` sandbox；保存完整响应供独立人工复核
4. 从本次 `thread.started` 事件取唯一 session ID，只续接该 ID，不使用 `--last`；检查两个验收 ID 没有丢失
5. 启动新的只读上下文，仅通过 handoff.md 与夹具恢复要求、约束、状态和下一步

## 如何判断结果

输出目录中的 summary.json 记录命令、目录、超时、真实退出码、运行耗时和产物位置。每一步有独立 stdout/stderr 文件。

- `prepared`：仅生成夹具，没调用模型
- `blocked`：步骤未完成；读 reason 与对应 stderr，先解决正常环境问题再新开一次探针
- `host_steps_executed_review_requires_inspection`：列出的宿主步骤执行成功；仍需检查审查响应、读取轨迹与交接内容，不是 P5 通过

测试会话属于本次新建夹具。脚本不读出认证信息、不复制凭据、不改 config.toml、不改安全设置、不推送、不创建 PR、不合并，也不会把它指定为生产环境。

本机最小宿主探针通过后，还必须通过用户选定的 `$zh` 主入口运行完整增强工作流：Serena 原生 onboarding、任务/检查合同、串行循环、真实取消与恢复、两模式各三组代表任务。GitHub 平台验收需要另外的明确沙盒仓库授权。不要用这个小探针替代 [完整验收矩阵](harness-acceptance.md)。

## 本次对脚本的验证

已实际运行准备模式并编译 Python；夹具初始失败测试和 Git 基线创建成功。模型路径的命令选项对照了官方稳定版 0.159.3 的 exec / review / resume 帮助。云端真实模型启动仍被上述环境错误阻塞，脚本模型执行分支未在本次云端宣称通过。

官方技能加载说明：[Build skills](https://learn.chatgpt.com/docs/build-skills)；CLI 命令说明：[Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
