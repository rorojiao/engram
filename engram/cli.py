"""Engram CLI."""
import typer
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(name="engram", help="🧠 Engram — Shared memory for AI coding agents")
console = Console()

@app.command()
def sync(verbose: bool = typer.Option(False, "--verbose", "-v")):
    """Sync conversations from all available AI tools."""
    from .storage.db import init_db, upsert_session
    from .extractors import get_available_extractors
    
    init_db()
    extractors = get_available_extractors()
    
    if not extractors:
        console.print("[red]No supported AI tools found on this machine.[/red]")
        console.print("Supported: Claude Code (~/.claude), OpenClaw, OpenCode, Cursor")
        raise typer.Exit(1)
    
    console.print(f"[green]Found {len(extractors)} tool(s):[/green] {', '.join(e.name for e in extractors)}")
    
    total = 0
    for extractor in extractors:
        count = 0
        with console.status(f"Syncing {extractor.name}..."):
            for session in extractor.extract_sessions():
                upsert_session(session)
                count += 1
                if verbose:
                    console.print(f"  [dim]{session['title'][:60]}[/dim]")
        console.print(f"  ✅ {extractor.name}: {count} sessions")
        total += count
    
    console.print(f"\n[bold green]✨ Done! Imported {total} sessions total.[/bold green]")
    console.print("Run [bold]engram search <query>[/bold] to find anything.")

@app.command()
def search(query: str, tool: str = typer.Option(None, "--tool", "-t"), limit: int = 10):
    """Search across all AI tool conversations."""
    from .storage.db import search_sessions, search_memories
    
    sessions = search_sessions(query, tool=tool, limit=limit)
    memories = search_memories(query, limit=5)
    
    if not sessions and not memories:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        console.print("Run [bold]engram sync[/bold] to import your conversations first.")
        return
    
    if sessions:
        table = Table(title=f"🔍 Sessions matching '{query}'", show_header=True)
        table.add_column("Tool", style="cyan", width=12)
        table.add_column("Title", style="white")
        table.add_column("Project", style="dim")
        table.add_column("Date", style="dim", width=12)
        table.add_column("ID", style="dim", width=18)
        
        for s in sessions:
            table.add_row(
                s["source_tool"],
                (s.get("title") or "")[:50],
                (s.get("project") or "")[:25],
                (s.get("created_at") or "")[:10],
                s["id"][:16],
            )
        console.print(table)
    
    if memories:
        console.print("\n[bold]📌 Memory snippets:[/bold]")
        for m in memories:
            console.print(Panel(m["content"][:200], title=f"Memory #{m['id']}"))

@app.command()
def ls(tool: str = typer.Option(None, "--tool", "-t"), limit: int = 20):
    """List recent sessions."""
    from .storage.db import list_sessions
    
    sessions = list_sessions(tool=tool, limit=limit)
    if not sessions:
        console.print("[yellow]No sessions. Run [bold]engram sync[/bold] first.[/yellow]")
        return
    
    table = Table(title="📚 Recent Sessions")
    table.add_column("Tool", style="cyan", width=12)
    table.add_column("Title")
    table.add_column("Msgs", width=5)
    table.add_column("Date", width=12)
    table.add_column("ID", style="dim", width=20)
    
    for s in sessions:
        table.add_row(
            s["source_tool"],
            (s.get("title") or "")[:55],
            str(s.get("message_count", 0)),
            (s.get("created_at") or "")[:10],
            s["id"],
        )
    console.print(table)

@app.command()
def show(session_id: str):
    """Show full conversation of a session."""
    from .storage.db import get_session
    
    session = get_session(session_id)
    if not session:
        console.print(f"[red]Session '{session_id}' not found.[/red]")
        raise typer.Exit(1)
    
    console.print(Panel(
        f"[bold]{session.get('title')}[/bold]\n"
        f"Tool: {session['source_tool']} | Project: {session.get('project','')} | "
        f"Messages: {len(session.get('messages',[]))}",
        title=f"Session {session['id']}"
    ))
    
    for msg in session.get("messages", []):
        role_color = "green" if msg["role"] == "user" else "blue"
        console.print(f"\n[{role_color}][{msg['role'].upper()}][/{role_color}]")
        console.print(msg["content"][:500])

@app.command()
def remember(content: str, tags: str = typer.Option("", help="Comma-separated tags")):
    """Save a memory snippet to Engram."""
    from .storage.db import init_db, add_memory
    init_db()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    mid = add_memory(content, tags=tag_list)
    console.print(f"[green]✅ Memory saved (id={mid})[/green]")

@app.command()
def serve():
    """Start the MCP server (for use in mcp.json config)."""
    from .mcp_server import main
    main()

@app.command()  
def config():
    """Show MCP configuration snippet to add to your tools."""
    import sys
    python_path = sys.executable
    
    config_json = {
        "mcpServers": {
            "engram": {
                "command": python_path,
                "args": ["-m", "engram.mcp_server"]
            }
        }
    }
    
    console.print("\n[bold]📋 Add this to your MCP config (claude_desktop_config.json / .cursor/mcp.json):[/bold]\n")
    console.print(json.dumps(config_json, indent=2))
    console.print("\n[dim]Then run: engram sync[/dim]")

if __name__ == "__main__":
    app()
