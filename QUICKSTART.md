# Engram 快速上手

## 已集成的工具
- ✅ OpenClaw（Skill 方式）
- ✅ Claude Code（MCP via ~/.claude.json）
- ✅ Cursor（MCP via ~/.cursor/mcp.json）
- ✅ OpenCode（MCP via ~/.config/opencode/opencode.json）

## 每日使用
```bash
# 同步所有工具的最新对话
engram sync

# 搜索历史
engram search "redis架构"

# 语义搜索
engram search "redis架构" --semantic
```

## MCP 使用（在 Claude Code / Cursor / OpenCode 中）
在对话中直接说：
- "用 engram 搜索我之前关于 xxx 的对话"
- "search_memory: redis 架构"

## Gitee 云同步（配置后可用）
```bash
engram push   # 上传到 Gitee
engram pull   # 从 Gitee 下载
```
