# 🧠 Engram

> Your AI tools share a brain.

[![PyPI](https://img.shields.io/pypi/v/engram-mcp)](https://pypi.org/project/engram-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Stop re-explaining your codebase every session.** Engram gives Claude Code, Cursor, OpenCode, and OpenClaw a shared memory — so what one tool learns, all tools know.

<p align="center">
  <img src="docs/demo.svg" alt="Engram Demo" width="600">
</p>

## Why Engram?

Every time you switch between AI coding tools, you lose context:

- 😤 Claude Code learned your naming conventions → **Cursor doesn't know**
- 😤 OpenCode figured out your project structure → **Claude Code forgot**
- 😤 You spend 5 minutes re-explaining things that were **already explained**

Engram fixes this. **One install. 15 seconds to set up. Works forever.**

## How It Works

```
You explain once  →  Engram remembers  →  All your AI tools know
```

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Claude Code  │  │   Cursor    │  │  OpenCode   │  │  OpenClaw   │
└──────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                 │                │                │
       └─────────────────┴────────────────┴────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    🧠 Engram Memory    │
                    │  SQLite + FTS5 + Vec  │
                    └───────────────────────┘
```

- 🔄 **Bidirectional sync** — Claude Code ↔ Cursor ↔ OpenCode ↔ OpenClaw
- 🔒 **Local-first** — all data stays on your machine
- ☁️ **Optional cloud sync** — via private GitHub / Gitee / WebDAV repo
- ⚡ **15-second setup** — one command per tool
- 🔍 **Semantic search** — vector embeddings + full-text search find anything

## Quick Start

### 1. Install

```bash
pip install engram-mcp
```

### 2. Import your conversations

```bash
engram sync     # auto-detects Claude Code, Cursor, OpenCode, OpenClaw
```

### 3. Connect to your AI tools (MCP)

```bash
engram config   # prints the JSON snippet — paste it into your tool's config
```

That's it. Your AI tools now share a brain.

## What Can You Do?

```bash
# Save a fact your AI should always know
engram remember "We use BEM naming for CSS classes" --scope project:myapp

# Search across ALL your AI conversations
engram search "redis connection pooling"

# List recent sessions from every tool
engram ls

# See everything Engram knows
engram facts

# Cloud sync (optional)
engram config-backend github --token ghp_xxx --repo you/engram-sync
engram push
```

## Supported Tools

### Coding Agents (via CLI extractors)

| Tool | Auto-detect | Format |
|------|:-----------:|--------|
| **Claude Code** | ✅ | JSONL conversations |
| **Cursor** | ✅ | SQLite workspace storage |
| **OpenCode** | ✅ | JSON session files |
| **OpenClaw** | ✅ | JSONL agent logs |
| **Codex CLI** | ✅ | — |

### Web AI (via Chrome Extension)

| Platform | Import | Live Snapshot |
|----------|:------:|:------------:|
| ChatGPT | ✅ | ✅ |
| Claude.ai | ✅ | ✅ |
| Gemini | — | ✅ |
| DeepSeek | ✅ | ✅ |
| Perplexity | — | ✅ |
| Grok | — | ✅ |
| 豆包 / 千问 / 通义 | ✅ | ✅ |

## MCP Server

Engram exposes these tools to any MCP-compatible AI:

| Tool | What it does |
|------|-------------|
| `search_memory` | Semantic + keyword search across everything |
| `add_memory` | Save facts, decisions, learnings |
| `list_sessions` | Browse sessions by tool or project |
| `get_session` | Full conversation replay |
| `sync_sessions` | Import latest from all tools |
| `get_context_summary` | Activity summary for a project |

### Config for Claude Code / Cursor / OpenClaw

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

## How It's Different

| | **Engram** | Mem0 | Letta (MemGPT) | ChatShuttle |
|---|---|---|---|---|
| **Focus** | AI coding tools | General AI memory | Stateful agents | Chat backup |
| **Works with** | Claude Code, Cursor, OpenCode, OpenClaw + web AI | Custom apps | Custom agents | ChatGPT only |
| **Setup** | `pip install` + one command | API keys + hosted | Complex setup | Chrome extension |
| **Data location** | 100% local (SQLite) | Cloud API | Local or cloud | Cloud |
| **Search** | Vector + FTS5 hybrid | Vector only | Vector only | Basic |
| **MCP support** | ✅ Native | ❌ | ❌ | ❌ |
| **Price** | Free & open source | Freemium | Free (complex) | Paid |

## Cloud Sync (Optional)

Keep your memory in sync across machines:

```bash
# GitHub
engram config-backend github --token ghp_xxx --repo you/engram-sync

# Gitee (for users in China)
engram config-backend gitee --token xxx --repo you/engram-sync

# WebDAV
engram config-backend webdav --url https://dav.example.com --username user --password pass

# Push / Pull
engram push
engram pull
```

## FAQ

**Q: Does my code get sent anywhere?**
No. Engram reads local conversation logs and stores everything in a local SQLite database. Cloud sync only uploads the memory database — never your source code.

**Q: Can I use it with just one tool?**
Yes. Even with a single tool, Engram gives you persistent memory across sessions and semantic search over your conversation history.

**Q: How is this different from CLAUDE.md / .cursorrules?**
Those are static files you maintain manually. Engram is dynamic — it learns from your conversations and makes knowledge searchable across tools automatically.

## Links

- 🌐 [Website](https://engram.gamezipper.com)
- 📦 [PyPI](https://pypi.org/project/engram-mcp/)
- 🐛 [Issues](https://github.com/rorojiao/engram/issues)

## License

MIT — use it however you want.
