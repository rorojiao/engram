"""从会话中自动提炼记忆事实（关键词规则，无需 LLM）。"""
import re
import os
from pathlib import Path
from .storage.memory_db import add_fact

# 触发关键词：包含这些词的摘要/标题才值得提炼
TRIGGER_KEYWORDS = [
    "注意", "坑", "bug", "修复", "不要", "never", "always",
    "必须", "must", "重要", "important", "critical", "warning",
    "决定", "决策", "方案", "架构", "设计",
    "TODO", "FIXME", "规则", "约定", "规范",
    "fix", "解决", "完成", "部署", "配置",
]

# 噪声模式：匹配这些的内容直接跳过
NOISE_PATTERNS = [
    r"^\[message_id:",           # OpenClaw 消息 ID
    r"^\[Subagent Context\]",    # 子代理上下文
    r"^\[(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ",  # 时间戳开头
    r"^Read HEARTBEAT\.md",      # Heartbeat 指令
    r"^HEARTBEAT_OK",
    r"A cron job .* (just completed|failed)",  # cron 汇报
    r"^\[System Message\]",
    r"^Pre-compaction memory flush",
    r"^你好$|^hii?$|^hello$|^hi$",  # 简短测试消息
    r"^What is \d",              # 测试问题
    r"^Greeting in",             # 测试标题
]

# 无意义的项目目录（不提炼为 project scope）
SKIP_PROJECT_DIRS = {
    "workspace",   # OpenClaw 工作空间（是 agent 的家，不是用户项目）
    "msdn",        # 用户主目录
    "clawd",       # Claude.ai 接入目录
    "home",
    "root",
    "",
    "unknown",
}

# 用户 home 目录（动态，跨平台）
_HOME = str(Path.home())


def _is_noise(text: str) -> bool:
    """判断内容是否是噪声，需要跳过。"""
    if not text or len(text.strip()) < 10:
        return True
    t = text.strip()
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, t, re.IGNORECASE):
            return True
    return False


def _detect_project(session: dict) -> str:
    """从 session 推断项目名称，返回 None 表示无意义项目。"""
    project = session.get("project", "") or ""
    if not project:
        return None

    # 规范化路径，去掉末尾斜杠
    project = project.rstrip("/")

    # 必须在用户 home 下的子目录，且不是 home 本身
    if not project.startswith(_HOME + "/"):
        # 不在 home 下（例如 /root/ 或相对路径），用目录名判断
        name = os.path.basename(project)
        if name in SKIP_PROJECT_DIRS or len(name) < 2:
            return None
        return name

    # 取相对于 home 的路径，例如 /home/msdn/engram → engram
    rel = project[len(_HOME) + 1:]  # "engram" 或 "projects/engram"
    parts = rel.split("/")
    if not parts:
        return None

    # 取第一级目录名作为项目名
    name = parts[0]
    if name in SKIP_PROJECT_DIRS or len(name) < 2:
        return None
    # 跳过隐藏目录（以 . 开头，如 .openclaw、.config、.local 等系统目录）
    if name.startswith("."):
        return None

    return name


def _has_trigger_keyword(text: str) -> bool:
    t = text.lower()
    return any(kw.lower() in t for kw in TRIGGER_KEYWORDS)


def extract_facts_from_session(session: dict) -> list[str]:
    """从单个会话中提取关键记忆片段，返回提炼出的 fact 内容列表。"""
    facts = []
    title = (session.get("title") or "").strip()
    summary = (session.get("summary") or "").strip()
    source_tool = session.get("source_tool", "")

    # OpenClaw 的 workspace 会话大量是 heartbeat/cron，全部跳过 title 提炼
    # 只有包含触发关键词才提炼
    if source_tool == "openclaw":
        if summary and _has_trigger_keyword(summary) and not _is_noise(summary):
            facts.append(summary[:150])
        return facts

    # 其他工具：title 是好的 fact 来源
    if title and not _is_noise(title) and len(title) > 15:
        if _has_trigger_keyword(title) or source_tool in ("claude_code", "cursor"):
            facts.append(title[:120])

    # summary 包含触发关键词
    if summary and not _is_noise(summary) and _has_trigger_keyword(summary):
        facts.append(summary[:150])

    return list(set(facts))


def auto_extract_from_new_sessions(sessions: list) -> int:
    """批量从新会话中提炼 facts，写入 memory.db。返回提炼条数。"""
    count = 0
    for session in sessions:
        proj_name = _detect_project(session)
        if proj_name is None:
            continue  # 无意义项目，跳过

        scope = f"project:{proj_name}"
        extracted = extract_facts_from_session(session)
        for content in extracted:
            if not _is_noise(content):
                add_fact(scope=scope, content=content, source="auto", priority=2)
                count += 1
    return count
