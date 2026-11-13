# 安装与使用

## 本地安装

源码仓库以 `skills/` 为唯一技能权威；先生成不含运行证据和宿主缓存的 `dist/zhiheng/` 插件包。包内 `.codex-plugin/plugin.json` 声明 `./skills/`，本仓库的本地 marketplace 指向该生成目录：

```sh
python3 tools/build_package.py
codex plugin marketplace add /absolute/path/to/zhiheng
codex plugin add zhiheng@zhiheng-local
codex plugin list --json
```

以上方式在隔离的 `CODEX_HOME` 下检查安装缓存与 17 个入口。也可以在项目本地复制完整 `skills/` 到该项目的 `.agents/skills/`；公共资源位于 `skills/zh/`，必须连同阶段入口安装。重建包后重新安装/刷新本地缓存以应用修订。脚本需要 Python 3.11+ 和系统 Git（`git --version` 应可在 `PATH` 中运行）；无 Git 元数据的项目也需要 Git 程序来核对工作区版本。在独立虚拟环境安装实际插件目录中的工具依赖：

```sh
python3 -m venv /absolute/path/to/zhiheng-tool-venv
/absolute/path/to/zhiheng-tool-venv/bin/python -m pip install -r /absolute/path/to/installed/zh/scripts/requirements.txt
```

后续三个命令均使用该虚拟环境的 Python，不改变业务项目依赖。

显式请求可以使用 `$zh` 协调整项工作，或 `$zh-review`、`$zh-spec` 等单独完成阶段。自动选择由各 `SKILL.md` 的描述触发；阶段单独请求以本阶段终点交付，不要求补做完整流水线。需要持续跟踪时沿用项目现有本地任务入口；没有约定时创建 `docs/tasks/T-YYYYMMDD-NNN/README.md`。模板位于 `skills/zh/assets/templates/`。

```sh
/absolute/path/to/zhiheng-tool-venv/bin/python /absolute/path/to/installed/zh/scripts/harness.py validate --task docs/tasks/T-20261112-001/README.md --format json
/absolute/path/to/zhiheng-tool-venv/bin/python /absolute/path/to/installed/zh/scripts/harness.py snapshot --task docs/tasks/T-20261112-001/README.md --scope scope.json --output manifest.json
/absolute/path/to/zhiheng-tool-venv/bin/python /absolute/path/to/installed/zh/scripts/harness.py compare --task docs/tasks/T-20261112-001/README.md --manifest manifest.json --format json
```

从实际安装的 `skills/zh/` 位置解析脚本路径；项目工作目录只保存任务记录。`scope.json` 的具体字段和例子见工具的 `--help` 与 `tests/`。结果退出码：0 为未发现需处理问题，1 为记录缺口或差异，2 为输入、依赖或运行错误。清单只覆盖所声明的来源、文件和证据；外部环境仍从项目实际入口核对。

项目发布方式由项目自己的文档、流水线和运行配置决定。发布任务应从项目知识入口取得环境、迁移、验证和恢复方式。真实项目选择、真实迁移和环境发布由用户后续安排。
