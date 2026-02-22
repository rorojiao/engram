"""Gitee backend for Engram sync."""
from .github import GitHubBackend


class GiteeBackend(GitHubBackend):
    name = "gitee"

    def __init__(self, token: str, repo: str):
        super().__init__(token, repo, host="gitee")
