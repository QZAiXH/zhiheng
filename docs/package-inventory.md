# 包与资料清单

权威技能源码为 [`skills/`](../skills/zh/SKILL.md)，包含 17 个入口及共享协议、方法资源、模板、Python 脚本与依赖声明。[`tools/build_package.py`](../tools/build_package.py) 从源码生成安装目录 `dist/zhiheng/`；本地 marketplace 指向这个目录。

| 范围 | 源码提交 | 插件安装包 |
|---|---|---|
| `skills/` 的 53 个非缓存文件 | 包含 | 包含 |
| `.codex-plugin/plugin.json`、根 `LICENSE` | 包含 | 包含 |
| `.agents/plugins/marketplace.json` | 包含 | 不包含 |
| `README.md`、`AGENTS.md`、`docs/` 根目录的维护说明和来源表 | 包含 | 不包含 |
| `tools/`、`tests/` | 包含 | 不包含 |
| `dist/zhiheng/package-manifest.json` | 构建生成 | 包含 |
| `docs/evidence/`、`docs/reviews/`、`docs/tasks/` | 本地审计资料，不提交 | 不包含 |
| `.harness/`、虚拟环境、字节码、宿主插件缓存、`.git/` | 不提交 | 不包含 |

生成包有 53 个技能文件、插件元数据、根许可和内容清单，共 56 个文件。[`tools/check_package.py`](../tools/check_package.py) 检查插件元数据、17 个入口、内部资源链接、生成清单和逐文件指纹。实际安装后的缓存曾在隔离 `CODEX_HOME` 中核对为 56 个文件和 17 个入口；本地审计原始材料不构成目标项目运行依赖。

源码交付保留根 MIT 声明，三张来源表见[来源说明](sources.md)。Python 第三方依赖按 [`requirements.txt`](../skills/zh/scripts/requirements.txt) 由使用者在独立环境安装，不随安装包捆绑。历史审计材料可能包含宿主插件缓存、数据库和其他项目工作副本；如需要共享证据，应单独挑选必要材料、核对许可和敏感信息。
