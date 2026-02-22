"""Engram configuration management."""
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".engram" / "config.json"


def get_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"backend": "local"}


def save_config(config: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    CONFIG_PATH.chmod(0o600)


def get_backend():
    config = get_config()
    backend_name = config.get("backend", "local")
    if backend_name == "local":
        from engram.backends.local import LocalBackend
        return LocalBackend()
    elif backend_name in ("github", "gitee"):
        from engram.backends.github import GitHubBackend, GiteeBackend
        token = config.get("token", "")
        repo = config.get("repo", "")
        if backend_name == "gitee":
            return GiteeBackend(token, repo)
        return GitHubBackend(token, repo)
    elif backend_name == "webdav":
        from engram.backends.webdav import WebDAVBackend
        return WebDAVBackend(config["url"], config["username"], config["password"])
    elif backend_name == "s3":
        from engram.backends.s3 import S3Backend
        return S3Backend(config["endpoint_url"], config["access_key"], config["secret_key"], config["bucket"])
    from engram.backends.local import LocalBackend
    return LocalBackend()
