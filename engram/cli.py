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

    # 自动提炼 facts + 更新 context.md
    from .extractor_facts import auto_extract_from_new_sessions
    from .context_gen import update_context_files
    from .storage.db import get_sessions_since
    from datetime import datetime, timedelta

    since = (datetime.utcnow() - timedelta(days=1)).isoformat()
    new_sessions = get_sessions_since(since)
    if new_sessions:
        extracted = auto_extract_from_new_sessions(new_sessions)
        if extracted:
            console.print(f"🧠 自动提炼 {extracted} 条记忆")

    results = update_context_files()
    console.print(f"📄 context.md 已更新（{len(results)} 个文件）")
    
    # Backend sync
    from .config import get_backend
    backend = get_backend()
    if backend.name != "local":
        from .storage.db import DB_PATH
        if backend.upload(DB_PATH):
            console.print(f"☁️  Synced to {backend.name}")
        else:
            console.print(f"⚠️  Upload to {backend.name} failed")

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

@app.command("remember")
def remember(
    content: str = typer.Argument(help="要记住的内容"),
    scope: str = typer.Option("global", "--scope", "-s", help="作用域：global 或 project:名称"),
    priority: int = typer.Option(3, "--priority", "-p", help="优先级 1-5"),
    pin: bool = typer.Option(False, "--pin", help="固定（永远出现在 context.md）"),
    tags: str = typer.Option("", help="Comma-separated tags (legacy)"),
):
    """保存一条记忆到 memory.db。"""
    from engram.storage.memory_db import add_fact
    fid = add_fact(scope=scope, content=content, priority=priority, pinned=pin)
    scope_label = f"[cyan]{scope}[/cyan]"
    pin_label = " 📌 [已固定]" if pin else ""
    console.print(f"✅ 已记住（{scope_label}）{pin_label}: {content[:60]}...")
    console.print(f"   ID: {fid}")

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

@app.command("config-backend")
def config_backend(
    backend: str = typer.Argument(help="local|github|gitee|webdav|s3"),
    token: str = typer.Option(None, help="GitHub/Gitee PAT token"),
    repo: str = typer.Option(None, help="owner/repo"),
    url: str = typer.Option(None, help="WebDAV URL"),
    username: str = typer.Option(None, help="WebDAV username"),
    password: str = typer.Option(None, help="WebDAV password"),
    endpoint_url: str = typer.Option(None, help="S3 endpoint URL"),
    access_key: str = typer.Option(None, help="S3 access key"),
    secret_key: str = typer.Option(None, help="S3 secret key"),
    bucket: str = typer.Option(None, help="S3 bucket name"),
):
    """Configure sync backend (local/github/gitee/webdav/s3)."""
    from .config import save_config, get_backend as _get_backend
    config = {"backend": backend}
    if token: config["token"] = token
    if repo: config["repo"] = repo
    if url: config["url"] = url
    if username: config["username"] = username
    if password: config["password"] = password
    if endpoint_url: config["endpoint_url"] = endpoint_url
    if access_key: config["access_key"] = access_key
    if secret_key: config["secret_key"] = secret_key
    if bucket: config["bucket"] = bucket
    save_config(config)
    b = _get_backend()
    if b.test_connection():
        console.print(f"✅ Backend '{backend}' configured and reachable")
    else:
        console.print(f"⚠️  Backend '{backend}' configured but connection test failed")


@app.command()
def push():
    """Push local database to configured backend."""
    from .config import get_backend
    from .storage.db import DB_PATH
    backend = get_backend()
    if backend.name == "local":
        console.print("[yellow]No remote backend configured. Use: engram config-backend <backend>[/yellow]")
        return
    if backend.upload(DB_PATH):
        console.print(f"[green]✅ Pushed to {backend.name}[/green]")
    else:
        console.print(f"[red]❌ Push to {backend.name} failed[/red]")


@app.command()
def pull():
    """Pull database from configured backend."""
    from .config import get_backend
    from .storage.db import DB_PATH
    backend = get_backend()
    if backend.name == "local":
        console.print("[yellow]No remote backend configured. Use: engram config-backend <backend>[/yellow]")
        return
    if backend.download(DB_PATH):
        console.print(f"[green]✅ Pulled from {backend.name}[/green]")
    else:
        console.print(f"[red]❌ Pull from {backend.name} failed[/red]")


@app.command("facts")
def list_fact_cmd(
    scope: str = typer.Option(None, "--scope", "-s", help="过滤 scope"),
    pinned: bool = typer.Option(False, "--pinned", help="只显示固定记忆"),
):
    """列出 memory.db 中的记忆事实。"""
    from engram.storage.memory_db import list_facts, get_all_scopes
    from rich.table import Table

    facts = list_facts(scope=scope, pinned_only=pinned)
    if not facts:
        console.print("[dim]暂无记忆[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", width=12)
    table.add_column("Scope", width=20)
    table.add_column("内容", width=50)
    table.add_column("P", width=3)
    table.add_column("📌", width=3)

    for f in facts:
        table.add_row(
            f["id"],
            f["scope"],
            f["content"][:50],
            str(f["priority"]),
            "✓" if f["pinned"] else "",
        )
    console.print(table)
    console.print(f"\n共 {len(facts)} 条记忆")


@app.command("context")
def context_cmd(
    update: bool = typer.Option(False, "--update", help="重新生成 context.md 文件"),
    show: bool = typer.Option(False, "--show", help="显示当前 context.md 内容"),
):
    """管理 context.md 文件（用于文件注入）。"""
    from engram.context_gen import update_context_files, CONTEXT_FILE

    if update:
        results = update_context_files()
        console.print("✅ context.md 已更新：")
        for r in results:
            console.print(f"   {r}")
        console.print(f"\n📄 全局文件：{CONTEXT_FILE}")
    elif show:
        if CONTEXT_FILE.exists():
            console.print(CONTEXT_FILE.read_text())
        else:
            console.print("[dim]context.md 不存在，请先运行 engram context --update[/dim]")
    else:
        console.print("用法：engram context --update  或  engram context --show")


if __name__ == "__main__":
    app()
