# Weekly Digest (单仓库/单体)

包含静态前端与后端 Flask 服务，用于生成每周 WDWDLW（Meeting Notes + GitHub Commits + Trello Actions）。

## 目录结构

```
.
├── assets/
│   └── styles.css
├── prompts/
│   └── summary_system_prompt.md
├── src/
│   ├── config.js
│   ├── dragdrop.js
│   ├── github.js
│   ├── openai.js
│   ├── template.js
│   └── trello.js
├── config.js            # 运行时前端配置（window.CONFIG.API_BASE_URL）
├── index.html           # Weekly Digest 单页（仓库根）
├── scripts/
│   └── trello_activity.py
├── webapp.py            # 后端 Flask API
├── requirements.txt
└── .env.example
```

## 本地开发（推荐）

1. 安装依赖并启动后端（端口 8001）：

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填写密钥与 TOKEN
PORT=8001 .venv/bin/python webapp.py
```

2. 启动前端静态服务器（仓库根）：

```
python3 -m http.server 8012
# 访问：http://localhost:8012/
```

> 默认 `src/config.js` 会读取 `window.CONFIG.API_BASE_URL`，若未设置，则回退到 `http://127.0.0.1:8001`。

## 必要与可选凭据

- Trello（必需）：`TRELLO_KEY`、`TRELLO_TOKEN`
- GitHub（可选）：`GITHUB_TOKEN`（提高速率限制）
- OpenAI（可选）：`OPENAI_API_KEY`（使用摘要功能时）

在 `.env` 中设置，上述均由 `webapp.py` 自动加载。

## GitHub Pages 部署（仅前端）

- 仓库设置 → Pages → Deploy from branch → 选择 `main / root`
- 将 `config.js` 中的 `API_BASE_URL` 指向公网后端（HTTPS），或在页面中替换 `window.CONFIG.API_BASE_URL`

## API 路由（后端）

- `GET /api/github/commits`：参数 `owner, repo, branch, since, until`
- `GET|POST /api/trello/meeting-notes`：`boardName, listName, since, until`
- `GET|POST /api/trello/board-actions`：`boardName, since, until, types`
- `POST /api/openai/summarize`：`systemPrompt, input`

## 注意

- 生产部署后端请使用 HTTPS 域名，前端通过 `window.CONFIG.API_BASE_URL` 指向后端。
- 本仓库为单体结构，Pages 仅发布静态前端；后端需独立部署运行。