# Agent 与 AstrBot 解耦方案

## 目标

把 AstrBot 从“承载具体能力的应用”收敛成“聊天入口和 agent 管理层”，把具体能力拆成独立 agent 服务。这样后续新增 Paper Radar、Dev Agent、RAG、文件处理、代码审查等能力时，只需要按统一协议注册到 AstrBot 侧，不需要把所有功能继续写进同一个 AstrBot 插件仓库。

## 当前落地状态

- AstrBot 插件已拆出 `client.py`、`config.py`、`utils.py`、`plugin.py` 和 `commands/`，插件入口变成薄组合层。
- 主仓库源码已统一移动到 `src/`，根目录只保留部署入口、配置、文档和环境模板。
- Paper Radar 已拆成独立 Git 仓库：`/home/dzx0902/paper_radar_agent`。
- Paper Radar agent 已提供 `/manifest`，可以被后续 gateway 或 registry 发现。
- 主仓库已移除 Paper Radar 源码，`docker-compose.yml` 通过 `PAPER_RADAR_AGENT_PATH` 引用独立仓库。
- `src/services/rag_api` 已移除重复的 `/papers/*` 路由，Paper Radar 请求只走独立 agent API。

## 当前问题

当前仓库同时包含：

- AstrBot 插件适配层：命令解析、消息发送、订阅状态、定时推送。
- Agent 能力实现：Dev Agent、RAG、文件处理、网页/视频处理、Paper Radar。
- 运行数据：数据库、日志、PDF、笔记、AstrBot data。
- 部署编排：同一个 `docker-compose.yml` 同时管理所有服务。

这会导致几个问题：

- AstrBot 插件知道太多后端细节，新增 agent 时要改插件代码。
- Paper Radar 这类业务 agent 的 API、定时任务和聊天交互混在一起。
- 代码仓库边界不清晰，后续如果只优化 agent 管理层，也会带着业务 agent 代码一起变动。
- 服务器迁移时，运行数据、配置、服务路径容易和源码纠缠。

## 推荐架构

采用三层结构：

```text
chat-adapter-astrbot
  只负责聊天平台接入、权限、命令路由、订阅管理、消息格式化

agent-gateway
  负责 agent 注册表、能力发现、统一调用协议、任务状态、审计、鉴权

agent-services
  paper-radar-agent
  dev-agent
  rag-agent
  ingest-agent
  future-agent-*
```

### 1. AstrBot 侧：聊天入口和管理层

建议仓库名：`astrbot-agent-hub`

职责：

- 提供少量稳定命令，例如 `/agents`、`/agent`、`/subscribe`、`/tasks`。
- 从 agent registry 读取可用 agent 和 capability。
- 把用户消息转换成统一 agent 请求。
- 保存聊天会话级配置：订阅、默认 agent、权限策略、消息偏好。
- 处理长文本分段、按钮/菜单、错误提示、用户身份映射。

不负责：

- 不直接实现 Paper Radar 逻辑。
- 不直接读写 RAG 数据库。
- 不直接执行代码任务。
- 不直接依赖具体 agent 的 Python 包。

### 2. Agent Gateway：统一协议层

可以先和 AstrBot 插件放同一仓库，后续再独立成服务。它是 AstrBot 和具体 agent 之间的稳定边界。

职责：

- 维护 agent 注册表。
- 暴露统一 HTTP API。
- 为每个 agent 转发请求。
- 统一处理超时、重试、鉴权、日志、任务 ID。
- 支持同步请求和异步任务。

建议接口：

```http
GET /agents
GET /agents/{agent_id}
POST /agents/{agent_id}/invoke
POST /agents/{agent_id}/tasks
GET /tasks/{task_id}
POST /subscriptions
GET /subscriptions
DELETE /subscriptions/{subscription_id}
```

统一请求格式：

```json
{
  "capability": "daily_report",
  "input": {
    "date": "2026-07-02",
    "limit": 20
  },
  "context": {
    "user_id": "astrbot-user",
    "conversation_id": "umo",
    "locale": "zh-CN",
    "timezone": "Asia/Shanghai"
  }
}
```

统一响应格式：

