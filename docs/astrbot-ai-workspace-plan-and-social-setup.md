# AstrBot AI Workspace 使用与改造计划

## 当前状态

当前系统已经具备：

- AstrBot WebUI 可访问：`http://localhost:6185`
- 默认模型：`deepseek-chat`
- `ai_workspace` 插件已能被 AstrBot 加载
- AstrBot 数据已迁移到 Docker volume：`ai_workspace_astrbot_data`
- AI Workspace 后端通过 FastAPI 提供 `/file`、`/ask`、`/web`、`/video`、`/dev/*` 等接口

当前还需要补齐：

- 拖文件到聊天框后自动分析
- Bot 经确认后真正修改本地项目文件
- MCP / Agent 安全配置模板
- 社交平台接入
- 管理员 ID、人格、知识库策略整理

## 改造计划

### 阶段 1：补齐文件分析体验

目标：让你可以“丢文件 -> Bot 自动分析”。

要做：

- 给 `ai_workspace` 插件增加附件识别能力
- 识别 PDF、TXT、Markdown、HTML、SRT、VTT 等文件
- 自动保存到 `/mnt/f/AIWorkspace/uploads`
- 自动调用 FastAPI `/file`
- 返回 Obsidian 笔记路径和后续提问建议

建议新增命令：

```text
/analyze_file
/analyze_latest
/analyze_pdf <category> <filename>
```

拖拽文件支持需要确认 AstrBot WebChat 的附件事件结构。插件应监听消息事件，提取附件 URL 或本地路径，然后转交给 AI Workspace 后端。

### 阶段 2：安全修改 Windows 本地项目

目标：Bot 可以分析、生成补丁、经你确认后应用补丁。

当前已有命令：

```text
/repos
/dev plan <repo_name> <task_description>
/dev review <repo_name>
/dev patch <repo_name> <task_description>
```

建议新增：

```text
/dev apply <task_id>
/dev diff <repo_name>
/dev test <repo_name> <command>
```

安全边界：

- 项目分析可读取 `/mnt/f` 下使用相对路径指定的任意目录
- 只允许修改 `/mnt/f/AIWorkspace/repos/allowed/<repo_name>`
- 禁止 `rm -rf`、`sudo`、`git push`、跨目录写入
- 每次 apply 前必须返回 diff，让用户确认
- 测试命令只允许白名单命令，例如 `pytest`、`npm test`、`pnpm test`

Windows 项目接入示例：

```bash
mkdir -p /mnt/f/AIWorkspace/repos/allowed
ln -s /mnt/f/Projects/demo /mnt/f/AIWorkspace/repos/allowed/demo
```

然后在 AstrBot 中使用：

```text
/repos
/dev review demo
/dev patch demo 修复启动报错
```

整盘只读分析也可以直接使用相对于 F 盘的路径。路径含空格时需要加引号：

```text
/dev review "2026Spring/King-of-Pigeon" 总结项目结构、技术栈和主要风险
/dev review "2026Spring/Database Technology/bigwork" 分析核心模块和运行方式
```

`/dev test` 和 `/dev apply` 仍只接受
`F:\AIWorkspace\repos\allowed` 下的仓库。

### 阶段 3：MCP / Agent 配置

目标：让 AstrBot 能调用工具，但不越权。

建议优先配置：

- filesystem MCP：只暴露 `/mnt/f/AIWorkspace/repos/allowed`
- git MCP：只允许本地仓库状态、diff、log
- sqlite MCP：只读查询本地知识库或任务数据库
- browser/search MCP：需要联网搜索时再启用

不要一开始暴露整个 Windows 盘，例如：

```text
/mnt/c
/mnt/d
/mnt/f
```

建议只暴露：

```text
/mnt/f/AIWorkspace
/mnt/f/AIWorkspace/repos/allowed
/mnt/f/ObsidianVault/AI
```

建议 Agent 角色：

- 研究助理：PDF、网页、视频总结
- 代码审查员：review、bug、测试缺口
- 开发代理：生成补丁、跑测试、解释代码
- 知识库管理员：整理笔记、分类、生成复习问题

### 阶段 4：知识库、人设、插件整理

知识库分两套：

```text
AI Workspace Chroma：/file /web /video /ask 这一套
AstrBot 内置知识库：WebUI 里的普通知识库
```

推荐策略：

