"""从会话中自动提炼记忆事实（关键词规则，无需 LLM）。"""
import re
from .storage.memory_db import add_fact

TRIGGER_KEYWORDS = [
    "注意", "坑", "bug", "bug fix", "修复", "不要", "never", "always",
    "必须", "must", "重要", "important", "critical", "warning",
    "决定", "决策", "选择", "方案", "架构", "设计",
    "TODO", "FIXME", "规则", "约定", "规范",
]

def _detect_project(session: dict) -> str:
    project = session.get("project", "") or ""
    if not project:
        return "unknown"
    import os
    name = os.path.basename(project.rstrip("/"))
    return name or "unknown"

def extract_facts_from_session(session: dict) -> list[str]:
    facts = []
    title = session.get("title", "")
    summary = session.get("summary", "")

    if title and len(title) > 10:
        facts.append(title[:120])

    if summary:
        for kw in TRIGGER_KEYWORDS:
            if kw.lower() in summary.lower():
                facts.append(summary[:150])
                break

    return list(set(facts))

def auto_extract_from_new_sessions(sessions: list) -> int:
    count = 0
    for session in sessions:
        proj_name = _detect_project(session)
        scope = f"project:{proj_name}" if proj_name != "unknown" else "global"
        extracted = extract_facts_from_session(session)
        for content in extracted:
            add_fact(scope=scope, content=content, source="auto", priority=2)
            count += 1
    return count
