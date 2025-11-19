# Weekly Digest Web

静态前端用于生成每周 WDWDLW（Meeting Notes + GitHub Commits + Trello Actions）。本目录包含两页：

- 根页面：`index.html`（DOCX 上传 → Trello 卡片创建）
- 子页面：`weekly-digest/index.html`（每周数据汇总预览）

## 本地开发

- 启动后端（Flask，端口 8001）：
  - 在项目根目录执行：`PORT=8001 .venv/bin/python webapp.py`
  - 后端需要 `.env` 中的 `TRELLO_KEY/TRELLO_TOKEN`，已支持自动加载
- 启动前端静态服务器（任选其一）：
  - 在 `web/`：`python3 -m http.server 8012` → 打开 `http://localhost:8012/weekly-digest/`
  - 在 `web/weekly-digest/`：`python3 -m http.server 8000` → 打开 `http://localhost:8000/`

> 提示：`weekly-digest/src/config.js` 默认指向 `http://127.0.0.1:8001`，无需额外配置即可调用后端。

## 依赖说明

- GitHub：可选 `GITHUB_TOKEN`（提升速率限制），在后端 `.env` 配置
- Trello：必须 `TRELLO_KEY/TRELLO_TOKEN`，在后端 `.env` 配置
- OpenAI：可选 `OPENAI_API_KEY`（如果使用摘要功能），在后端 `.env` 配置

## 部署（GitHub Pages）

- 创建仓库并推送本目录内容为仓库根
- 在仓库设置中启用 Pages（Deploy from branch → `main`/root）
- 如后端在公网部署，请将 `web/config.js` 的 `API_BASE_URL` 设置为后端公网地址

## 目录结构

```
web/
├── README.md
├── config.js           # 根页面运行时配置（DOCX 上传页）
├── index.html          # DOCX 上传页
└── weekly-digest/
    ├── assets/
    │   └── styles.css
    ├── index.html      # 每周 Digest 页面
    ├── prompts/
    │   └── summary_system_prompt.md
    └── src/
        ├── config.js   # 子页运行时配置（含后端地址回退）
        ├── dragdrop.js
        ├── github.js
        ├── openai.js
        ├── template.js
        └── trello.js
```