- 论文、网页、视频课程：使用 AI Workspace
- 聊天常识、固定 FAQ、角色资料：使用 AstrBot 内置知识库

建议人格：

- 科研分析师
- 代码审查员
- 学习教练
- 项目工程师

默认人格可先设为“项目工程师”或“科研分析师”。

## 日常使用命令

分析 PDF：

```text
/file pdf paper xxx.pdf
/ask pdf paper 总结这篇 PDF
/ask pdf paper 提取关键概念和复习题
```

分析网页：

```text
/web research https://example.com/article
/ask web research 这篇文章讲了什么
```

分析视频：

```text
/video course https://www.youtube.com/watch?v=xxx
/transcribe course https://www.youtube.com/watch?v=xxx
```

项目开发：

```text
/repos
/dev plan demo 分析项目结构
/dev review demo
/dev patch demo 修复某个问题
```

## 社交软件配置教程

### 共同前置步骤

打开 AstrBot：

```text
http://localhost:6185
```

确认模型：

```text
配置 -> 服务提供商 / 模型
```

确保：

```text
deepseek-chat 可用
default_provider_id = deepseek-chat
```

设置管理员 ID：

1. 在聊天里发送：

```text
/sid
```

2. 拿到会话 ID 后，到：

```text
配置 -> 其他配置 -> 管理员 ID 列表
```

3. 加入你的 ID。

管理员 ID 很重要。敏感功能、电脑控制、开发工具调用通常都应限制为管理员可用。

### WebChat

这是最简单的本机测试方式。

入口：

```text
AstrBot WebUI -> 聊天 / WebChat
```

可直接发送：

```text
/ask 你好
/file pdf paper test.pdf
/repos
```

适合调试插件、命令、模型和知识库。

### QQ 个人号：NapCat + aiocqhttp

流程：

1. 启动 NapCat
2. 登录 QQ
3. 在 AstrBot 创建 `aiocqhttp` 平台
4. 配置 WebSocket 地址
5. 看控制台是否显示 `aiocqhttp(OneBot v11) 适配器已连接`

AstrBot 中：

```text
机器人 -> 创建机器人 -> aiocqhttp
```

如果 NapCat 和 AstrBot 在同一个 Docker 网络，地址通常类似：

```text
ws://napcat:3001
```

如果 NapCat 在 Windows 本机，AstrBot 在 Docker 里，可能使用：

```text
ws://host.docker.internal:<端口>/ws
```

成功标志：

```text
控制台出现 aiocqhttp(OneBot v11) 适配器已连接
```

然后在 QQ 中发送：

```text
/sid
```

把你的 ID 加入 AstrBot 管理员列表。

### Telegram

流程：

1. 找 BotFather 创建机器人
2. 拿到 Bot Token
3. AstrBot 中创建 `telegram` 机器人
4. 填 Token
5. 如果要群聊，BotFather 中关闭 Privacy Mode

关闭群聊隐私模式：

```text
/setprivacy -> Disable
```

然后把 Bot 拉进群。

### 飞书

适合企业协作。

流程：

1. 在飞书开放平台创建企业自建应用
2. 获取 `app_id` 和 `app_secret`
3. AstrBot 中创建 `lark` 机器人
4. 填写 `app_id`、`app_secret`
5. 配置事件订阅和回调
6. 给应用开消息权限
7. 发布版本
8. 把机器人加入群

如果 AstrBot 只在本机，没有公网地址，飞书回调进不来。需要：

```text
公网服务器 / 内网穿透 / Cloudflare Tunnel / frp
```

### 企业微信

适合企业微信内部群。

流程：

1. 企业微信后台创建应用或智能机器人
2. AstrBot 中创建 `wecom` 或 `wecom_ai_bot`
3. 填 `CorpID`、`AgentID`、`Secret`、`Token`、`EncodingAESKey`
4. 配置回调 URL
5. 开启接收消息权限

同样需要公网可访问地址，除非只在局域网内使用。

## 推荐实施顺序

```text
1. 先用 WebChat 跑通 /file /ask /dev
2. 配置管理员 ID
3. 接入 QQ / NapCat 或飞书
4. 补“拖文件自动分析”
5. 补“确认后应用代码补丁”
6. 再配置 MCP / Agent
```

不要一上来就开所有社交平台。先选一个最常用的平台，打通收发消息、管理员 ID、插件命令，再逐步扩展。
