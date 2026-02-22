"""Engram MCP Server — shares memory across AI coding tools."""
import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .storage.db import init_db, search_sessions, list_sessions, get_session, add_memory, search_memories
from .extractors import get_available_extractors

app = Server("engram")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_memory",
            description="Search across all AI coding tool conversations (Claude Code, Cursor, OpenCode, OpenClaw). Returns relevant sessions and memory snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "tool": {"type": "string", "description": "Filter by tool: claude_code, cursor, opencode, openclaw"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="list_sessions",
            description="List recent AI coding sessions. Optionally filter by tool or project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Filter by tool"},
                    "project": {"type": "string", "description": "Filter by project path"},
                    "limit": {"type": "integer", "default": 20}
                }
            }
        ),
        types.Tool(
            name="get_session",
            description="Get the full conversation history of a specific session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID from list_sessions or search_memory"}
                },
                "required": ["session_id"]
            }
        ),
        types.Tool(
            name="add_memory",
            description="Add a memory fact to Engram memory.db (synced to cloud). Use scope='global' for cross-project rules, scope='project:NAME' for project-specific facts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "scope": {"type": "string", "description": "Scope: 'global' or 'project:name'", "default": "global"},
                    "priority": {"type": "integer", "description": "1-5, default 3", "default": 3},
                    "pin": {"type": "boolean", "description": "Pin to core.md (always loaded)", "default": False},
                },
                "required": ["content"]
            }
        ),
        types.Tool(
            name="sync_sessions",
            description="Sync and import latest sessions from all available AI tools on this machine.",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="semantic_search",
            description="Semantic/vector search across all AI conversations. Better than keyword search for conceptual queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_context_summary",
            description="Get a summary of recent activity across all tools for a given project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project directory path"},
                    "limit": {"type": "integer", "default": 5, "description": "Number of recent sessions"}
                }
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "search_memory":
        sessions = search_sessions(
            arguments["query"],
            tool=arguments.get("tool"),
            limit=arguments.get("limit", 10)
        )
        # 同时搜索 memory.db facts（跨工具共享的精炼记忆）
        from .storage.memory_db import search_facts
        facts = search_facts(arguments["query"], limit=8)
        memories = search_memories(arguments["query"], limit=5)
        result = {
            "facts": [{"id": f["id"], "scope": f["scope"], "content": f["content"]} for f in facts],
            "sessions": sessions,
            "memories": memories,
            "total": len(facts) + len(sessions) + len(memories),
        }
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    
    elif name == "list_sessions":
        sessions = list_sessions(
            tool=arguments.get("tool"),
            project=arguments.get("project"),
            limit=arguments.get("limit", 20)
        )
        return [types.TextContent(type="text", text=json.dumps(sessions, ensure_ascii=False, indent=2))]
    
    elif name == "get_session":
        session = get_session(arguments["session_id"])
        if not session:
            return [types.TextContent(type="text", text='{"error": "Session not found"}')]
        return [types.TextContent(type="text", text=json.dumps(session, ensure_ascii=False, indent=2))]
    
    elif name == "add_memory":
        # 写到 memory_db.py 的 facts 表（可 engram facts 查看，可 push 同步）
        from .storage.memory_db import add_fact
        scope = arguments.get("scope", "global")
        fid = add_fact(
            scope=scope,
            content=arguments["content"],
            source="mcp",
            priority=arguments.get("priority", 3),
            pinned=bool(arguments.get("pin", False)),
        )
        return [types.TextContent(type="text", text=json.dumps({"id": fid, "scope": scope, "status": "saved"}))]
    
    elif name == "sync_sessions":
        from .storage.db import upsert_session
        extractors = get_available_extractors()
        counts = {}
        for extractor in extractors:
            count = 0
            for session in extractor.extract_sessions():
                upsert_session(session)
                count += 1
            counts[extractor.name] = count
        total = sum(counts.values())
        return [types.TextContent(type="text", text=json.dumps({"synced": counts, "total": total}))]
    
    elif name == "semantic_search":
        from .storage.db import semantic_search
        results = semantic_search(arguments.get("query", ""), arguments.get("limit", 10))
        return [types.TextContent(type="text", text=json.dumps(results[:5], ensure_ascii=False, indent=2))]

    elif name == "get_context_summary":
        sessions = list_sessions(project=arguments.get("project"), limit=arguments.get("limit", 5))
        summary_lines = []
        for s in sessions:
            summary_lines.append(f"[{s['source_tool']}] {s['title']} ({s.get('created_at','')})")
            if s.get("summary"):
                summary_lines.append(f"  → {s['summary'][:100]}")
        result = {"project": arguments.get("project"), "recent_sessions": sessions, "summary": "\n".join(summary_lines)}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    
    return [types.TextContent(type="text", text='{"error": "Unknown tool"}')]

def main():
    init_db()
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    asyncio.run(_run())

if __name__ == "__main__":
    main()
