# AI Workspace

本仓库保存 AI Workspace 的 AstrBot 接入层、agent 管理层雏形、RAG/Dev/文件处理相关源码，以及 Docker 部署编排。

Paper Radar 已拆分为独立仓库，默认放在本仓库同级目录：

```text
/home/dzx0902/ai_workspace
/home/dzx0902/paper_radar_agent
```

当前组件边界记录在 `config/agents.yaml`：

- `paper-radar`：外部独立 agent 服务。
- `workspace`：当前仓库内的 RAG / 文件 / 网页 / 视频处理服务。
- `dev`：当前仓库内的代码开发辅助 agent。

## 首次部署

```bash
cp .env.example .env
```

然后编辑 `.env`，填入 API Key、模型路径、工作目录路径等本机或服务器配置。

如果 Paper Radar agent 不在 `../paper_radar_agent`，请修改：

```env
PAPER_RADAR_AGENT_PATH=/path/to/paper_radar_agent
```

## 启动

```bash
docker compose up -d --build
```

## 迁移提醒

- `.env`、数据库、日志、PDF、上传文件、AstrBot 运行数据不会提交到 Git。
- 如果要把本地历史数据一起迁移到服务器，请用 `rsync` 或压缩包单独迁移 `astrbot-data/` 等运行目录。
- Paper Radar 的运行数据现在归独立仓库或 Docker volume 管理，源码更新也在 `paper_radar_agent` 仓库内完成。
- `docker-compose.yml` 当前仍包含部分 WSL/Windows 路径，迁移服务器时需要按服务器实际目录调整挂载路径。
