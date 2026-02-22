"""生成 ~/.engram/context.md，用于文件注入。token 预算 800。"""
import json
from pathlib import Path
from datetime import datetime, timedelta
from .storage.memory_db import list_facts, get_all_scopes
from .storage.db import list_sessions

CONTEXT_FILE = Path.home() / ".engram" / "context.md"
PROJECT_CONTEXT_DIR = Path.home() / ".engram" / "projects"

BUDGET_CHARS = {
    "global_pinned": 800,
    "project_facts": 1600,
    "recent_activity": 800,
}

def _format_fact(f: dict) -> str:
    pin = "📌 " if f["pinned"] else ""
    return f"- {pin}{f['content']}"

def generate_global_context() -> str:
    lines = ["## Engram 全局记忆（自动更新）", f"_更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_", ""]

    pinned = list_facts(scope="global", pinned_only=True)
    if pinned:
        lines.append("### 📌 全局规则")
        chars = 0
        for f in pinned:
            line = _format_fact(f)
            chars += len(line)
            if chars > BUDGET_CHARS["global_pinned"]:
                break
            lines.append(line)
        lines.append("")

    other_global = list_facts(scope="global", pinned_only=False)
    other_global = [f for f in other_global if not f["pinned"]][:10]
    if other_global:
        lines.append("### 全局偏好与约定")
        for f in other_global:
            lines.append(_format_fact(f))
        lines.append("")

    scopes = get_all_scopes()
    project_scopes = [s for s in scopes if s.startswith("project:")]
    if project_scopes:
        lines.append("### 近期活跃项目")
        chars = 0
        for scope in project_scopes[:8]:
            proj_name = scope.replace("project:", "")
            facts = list_facts(scope=scope)[:3]
            if not facts:
                continue
            summary = f"- **{proj_name}**：" + "；".join(f["content"][:50] for f in facts)
            chars += len(summary)
            if chars > BUDGET_CHARS["project_facts"]:
                break
            lines.append(summary)
        lines.append("")

    recent = list_sessions(limit=30)
    if recent:
        from .extractor_facts import _is_noise, SKIP_PROJECT_DIRS
        import os
        clean = [
            s for s in recent
            if not _is_noise(s.get("title") or "")
            and os.path.basename((s.get("project") or "").rstrip("/")) not in SKIP_PROJECT_DIRS
        ][:5]
        if clean:
            lines.append("### 最近会话")
            chars = 0
            for s in clean:
                ts = (s.get("created_at") or s.get("imported_at") or "")[:10]
                title = (s.get("title") or "")[:60]
                tool = s.get("source_tool", "")
                line = f"- [{ts}] ({tool}) {title}"
                chars += len(line)
                if chars > BUDGET_CHARS["recent_activity"]:
                    break
                lines.append(line)

    return "\n".join(lines)

def generate_project_context(project_name: str) -> str:
    scope = f"project:{project_name}"
    facts = list_facts(scope=scope)
    if not facts:
        return ""

    lines = [
        f"## 项目记忆：{project_name}",
        f"_更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        ""
    ]
    pinned = [f for f in facts if f["pinned"]]
    others = [f for f in facts if not f["pinned"]]

    if pinned:
        lines.append("### 📌 关键规则")
        for f in pinned:
            lines.append(_format_fact(f))
        lines.append("")

    if others:
        lines.append("### 决策与记录")
        for f in others[:15]:
            lines.append(_format_fact(f))

    return "\n".join(lines)

def update_context_files():
    results = []
    global_content = generate_global_context()
    _atomic_write(CONTEXT_FILE, global_content)
    results.append(f"global: {len(global_content)} chars")

    scopes = get_all_scopes()
    for scope in scopes:
        if not scope.startswith("project:"):
            continue
        proj_name = scope.replace("project:", "")
        content = generate_project_context(proj_name)
        if content:
            proj_dir = PROJECT_CONTEXT_DIR / proj_name
            proj_dir.mkdir(parents=True, exist_ok=True)
            _atomic_write(proj_dir / "context.md", content)
            results.append(f"{proj_name}: {len(content)} chars")

    return results

def _atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    bak = path.with_suffix(".bak")
    tmp.write_text(content, encoding="utf-8")
    if path.exists():
        import shutil
        shutil.copy2(path, bak)
    tmp.rename(path)