```json
{
  "ok": true,
  "type": "message",
  "message": "可直接发给聊天窗口的文本",
  "data": {},
  "artifacts": []
}
```

异步任务响应：

```json
{
  "ok": true,
  "type": "task",
  "task_id": "paper-radar-20260702-083000",
  "status": "queued"
}
```

### 3. Agent 服务侧：独立能力服务

每个 agent 是一个独立仓库或至少独立包，提供自己的 Dockerfile、配置、测试和 API。

建议仓库：

- `paper-radar-agent`
- `dev-agent`
- `knowledge-agent` 或 `rag-agent`
- `ingest-agent`
- `astrbot-agent-hub`
- 可选：`agent-protocol`，存放 Pydantic schema、OpenAPI、共享客户端。

每个 agent 需要提供：

```http
GET /health
GET /manifest
POST /invoke
POST /tasks
GET /tasks/{task_id}
```

`/manifest` 示例：

```json
{
  "id": "paper-radar",
  "name": "Paper Radar",
  "version": "0.1.0",
  "capabilities": [
    {
      "name": "daily_report",
      "description": "生成指定日期论文日报",
      "mode": "sync",
      "input_schema": {
        "date": "string",
        "limit": "integer",
        "use_llm": "boolean"
      }
    },
    {
      "name": "subscribe_daily",
      "description": "创建每日论文推送订阅",
      "mode": "subscription"
    }
  ]
}
```

## 仓库拆分建议

### 第一阶段：不拆远程仓库，先拆目录边界

在当前仓库内整理成：

```text
apps/
  astrbot-agent-hub/
  agent-gateway/
agents/
  paper-radar/
  dev-agent/
  rag-agent/
packages/
  agent-protocol/
deploy/
  docker-compose.local.yml
  docker-compose.server.yml
docs/
```

优点是改动可控，现有功能容易保住。

### 第二阶段：拆成多个 GitHub 仓库

推荐最终拆法：

```text
astrbot-agent-hub
agent-protocol
paper-radar-agent
dev-agent
rag-agent
ai-workspace-deploy
```

其中 `ai-workspace-deploy` 只放 compose、服务器部署文档、反向代理配置、systemd 文件和 `.env.example`，不放业务源码。

## 当前功能映射

| 当前位置 | 目标归属 | 说明 |
|---|---|---|
| `src/astrbot_plugins/ai_workspace` | `astrbot-agent-hub` | 改成薄适配层，只调用 gateway |
| `paper_radar/` | `paper-radar-agent` | 已拆到 `/home/dzx0902/paper_radar_agent` |
| `src/dev_agents/` | `dev-agent` | 代码任务、repo 权限、patch/test 等能力独立 |
| `src/scripts/query_kb.py`、`src/services/rag_api` 的 `/ask` | `rag-agent` | 知识库查询独立 |
| `src/scripts/process_file.py`、`web_to_note.py`、`video_to_note.py` | `ingest-agent` | 文件/网页/视频摄取独立 |
| `docker-compose.yml` | `ai-workspace-deploy` | 只负责组合服务 |

## 命令设计

建议 AstrBot 只保留通用命令，具体 agent 通过 manifest 暴露能力：

```text
/agents
/agent paper-radar daily_report --date 2026-07-02 --limit 20
/agent dev plan repo-name "优化登录流程"
/agent rag ask "某个问题"
/subscribe paper-radar daily_report --time 08:30 --top 20
/unsubscribe <subscription_id>
/tasks
/task <task_id>
```

为了兼容现有习惯，可以保留 alias：

```text
/papers -> /agent paper-radar daily_report
/paper_run -> /agent paper-radar run_daily
/dev plan -> /agent dev plan
/ask -> /agent rag ask
```

alias 配置应该放在 AstrBot 侧配置文件，不写死在 Python 代码里。

## 定时任务归属

建议把“什么时候触发”放在管理层，把“触发后做什么”放在 agent。

也就是：

- AstrBot/agent-gateway 保存订阅：哪个会话、几点、调用哪个 agent capability、参数是什么。
- 到时间后 gateway 调用 `paper-radar-agent` 的 `daily_report` 或 `run_daily`。
- Paper Radar 不需要知道 AstrBot 的 `unified_msg_origin`。

