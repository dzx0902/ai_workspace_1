# MCP 配置模板

当前不建议直接给 AstrBot 开整个 Windows 盘的文件系统权限。更稳的做法是只暴露 AI Workspace 的受控目录。

## 推荐暴露目录

```text
/mnt/f/AIWorkspace/repos/allowed
/mnt/f/AIWorkspace/tasks
/mnt/f/ObsidianVault/AI
```

不要暴露：

```text
/mnt/c
/mnt/d
/mnt/f
```

## AstrBot 配置文件位置

当前 AstrBot 的 MCP 配置在 Docker volume 内：

```text
/AstrBot/data/mcp_server.json
```

可通过容器查看：

```bash
docker exec ai_astrbot cat /AstrBot/data/mcp_server.json
```

## 文件系统 MCP 示例

下面是一个示例结构，具体命令要根据你安装的 MCP server 实现调整。

```json
{
  "mcpServers": {
    "ai_workspace_files": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/mnt/f/AIWorkspace/repos/allowed",
        "/mnt/f/ObsidianVault/AI"
      ]
    }
  }
}
```

## 使用建议

- 先只读使用，确认工具调用路径和权限正确后再考虑写入。
- 项目修改优先使用 AI Workspace 的 `/dev patch` 和 `/dev apply` 流程。
- 写入能力只允许作用于 `/mnt/f/AIWorkspace/repos/allowed/<repo_name>`。
- 敏感工具只给管理员 ID 使用。

## 与当前开发接口的分工

MCP 适合：

- 浏览文件
- 查询资料
- 作为 Agent 工具补充

AI Workspace `/dev` 接口适合：

- 生成计划
- 生成补丁
- 查看 diff
- 经确认后应用补丁
- 运行白名单测试命令
