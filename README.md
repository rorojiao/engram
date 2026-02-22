# 🧠 Engram

**Shared memory layer for AI coding agents**

[![PyPI](https://img.shields.io/pypi/v/engram-mcp)](https://pypi.org/project/engram-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> Stop losing context when switching between Claude Code, Cursor, OpenCode, and OpenClaw. Engram gives all your AI tools a shared memory.

🌐 **Website:** [engram.gamezipper.com](https://engram.gamezipper.com)

## Quick Start

```bash
pip install engram-mcp
engram sync                        # imports all your AI conversations
engram search "redis connection"   # find anything across all tools
engram config                      # get MCP config snippet
```

## Supported Platforms

### Web AI (Chrome Extension)
| Platform | URL | Import | Live Snapshot |
|----------|-----|--------|--------------|
| ChatGPT | chat.openai.com | ✅ Official ZIP | ✅ |
| Claude | claude.ai | ✅ Official JSON | ✅ |
| Gemini | gemini.google.com | - | ✅ |
| Perplexity | perplexity.ai | - | ✅ |
| Grok | grok.x.com | - | ✅ |
| DeepSeek | chat.deepseek.com | ✅ JSON | ✅ |
| 豆包 Doubao | doubao.com/chat | ✅ Markdown | ✅ |
| 千问 Qwen | chat.qwen.ai | - | ✅ |
| 通义 Tongyi | tongyi.aliyun.com | - | ✅ |

### Coding Tools (Python CLI)
| Tool | Path | Format |
|------|------|--------|
| Claude Code | ~/.claude/projects | JSONL |
| OpenClaw | ~/.openclaw/agents | JSONL |
| OpenCode | ~/.local/share/opencode/storage/ | JSON files (ses_*.json, msg_*.json, prt_*.json) |
| Cursor | ~/.config/Cursor/User/workspaceStorage/*/state.vscdb | SQLite (ItemTable) |
| Codex CLI | ~/.codex | - |

## Features

### 🔍 Vector Semantic Search
Engram uses [fastembed](https://github.com/qdrant/fastembed) (BAAI/bge-small-en-v1.5, 384-dim) + [sqlite-vec](https://github.com/asg017/sqlite-vec) for semantic search alongside FTS5 keyword search. Results are merged and deduplicated.

```bash
pip install engram-mcp[vector]  # installs sqlite-vec + fastembed
engram sync                      # embeddings generated automatically
engram search "how to fix auth"  # uses both vector + FTS5
```

### ☁️ Multi-Backend Storage
Sync your Engram database to remote backends:

```bash
# GitHub
engram config-backend github --token ghp_xxx --repo owner/repo

# Gitee
engram config-backend gitee --token xxx --repo owner/repo

# WebDAV
engram config-backend webdav --url https://dav.example.com --username user --password pass

# Manual push/pull
engram push
engram pull
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_memory` | Search across all conversations and memory snippets |
| `list_sessions` | List recent sessions, filter by tool or project |
| `get_session` | Get full conversation history of a session |
| `add_memory` | Save a memory snippet (context, decisions, learnings) |
| `sync_sessions` | Import latest sessions from all available tools |
| `get_context_summary` | Summary of recent activity for a project |

## Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude Code  │  │   Cursor    │  │  OpenCode   │  │  OpenClaw   │
└──────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                 │                │                │
       └────────┬────────┴────────┬───────┘                │
                │    Extractors   │                        │
                └────────┬────────┘────────────────────────┘
                         │
                ┌────────▼────────┐
                │  SQLite + FTS5  │  ~/.engram/engram.db
                └────────┬────────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
        ┌─────▼───┐ ┌───▼────┐ ┌──▼───┐
        │   CLI   │ │  MCP   │ │ Web  │
        │ engram  │ │ Server │ │  UI  │
        └─────────┘ └────────┘ └──────┘
```

## MCP Configuration

### Claude Code / Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "engram": {
      "command": "python3",
      "args": ["-m", "engram.mcp_server"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "engram": {
      "command": "python3",
      "args": ["-m", "engram.mcp_server"]
    }
  }
}
```

### OpenClaw

Add to your OpenClaw MCP config:

```json
{
  "mcpServers": {
    "engram": {
      "command": "python3",
      "args": ["-m", "engram.mcp_server"]
    }
  }
}
```

## CLI Commands

```bash
engram sync              # Import conversations from all tools
engram search "query"    # Full-text search across everything
engram ls                # List recent sessions
engram show <id>         # Show full conversation
engram remember "text"   # Save a memory snippet
engram serve             # Start MCP server
engram config            # Show MCP config snippet
```

## How It Works

1. **Extractors** read conversation data from each tool's local storage
2. **Storage** normalizes everything into SQLite with FTS5 full-text search
3. **MCP Server** exposes search/retrieval tools to any MCP-compatible AI
4. **CLI** provides direct access for humans

All data stays local. Nothing leaves your machine.

## License

MIT
