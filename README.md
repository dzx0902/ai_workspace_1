# AI Workspace

本仓库保存本地 AI Workspace / AstrBot / Paper Radar 的源码和 Docker 部署骨架。

## 首次部署

```bash
cp .env.example .env
```

然后编辑 `.env`，填入 API Key、模型路径、工作目录路径等本机或服务器配置。

## 启动

```bash
docker compose up -d --build
```

## 迁移提醒

- `.env`、数据库、日志、PDF、上传文件、AstrBot 运行数据不会提交到 Git。
- 如果要把本地历史数据一起迁移到服务器，请用 `rsync` 或压缩包单独迁移 `astrbot-data/`、`paper_radar/data/`、`paper_radar/notes/` 等运行目录。
- `docker-compose.yml` 当前仍包含部分 WSL/Windows 路径，迁移服务器时需要按服务器实际目录调整挂载路径。
