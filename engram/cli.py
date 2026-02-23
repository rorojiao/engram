"""Engram CLI."""
import typer
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

def _version_callback(value: bool):
    if value:
        from engram import __version__
        print(f"engram {__version__}")
        raise typer.Exit()

app = typer.Typer(name="engram", help="🧠 Engram — Shared memory for AI coding agents",
                  callback=lambda version: None)
console = Console()

@app.callback()
def main(version: bool = typer.Option(False, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version")):
    pass

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
        try:
            with console.status(f"Syncing {extractor.name}..."):
                for session in extractor.extract_sessions():
                    upsert_session(session)
                    count += 1
                    if verbose:
                        console.print(f"  [dim]{session['title'][:60]}[/dim]")
            console.print(f"  ✅ {extractor.name}: {count} sessions")
        except Exception as e:
            console.print(f"  [red]⚠️ {extractor.name} 出错（已跳过）: {e}[/red]")
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

    # 注意：sync 不上传任何文件（engram.db 可能几十MB）
    # 用 `engram push` 显式推送 memory.db + core.md + context.md

@app.command()
def search(query: str, tool: str = typer.Option(None, "--tool", "-t"), limit: int = 10):
    """Search across all AI tool conversations AND memory facts."""
    from .storage.db import search_sessions, search_memories
    from .storage.memory_db import search_facts

    sessions = search_sessions(query, tool=tool, limit=limit)
    memories = search_memories(query, limit=5)
    facts = search_facts(query, limit=8)

    if not sessions and not memories and not facts:
        console.print(f"[yellow]No results for '{query}'[/yellow]")
        console.print("Tip: Run [bold]engram pull[/bold] to sync shared memory from cloud, or [bold]engram sync[/bold] to import local sessions.")
        return

    # 优先展示 facts（来自 memory.db，跨工具共享的精华）
    if facts:
        from rich.table import Table
        table = Table(title=f"📌 Memory facts matching '{query}'", show_header=True, header_style="bold yellow")
        table.add_column("Scope", style="cyan", width=20)
        table.add_column("内容", style="white", width=60)
        table.add_column("P", width=3)
        for f in facts:
            pin = "📌" if f.get("pinned") else ""
            table.add_row(f["scope"], f"{pin} {f['content'][:60]}", str(f["priority"]))
        console.print(table)

    if sessions:
        from rich.table import Table
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
    content: str = typer.Argument(None, help="要记住的内容（省略则从 stdin 读取）"),
    scope: str = typer.Option("global", "--scope", "-s", help="作用域：global 或 project:名称"),
    priority: int = typer.Option(3, "--priority", "-p", help="优先级 1-5"),
    pin: bool = typer.Option(False, "--pin", help="固定（永远出现在 context.md）"),
    tags: str = typer.Option("", help="Comma-separated tags (legacy)"),
):
    """保存一条记忆到 memory.db。支持从 stdin 读取长文本：echo "长内容" | engram remember"""
    import sys
    if content is None:
        if not sys.stdin.isatty():
            content = sys.stdin.read().strip()
        if not content:
            console.print("[red]请提供要记住的内容（参数或 stdin）[/red]")
            raise typer.Exit(1)
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
    if token:
        console.print("[dim]🔒 Token 已保存到 ~/.engram/config.json（权限 600，仅本人可读）[/dim]")


@app.command()
def push():
    """Push memory.db + core.md + context.md to configured backend."""
    from .config import get_backend
    from .storage.memory_db import MEMORY_DB
    from .context_gen import CONTEXT_FILE, CORE_FILE
    from pathlib import Path

    backend = get_backend()
    if backend.name == "local":
        console.print("[yellow]No remote backend configured. Use: engram config-backend gitee --token <PAT> --repo owner/repo[/yellow]")
        return

    sync_files = [
        (MEMORY_DB, "memory.db"),
        (CORE_FILE, "core.md"),
        (CONTEXT_FILE, "context.md"),
    ]
    ok_count = 0
    for fpath, remote_name in sync_files:
        if not fpath.exists():
            console.print(f"[dim]跳过 {remote_name}（不存在）[/dim]")
            continue
        if backend.upload(fpath, remote_name=remote_name):
            ok_count += 1
        else:
            console.print(f"[red]❌ 上传 {remote_name} 失败[/red]")

    if ok_count > 0:
        console.print(f"[green]☁️  已同步 {ok_count} 个文件到 {backend.name}（memory.db + core.md + context.md）[/green]")


@app.command()
def pull():
    """Pull memory.db + core.md + context.md from configured backend.
    
    安全合并：本地未推送的 facts 不会丢失（远端优先，本地独有 facts 保留）。
    """
    from .config import get_backend
    from .storage.memory_db import MEMORY_DB, list_facts, add_fact
    from .context_gen import CONTEXT_FILE, CORE_FILE
    import shutil, tempfile
    from pathlib import Path

    backend = get_backend()
    if backend.name == "local":
        console.print("[yellow]No remote backend configured.[/yellow]")
        return

    # ── 1. 保存本地 facts（pull 前快照）──
    local_facts_before = {f["id"]: f for f in list_facts()} if MEMORY_DB.exists() else {}

    # ── 2. 下载远端文件（memory.db 直接覆盖）──
    ok_files = []
    for fpath, remote_name in [(MEMORY_DB, "memory.db"), (CORE_FILE, "core.md"), (CONTEXT_FILE, "context.md")]:
        try:
            if backend.download(fpath, remote_name=remote_name):
                console.print(f"[green]✅ 下载 {remote_name}[/green]")
                ok_files.append(remote_name)
            else:
                console.print(f"[dim]⏭ {remote_name} 未找到（跳过）[/dim]")
        except Exception as e:
            console.print(f"[red]❌ 下载 {remote_name} 失败: {e}[/red]")
            console.print("[yellow]💡 提示：网络问题可稍后重试 engram pull[/yellow]")

    # ── 3. 合并：本地独有 facts 回写（防止本地未 push 的 facts 丢失）──
    if "memory.db" in ok_files and local_facts_before:
        remote_ids = {f["id"] for f in list_facts()}
        local_only = [f for fid, f in local_facts_before.items() if fid not in remote_ids]
        if local_only:
            for f in local_only:
                add_fact(f["scope"], f["content"], source=f.get("source", "manual"),
                         priority=f["priority"], pinned=bool(f["pinned"]))
            console.print(f"[cyan]🔀 合并 {len(local_only)} 条本地独有 facts（未丢失）[/cyan]")

    # ── 4. 重新生成 context 文件（core.md / context.md 已被新版覆盖）──
    if ok_files:
        from .context_gen import update_context_files
        update_context_files()
        console.print("[dim]🔄 context 文件已同步更新[/dim]")


@app.command("status")
def status_cmd():
    """显示 engram 整体状态：facts 数量、文件大小、backend 连通性、上次同步时间。"""
    from .config import get_backend, get_config
    from .storage.memory_db import MEMORY_DB, list_facts, get_all_scopes
    from .context_gen import CORE_FILE, CONTEXT_FILE
    from pathlib import Path
    import sqlite3, os

    console.print("\n[bold cyan]🧠 Engram Status[/bold cyan]\n")

    # ── Facts 统计 ──
    facts = list_facts()
    pinned = [f for f in facts if f["pinned"]]
    scopes = get_all_scopes()
    console.print(f"[bold]📌 Memory Facts:[/bold] {len(facts)} 条 (固定: {len(pinned)})")
    for scope in scopes:
        cnt = len([f for f in facts if f["scope"] == scope])
        limit = 50 if scope == "global" else 30
        bar = "█" * int(cnt / limit * 10)
        console.print(f"   {scope:<25} {cnt:>3}/{limit}  {bar}")

    # ── 文件状态 ──
    console.print()
    console.print("[bold]📂 Files:[/bold]")
    for label, path in [("memory.db", MEMORY_DB), ("core.md", CORE_FILE), ("context.md", CONTEXT_FILE)]:
        if path.exists():
            size = path.stat().st_size
            mtime = path.stat().st_mtime
            from datetime import datetime
            age = datetime.now() - datetime.fromtimestamp(mtime)
            age_str = f"{int(age.total_seconds()//60)}min ago" if age.total_seconds() < 3600 else f"{int(age.total_seconds()//3600)}h ago"
            if label.endswith(".md"):
                char_count = len(path.read_text(encoding="utf-8"))
                token_hint = f" (~{char_count//4} token)"
            else:
                token_hint = ""
            console.print(f"   {label:<15} {size:>7} bytes  updated {age_str}{token_hint}")
        else:
            console.print(f"   {label:<15} [dim]not found[/dim]")

    # ── core.md 大小警告 ──
    if CORE_FILE.exists():
        tokens = len(CORE_FILE.read_text(encoding="utf-8")) // 4
        if tokens > 80:
            console.print(f"   [yellow]⚠️  core.md {tokens} token，接近 100 token 上限！[/yellow]")

    # ── Backend 状态 ──
    console.print()
    cfg = get_config()
    backend_name = cfg.get("backend", "local")
    console.print(f"[bold]☁️  Backend:[/bold] {backend_name}")
    if backend_name != "local":
        repo = cfg.get("repo", "?")
        console.print(f"   Repo: {repo}")
        try:
            b = get_backend()
            ok = b.test_connection()
            console.print(f"   Connection: {'[green]✅ OK[/green]' if ok else '[red]❌ FAIL[/red]'}")
        except Exception as e:
            console.print(f"   Connection: [red]❌ {e}[/red]")

    console.print()
    console.print("[dim]Run [bold]engram pull[/bold] to sync from cloud | [bold]engram push[/bold] to upload[/dim]\n")


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

    # Group by scope for better readability
    from collections import defaultdict
    grouped = defaultdict(list)
    for f in facts:
        grouped[f["scope"]].append(f)

    for scope_name in sorted(grouped.keys()):
        scope_facts = grouped[scope_name]
        table = Table(title=f"📂 {scope_name}", show_header=True, header_style="bold cyan")
        table.add_column("ID", width=12)
        table.add_column("内容", width=50)
        table.add_column("P", width=3)
        table.add_column("📌", width=3)

        for f in scope_facts:
            table.add_row(
                f["id"],
                f["content"][:50],
                str(f["priority"]),
                "✓" if f["pinned"] else "",
            )
        console.print(table)
    console.print(f"\n共 {len(facts)} 条记忆（{len(grouped)} 个 scope）")


@app.command("context")
def context_cmd(
    update: bool = typer.Option(False, "--update", help="重新生成所有 context 文件"),
    show: bool = typer.Option(False, "--show", help="显示完整 context.md"),
    core: bool = typer.Option(False, "--core", help="只显示 core.md（@include 加载的极小核心）"),
):
    """管理 context 文件（Layer1 core.md + Layer2 context.md）。"""
    from engram.context_gen import update_context_files, CONTEXT_FILE, CORE_FILE

    if update:
        results = update_context_files()
        console.print("✅ context 文件已更新：")
        for r in results:
            console.print(f"   {r}")
        console.print(f"\n📌 核心文件（@include 用）：{CORE_FILE}")
        console.print(f"📄 完整摘要：{CONTEXT_FILE}")
    elif core:
        if CORE_FILE.exists():
            content = CORE_FILE.read_text()
            console.print(f"[dim]core.md ({len(content)} chars ≈ {len(content)//4} token):[/dim]\n")
            console.print(content)
        else:
            console.print("[dim]core.md 不存在，请先运行 engram context --update[/dim]")
    elif show:
        if CONTEXT_FILE.exists():
            console.print(CONTEXT_FILE.read_text())
        else:
            console.print("[dim]context.md 不存在，请先运行 engram context --update[/dim]")
    else:
        console.print("用法：")
        console.print("  engram context --update    重新生成所有文件")
        console.print("  engram context --core      查看 core.md（@include 实际加载的内容）")
        console.print("  engram context --show      查看完整 context.md")


@app.command("recent")
def recent(
    days: int = typer.Option(3, "--days", "-d", help="最近几天"),
    limit: int = typer.Option(10, "--limit", "-n", help="最多显示条数"),
    summary: bool = typer.Option(False, "--summary", help="精简摘要模式（适合注入 context）"),
    all_sessions: bool = typer.Option(False, "--all", help="显示包括系统/heartbeat会话"),
):
    """显示最近的会话记录（按时间倒序）。"""
    from engram.storage.db import list_sessions
    from engram.extractor_facts import _is_noise, SKIP_PROJECT_DIRS
    from datetime import datetime, timedelta
    import os

    sessions = list_sessions(limit=limit * 5)
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    recent_sessions = [
        s for s in sessions
        if (s.get("imported_at") or s.get("created_at") or "") >= cutoff
    ]

    if not all_sessions:
        # 过滤噪声（heartbeat/cron/system sessions）
        recent_sessions = [
            s for s in recent_sessions
            if not _is_noise(s.get("title") or "")
            and os.path.basename((s.get("project") or "").rstrip("/")) not in SKIP_PROJECT_DIRS
        ]

    recent_sessions = recent_sessions[:limit]

    if not recent_sessions:
        console.print(f"[dim]最近 {days} 天没有有效会话（heartbeat/cron 已过滤，加 --all 查看全部）[/dim]")
        return

    if summary:
        lines = [f"## 最近 {days} 天会话（{len(recent_sessions)} 条）", ""]
        for s in recent_sessions:
            ts = (s.get("created_at") or s.get("imported_at") or "")[:10]
            title = (s.get("title") or "")[:70]
            tool = s.get("source_tool", "")
            proj = s.get("project", "")
            proj_name = proj.split("/")[-1] if proj else ""
            lines.append(f"- [{ts}] `{tool}` **{title}**" + (f"（{proj_name}）" if proj_name else ""))
        console.print("\n".join(lines))
    else:
        from rich.table import Table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("时间", width=12)
        table.add_column("工具", width=12)
        table.add_column("项目", width=15)
        table.add_column("标题", width=45)
        for s in recent_sessions:
            ts = (s.get("created_at") or s.get("imported_at") or "")[:10]
            title = (s.get("title") or "")[:45]
            tool = s.get("source_tool", "")
            proj = (s.get("project") or "").split("/")[-1]
            table.add_row(ts, tool, proj, title)
        console.print(table)
        console.print(f"\n共 {len(recent_sessions)} 条（最近 {days} 天，噪声已过滤）")


@app.command("forget")
def forget(
    fact_id: str = typer.Argument(help="要删除的 fact ID（来自 engram facts）"),
):
    """删除一条记忆 fact。"""
    from engram.storage.memory_db import delete_fact
    if delete_fact(fact_id):
        console.print(f"✅ 已删除：{fact_id}")
    else:
        console.print(f"[yellow]未找到：{fact_id}[/yellow]")


if __name__ == "__main__":
    app()
