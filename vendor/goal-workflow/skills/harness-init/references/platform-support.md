# 平台支持与验证边界

## 实现范围与实测状态

- Linux：已在真实 Linux 本地文件系统上运行初始化、公共 Git 目录锁互斥、关联 worktree、停止/恢复及 CLI 测试
- macOS：已实现原生 POSIX 锁和 APFS/HFS 检测，并于 2026-10-01 在真实 GitHub Actions `macos-latest` 开始测试。首轮整体未通过；初始化原生检测、文件创建、锁互斥及安装器测试已执行，其中两项初始化断言因旧 fixture 的 `/var` 与系统规范路径 `/private/var` 不一致而失败。当前 fixture 已规范化路径，并增加目录别名回归；修复后的真实 Mac 完整重跑尚待验证，不能写成 macOS 已验收
- WSL：使用 Linux 路径；仓库须放在发行版自身受支持的本地 Linux 文件系统。Windows 挂载盘常见的 drvfs/9p 被拒绝；没有实际 WSL 的 P0 记录前，不宣称该宿主已经验证
- 原生 Windows：不支持。不要退回软锁、删除锁文件或跳过文件系统检查来运行

安装器可在 macOS 和 Linux/WSL 使用原生 `fcntl.flock`，复制到显式目标的 `.agents/skills`。安装完成仍不等于实际宿主能力已验证。启动后生成的固定 `.venv` 会在升级/回退时保留；业务文件、用户编辑与未知同名技能不覆盖。

## 本地文件系统检查

Linux/WSL 从实际 `/proc/self/mountinfo` 找到目标目录所在的最长匹配挂载点，仅允许 ext2/ext3/ext4、XFS、Btrfs、tmpfs 和本地 overlay 类型。NFS、SMB/CIFS、FUSE、drvfs、9p 和未知类型均阻塞。

macOS 通过已经打开的目录描述符调用系统 64 位 `fstatfs`，同时要求类型为 `apfs` 或 `hfs`，并带有系统返回的 `MNT_LOCAL` 标志。Intel 使用明确的 64 位 inode ABI，Apple Silicon 使用原生 64 位 ABI；无法识别架构、API、布局或文件系统时均阻塞。依据是 Apple 官方的 [statfs 系统调用](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/statfs.2.html) 和 [XNU mount.h 接口定义](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/mount.h)。

## 同一锁 inode

初始化、运行与受控知识修改使用 Git 公共目录下的同一个 `harness.run.lock`。文件先以 no-follow、排他创建方式安全打开；拒绝 symlink、硬链接、非普通文件和非空未知锁。然后使用固定版本 filelock 3.19.1 的原生 `UnixFileLock` 获取非阻塞锁：Linux 用 `/proc/self/fd`，macOS 用 `/dev/fd` 指向已打开的描述符。

取得锁后再次核对库实际持有描述符与原锁的设备号/inode，并确认公共目录内的锁路径没有被替换。锁文件永不由清理逻辑删除。取得锁不证明旧执行已停止：其他关联 worktree 的 checkpoint 或公共执行日志仍须恢复对账。

## 发布前仍须完成

在每个实际使用的 macOS/Linux/WSL 宿主执行原生 Git、知识读写、执行/独立审查、子进程停止、新会话续接，以及该模式的端到端 P0–P5 试点。结构检查、模拟宿主、模拟 Darwin、版本输出和安装成功不能替代这些结果。

首次 macOS CI 还暴露了其他模块的产物路径规范化及 GNU 专用命令依赖问题；它们与初始化 fixture 的字符串断言分开处理。必须在全部修复合并、测试快照一致后重新运行真实平台测试，再更新此处结论。
