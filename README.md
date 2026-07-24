# AI Workspace

本仓库保存 AI Workspace 的 AstrBot 接入层、agent 管理层雏形、RAG/Dev/文件处理相关源码，以及 Docker 部署编排。

## 仓库结构

日常维护时主要看这些目录：

```text
ai_workspace/
├── src/
│   ├── astrbot_plugins/ai_workspace/   # AstrBot 聊天入口和命令适配层
│   ├── dev_agents/                     # 代码开发辅助 agent
│   ├── scripts/                        # RAG、文件处理、网页/视频处理核心脚本
│   └── services/rag_api/               # Workspace HTTP API
├── config/
│   └── agents.yaml                     # agent 注册表和组件边界
├── docs/                               # 架构、部署、迁移文档
├── Dockerfile.astrbot                  # AstrBot 插件镜像
├── docker-compose.yml                  # 本地/服务器组合部署入口
├── .env.example                        # 环境变量模板
└── README.md
```

这些是本地运行态目录，不属于源码管理：

```text
astrbot-data/ input/ inbox/ uploads/ processed/ notes/ notes_out/
kb/ logs/ repos/ tasks/ tmp/ paper_radar/
```

它们已经被 `.gitignore` 排除，并通过 `.vscode/settings.json` 在 VS Code Explorer 中隐藏。需要查看历史数据时，可以临时关闭 VS Code 的 `files.exclude`。

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

## AstrBot 论文命令

平台部署后，飞书里的 AstrBot 入口可以直接管理论文 agent：

```text
/paper_run --llm --limit 5
/paper_schedule
/paper_schedule 08:00 --llm --limit 5
/paper_schedule off
/paper_schedule on
/paper_schedule run
```

- `/paper_run`：立即在当前聊天返回一次论文雷达结果。
- `/paper_schedule`：查看平台级每日论文推送设置。
- `/paper_schedule 08:00`：把每日自动推送改到北京时间 08:00。
- `/paper_schedule run`：立即触发平台 scheduler，结果按通知路由推送到论文机器人或论文群。

## 迁移提醒

- `.env`、数据库、日志、PDF、上传文件、AstrBot 运行数据不会提交到 Git。
- 如果要把本地历史数据一起迁移到服务器，请用 `rsync` 或压缩包单独迁移 `astrbot-data/` 等运行目录。
- Paper Radar 的运行数据现在归独立仓库或 Docker volume 管理，源码更新也在 `paper_radar_agent` 仓库内完成。
- `docker-compose.yml` 当前仍包含部分 WSL/Windows 路径，迁移服务器时需要按服务器实际目录调整挂载路径。
