# 安装、更新与恢复

从源码仓库根目录运行以下命令，需要 Python 3.10+。七个技能必须一起安装并保持同级目录，安装工具会检查所需资源与相对链接。使用示例见 [README](../README.md)。

## 用户级安装

以下 Bash 命令适用于 Linux、macOS 或 WSL。源码仓库应放在安装目录和备份目录之外。

```bash
python3 tools/install.py install \
  --target "$HOME/.agents/skills" \
  --backups "$HOME/.local/state/zhiheng/skill-backups" \
  --dry-run

python3 tools/install.py install \
  --target "$HOME/.agents/skills" \
  --backups "$HOME/.local/state/zhiheng/skill-backups"

python3 tools/validate.py "$HOME/.agents/skills"
```

`--dry-run` 只输出计划，不创建目录或改动文件。正式安装成功后保存输出中的 `backup_id` 和 `backup` 路径，恢复需要使用该 ID。

示例选用 Codex 当前的用户级 skills 目录，项目级目录及发现方式见 [OpenAI 官方文档](https://learn.chatgpt.com/docs/build-skills)。新装后可打开新会话检查 `$zh`；如果未发现新技能，重启 Codex。

### 参数与现有默认值

| 参数 | 用途 | 不传时的实际行为 |
| --- | --- | --- |
| `--source` | 包含七个技能的源码根目录 | 使用 `install.py` 所在 `tools/` 的上一级 |
| `--target` | 宿主实际发现 skills 的目录 | 使用 `/root/.codex/skills` |
| `--backups` | 独立备份目录 | 使用 `/root/.codex/skill-backups` |
| `--dry-run` | 预览安装或恢复 | 不传则实际执行 |

当前脚本不根据 `HOME` 或 `CODEX_HOME` 自动调整默认值，所以建议始终显式传入 `--target` 和 `--backups`。源码、目标、备份目录必须互不包含；工具会拒绝重叠目录和其检查到的不安全符号链接布局。

如果宿主已经从其他目录加载本集合，更新时应继续使用那个目标目录，避免重复安装同名技能。此工具仅管理 `--target` 下的安装，不会迁移其他发现目录里的副本。

## 项目级安装

将七个技能安装到目标项目的 `.agents/skills`，备份仍放在技能发现目录之外。例如，先将下列项目路径替换为实际路径：

```bash
python3 tools/install.py install \
  --target /path/to/project/.agents/skills \
  --backups "$HOME/.local/state/zhiheng/project-skill-backups" \
  --dry-run
```

核对输出后移除 `--dry-run` 执行。项目内安装是否提交到项目仓库，由该项目的约定决定；安装脚本本身不会提交文件。

## 更新和旧版迁移

在干净的源码仓库中更新，然后沿用原安装目标与备份路径重新安装：

```bash
git pull --ff-only
python3 tools/validate.py
python3 tools/install.py install \
  --target "$HOME/.agents/skills" \
  --backups "$HOME/.local/state/zhiheng/skill-backups" \
  --dry-run
```

核对后移除 `--dry-run` 执行。只更新 Git 源码不会同步已复制的 skills。

每次正式安装会创建唯一备份，完整保留目标目录中已有的七个同名技能及旧 `zhiheng` 目录，然后替换为新集合并移除目标中的旧 `zhiheng`。其他技能不受影响。安装工具不修改业务项目的 `.zhiheng/` 知识、`AGENTS.md` 或旧钩子配置。

## 恢复某次安装

将 `BACKUP_ID` 替换为安装输出中的实际值，`--backups` 必须指向那次安装使用的备份根目录：

```bash
python3 tools/install.py restore BACKUP_ID \
  --backups "$HOME/.local/state/zhiheng/skill-backups" \
  --dry-run

python3 tools/install.py restore BACKUP_ID \
  --backups "$HOME/.local/state/zhiheng/skill-backups"
```

恢复会先把当前受影响的技能目录存入该备份下唯一的 `restore-archives/` 子目录，再还原安装前的版本，并移除那次安装新引入的技能。因此安装后的手工修改仍可从归档找回。恢复已完成的同一个备份不会重复操作；无关技能保持不变。

恢复目标从备份的 `manifest.json` 读取；可选传入 `--target` 核对，但不能借此恢复到另一个位置。这是还原整次安装，不是只卸载其中一个技能。

## 中断与排查

每份备份的 `manifest.json` 保存原目录集合、安装阶段及恢复归档。安装或恢复中断后，保留现场并使用报错中的备份 ID 执行 `restore`；恢复再次中断可以重试。同一目标存在未完成迁移时，新安装会被阻止。首次 manifest 写入前的备份复制失败不会改动已安装技能。

| 现象 | 检查方式 |
| --- | --- |
| 权限不足或写入 `/root` 失败 | 显式传入当前用户有权限的 `--target`、`--backups` |
| 找不到 `$zh` | 确认宿主发现目录、七个 `SKILL.md` 是否存在；检查同名副本并重启宿主 |
| 报缺少资源或相对链接失效 | 重新获取完整仓库，运行 `python3 tools/validate.py` |
| 报未完成迁移 | 使用报错中的备份 ID 和原备份根目录恢复，再重新安装 |
| 新版本没有生效 | 核对源码提交、实际安装目录；`git pull` 后需重新执行安装 |

备份和恢复归档在确认无需回退前应保留。报问题时提供脱敏错误、命令、系统及版本信息，见 [贡献指南](../CONTRIBUTING.md)。
