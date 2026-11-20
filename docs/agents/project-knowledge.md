# 项目知识

| 项目 | 值 |
| --- | --- |
| 项目标识和专用账号 | `qzaixh-zhiheng` |
| 普通用户和角色 | `codex`，`user` |
| 服务端点 | `http://192.168.31.141:1933` |
| 项目资源根 | `viking://resources/qzaixh-zhiheng` |
| 普通凭据文件 | `~/.config/openviking/projects/qzaixh-zhiheng.key`（`0600`） |

从仓库根目录核对普通身份。该项目的工作树复用这套绑定。

```sh
python3 -B plugins/zhiheng/skills/setup-harness/scripts/project_access.py verify \
  --url http://192.168.31.141:1933 --account qzaixh-zhiheng --user codex \
  --key-file "$HOME/.config/openviking/projects/qzaixh-zhiheng.key"
```

Codex 加载项目 `.codex/config.toml` 后，通过 `http_headers_helper` 读取上表的普通凭据文件。直接在桌面端打开本项目或在仓库内启动 `codex` 即可使用 `find` 和 `read`。

## 按目标版本读取

- 知道完整 URI 时直接调用 `read`。否则从工单提取场景和目标版本，调用 `find`，传入 `target_uri: "viking://resources/qzaixh-zhiheng"` 和 `level: [2]`，再 `read` 命中的原文。
- MCP 不可用时，用相同普通身份调用原生 HTTP。请求带 `Authorization: Bearer <project-key>`。查询用 `POST /api/v1/search/find`，JSON 包含 `query`、上述 `target_uri` 与 `level`。回读用 `GET /api/v1/content/read?uri=<encoded-uri>`。
- 按目标版本核对原文的结论、范围和确认来源。用 `git show <revision>:<path>` 打开适用的 Git 条文并引用文件、章节和修订。遇到冲突时按目标修订及已经确认的决定核对。仍待决的条款交给外环，受影响的验收项保持待处理。
- 有明确版本范围时按范围执行。未指定版本的决定，从确认时排定的下一次常规交付开始生效，包括正在开发的下一版本，直至被取代或撤回。把生效版本写进知识原文。没有版本号时用迭代或交付工单标识。例如下一版 `v1.8` 正在开发时，新规则适用于 `v1.8`。`v1.7` 热修使用原规则，除非明确批准该场景回移到 `v1.7`，届时同时核对新决定和回移批准。无法确认目标时保留相应验收项待处理。

## 提交与恢复

经确认、可复用的规则写入 `viking://resources/qzaixh-zhiheng/knowledge/` 下的稳定 URI，正文包含结论、适用版本和场景、确认来源，以及 Git 文件、章节和修订。业务含义变化时使用带版本的 URI，并记录适用范围和替代关系。一次性结果和未确认观察留在工单。获准入库的完整研究报告放在 `viking://resources/qzaixh-zhiheng/research/`。外环批准复用的已验证经验放在 `viking://resources/qzaixh-zhiheng/episodes/`，按场景查找并读原文和证据。

1. 写入前，在原 GitHub Issue 的正文、评论或从工单可访问的持久附件中保存精确 URI、目标版本或修订、确认来源和完整获批 UTF-8 正文。获批原件是文件时，以保持原字节的附件保留，并在工单链接。重新打开工单及正文，确认后续会话可读。同一 URI 同时由一人负责提交。
2. 新写或重试时先用普通凭据读取精确 URI。原文逐字节相同时结束。经认证的原生 HTTP `404` 确认资源缺失时，进入下一步。另有明确授权的纠错，核对当前原文和适用范围后再进入下一步。内容冲突、鉴权失败或服务不可用时，在原工单保留已批准正文、实际错误、待同步状态和下一步。
3. 直接从已批准的 UTF-8 原件读取 `content`，保留换行和末尾换行。如果记录了摘要值，发送前同时核对摘要值。取得步骤 2 的写入依据后，用同一普通凭据发一次 `POST /api/v1/content/write`，JSON 含 `uri`、`content`、`mode: "replace"`、`processing_mode: "vectors_only"` 和 `wait: true`。用 `GET /api/v1/content/read` 回读同一 URI，将响应中的正文字符串以 UTF-8 编码后与获批原件逐字节比较。在原工单登记验证通过的 URI，并单独记录索引结果。后续交接依赖搜索时，再验证 `find` 能查到该原文。
4. 回读未能确认原文时，保留工单上的完整原件，记录实际错误、待同步状态与恢复动作。从步骤 2 继续。其余验收项可根据已核对的原始证据继续验证。
