![Version](https://img.shields.io/badge/version-0.2.1-blue)
[![PyPI](https://img.shields.io/pypi/v/engram-mcp)](https://pypi.org/project/engram-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

# 🧠 Engram

> Your AI tools share a brain.

**A bidirectional memory layer for AI coding tools.** What Claude Code learns, Cursor already knows. What you explain in OpenCode, OpenClaw remembers. Stop re-explaining your codebase every session.

<p align="center">
  <img src="docs/demo.svg" alt="Engram Demo" width="600">
</p>

## ✨ Features

- 🔄 **Bidirectional sync** across Claude Code, Cursor, OpenCode, and OpenClaw
- 🏠 **Local-first** — your memories stay on your machine (SQLite + FTS5 + vector)
- ☁️ **Cloud backup** via GitHub, Gitee, or WebDAV — sync across machines
- 🔍 **Semantic search** — vector embeddings + full-text search find anything instantly
- 🌐 **Chrome extension** — import from ChatGPT, Claude.ai, Gemini, DeepSeek, and more
- 🔌 **Native MCP server** — works with any MCP-compatible AI tool
- 📦 **Zero config** — one `pip install`, one command, done
- 🆓 **Free and open source** — MIT licensed, forever

## 🚀 Quick Start

```bash
# Install
pip install engram-mcp

# Import all your existing AI conversations
engram sync

# Connect to your tools (prints config JSON to paste)
engram config

# Optional: cloud sync
engram config-backend github --token ghp_xxx --repo you/engram-sync
engram push
```

**That's it.** Your AI tools now share a brain.

## 🔧 Tool Integration

<details>
<summary><b>Claude Code</b></summary>

Add to your MCP config (`.claude/mcp.json` or project settings):

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

Or reference in `CLAUDE.md`:
```
@engram search "your query" for cross-tool context
```
</details>

<details>
<summary><b>Cursor</b></summary>

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

Cursor's workspace storage is auto-detected by `engram sync`.
</details>

<details>
<summary><b>OpenCode</b></summary>

Add the same MCP config to OpenCode's settings. Session files are auto-detected by `engram sync`.
</details>

<details>
<summary><b>OpenClaw</b></summary>

Add MCP server config or use file injection. Agent logs are auto-detected by `engram sync`.
</details>

## 📖 How It Works

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude Code  │  │   Cursor    │  │  OpenCode   │  │  OpenClaw   │
└──────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                 │                │                │
       └────── remember ─┴──── search ────┴──── sync ─────┘
                                │
                    ┌───────────▼───────────┐
                    │    🧠 Engram Memory    │
                    │  SQLite + FTS5 + Vec  │
                    └───────────┬───────────┘
                                │  push / pull
                    ┌───────────▼───────────┐
                    │  GitHub / Gitee / DAV  │
                    └───────────────────────┘
```

1. **You work** with any supported AI tool as usual
2. **Engram syncs** conversations into a local semantic database
3. **Any tool** can search and recall memories from all other tools
4. **Cloud sync** (optional) keeps multiple machines in sync

## ⚡ CLI Commands

```bash
engram sync                    # Import from all detected tools
engram search "redis pooling"  # Semantic + keyword search
engram remember "Use BEM CSS"  # Save a persistent fact
engram ls                      # List recent sessions
engram facts                   # Show all saved facts
engram push / pull             # Cloud sync
engram status                  # Health check
```

## 🔌 MCP Tools

| Tool | Description |
|------|-------------|
| `search_memory` | Semantic + keyword search across everything |
| `add_memory` | Save facts, decisions, learnings |
| `list_sessions` | Browse sessions by tool or project |
| `get_session` | Full conversation replay |
| `sync_sessions` | Import latest from all tools |
| `get_context_summary` | Activity summary for a project |

## 🏆 How It's Different

| | **Engram** | Mem0 | Letta Code | ChatShuttle | Augment |
|---|---|---|---|---|---|
| **Cross-tool sync** | ✅ 4 tools + web AI | ❌ | ❌ Single agent | ❌ ChatGPT only | ❌ Proprietary |
| **Bidirectional** | ✅ | — | — | ❌ One-way | — |
| **Local-first** | ✅ SQLite | ❌ Cloud API | ✅ | ❌ Cloud | ❌ Cloud |
| **MCP native** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Setup time** | 15 seconds | API keys | Complex | Extension | Enterprise |
| **Price** | **Free forever** | Freemium | Free | Paid | Enterprise |

## 🗺️ Roadmap

- **Phase 1:** Community — reach 500 GitHub stars, stabilize MCP protocol
- **Phase 2:** Cloud Pro — hosted sync, team sharing ($3/mo individual, $12/mo team)
- **Phase 3:** MCP Marketplace — publish as a first-class MCP integration

## 🤝 Contributing

Contributions welcome! Here are some good first issues:

- 🐛 Add support for new AI tools (Windsurf, Aider, etc.)
- 📝 Improve documentation and examples
- 🧪 Add test coverage
- 🌍 i18n for CLI messages

See [CONTRIBUTING.md](CONTRIBUTING.md) or open an [issue](https://github.com/rorojiao/engram/issues).

## 🔗 Links

- 🌐 [Website](https://engram.gamezipper.com)
- 📦 [PyPI](https://pypi.org/project/engram-mcp/)
- 🐛 [Issues](https://github.com/rorojiao/engram/issues)
- 💬 [Discussions](https://github.com/rorojiao/engram/discussions)

## 📄 License

MIT — use it however you want.
