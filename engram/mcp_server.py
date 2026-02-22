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
            description="Add a memory snippet to Engram. Useful for saving important context, decisions, or learnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"}
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
        memories = search_memories(arguments["query"], limit=5)
        result = {"sessions": sessions, "memories": memories, "total": len(sessions) + len(memories)}
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
        mid = add_memory(
            arguments["content"],
            tags=arguments.get("tags", [])
        )
        return [types.TextContent(type="text", text=json.dumps({"id": mid, "status": "saved"}))]
    
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
    asyncio.run(stdio_server(app))

if __name__ == "__main__":
    main()