这样未来任何 agent 都能订阅：

```text
每天 08:30 推论文日报
每周一 09:00 生成 repo review
每天晚上同步知识库
```

## 配置设计

AstrBot 侧只需要：

```env
AGENT_GATEWAY_BASE_URL=http://agent-gateway:8080
AGENT_GATEWAY_TOKEN=...
ASTRBOT_TIMEZONE=Asia/Shanghai
```

Gateway 侧维护 agent registry：

```yaml
agents:
  paper-radar:
    base_url: http://paper-radar-agent:8010
    token_env: PAPER_RADAR_AGENT_TOKEN
  dev:
    base_url: http://dev-agent:8020
    token_env: DEV_AGENT_TOKEN
  rag:
    base_url: http://rag-agent:8030
    token_env: RAG_AGENT_TOKEN
```

具体 agent 自己维护自己的 `.env.example`，例如 API key、数据库目录、模型目录。

## Docker Compose 设计

最终部署形态：

```yaml
services:
  astrbot:
    image: astrbot-agent-hub
    environment:
      - AGENT_GATEWAY_BASE_URL=http://agent-gateway:8080

  agent-gateway:
    image: agent-gateway
    volumes:
      - ./config/agents.yaml:/app/config/agents.yaml:ro
      - gateway_data:/app/data

  paper-radar-agent:
    image: paper-radar-agent
    volumes:
      - paper_radar_data:/app/data
      - paper_radar_notes:/app/notes

  dev-agent:
    image: dev-agent
    volumes:
      - repos:/workspace/repos
      - dev_tasks:/workspace/tasks

  rag-agent:
    image: rag-agent
    depends_on:
      - chroma

  chroma:
    image: chromadb/chroma
```

## 迁移路线

### Step 1：收窄 AstrBot 插件

- 新增 `AgentClient`，统一封装 HTTP 请求。
- 把当前 `post_json`、`paper_post_json`、`paper_get_json` 统一到 client。
- 把命令处理拆成 `commands/paper.py`、`commands/dev.py`、`commands/rag.py`。
- 行为不变，只改变内部结构。

### Step 2：把 Paper Radar 从总 API 中移除

- AstrBot 不再调用 `src/services/rag_api` 的 `/papers/*`。
- AstrBot 或 gateway 直接调用 `paper_radar/paper_radar/api.py` 服务。
- 删除 `src/services/rag_api/app.py` 中 Paper Radar 的导入和路由。

这是最优先的一刀，因为 Paper Radar 已经基本具备独立服务形态。

### Step 3：引入 agent manifest

- 每个 agent 提供 `/manifest`。
- AstrBot/gateway 启动时拉取 manifest。
- `/agents` 命令从 manifest 生成列表。

### Step 4：引入 gateway

- AstrBot 只连 gateway。
- gateway 根据 registry 转发到各 agent。
- 订阅任务迁移到 gateway。

### Step 5：拆仓库

- 先拆 `paper-radar-agent`。
- 再拆 `astrbot-agent-hub`。
- 最后拆 `dev-agent`、`rag-agent`、`ingest-agent`。

## 优先级建议

第一优先级：

- Paper Radar 独立仓库和独立 Docker 服务。
- AstrBot 插件改为只调用 Paper Radar API，不再包含 Paper Radar 业务逻辑。

第二优先级：

- 抽 `AgentClient` 和 manifest。
- 用 registry 代替写死的 API endpoint。

第三优先级：

- 引入 gateway，把订阅和任务状态统一管理。
- 拆 Dev Agent、RAG Agent、Ingest Agent。

## 判断是否解耦成功

满足这些条件就算拆干净：

- 新增一个 agent 时，不需要改 AstrBot 插件代码，只改 registry 或安装 agent。
- 升级 Paper Radar 时，不需要重建 AstrBot 镜像。
- AstrBot 仓库里没有 Paper Radar、RAG、Dev Agent 的业务实现。
- agent 可以脱离 AstrBot 单独用 curl 或 Web UI 调用。
- 定时订阅数据里保存的是 `agent_id + capability + input`，而不是某个具体 Python 函数名。
