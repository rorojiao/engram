import base64
import requests
from pathlib import Path
from .base import BaseBackend


class GitHubBackend(BaseBackend):
    name = "github"

    def __init__(self, token: str, repo: str, host: str = "github"):
        self.token = token
        self.repo = repo
        if host == "gitee":
            self.api_base = "https://gitee.com/api/v5"
        else:
            self.api_base = "https://api.github.com"
        self.headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
        self.filename = "engram.db.b64"

    def _get_file_sha(self):
        url = f"{self.api_base}/repos/{self.repo}/contents/{self.filename}"
        r = requests.get(url, headers=self.headers, timeout=15)
        if r.status_code == 200:
            return r.json().get("sha")
        return None

    def upload(self, local_path: Path) -> bool:
        try:
            content = base64.b64encode(local_path.read_bytes()).decode()
            sha = self._get_file_sha()
            url = f"{self.api_base}/repos/{self.repo}/contents/{self.filename}"
            payload = {"message": "engram sync", "content": content}
            if sha:
                payload["sha"] = sha
            r = requests.put(url, headers=self.headers, json=payload, timeout=30)
            return r.status_code in (200, 201)
        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download(self, local_path: Path) -> bool:
        try:
            url = f"{self.api_base}/repos/{self.repo}/contents/{self.filename}"
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code != 200:
                return False
            content = base64.b64decode(r.json()["content"].replace("\n", ""))
            local_path.write_bytes(content)
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            url = f"{self.api_base}/repos/{self.repo}"
            r = requests.get(url, headers=self.headers, timeout=10)
            return r.status_code == 200
        except Exception:
            return False


class GiteeBackend(BaseBackend):
    """Gitee backend — uses access_token param (Gitee API v5)."""
    name = "gitee"

    def __init__(self, token: str, repo: str):
        self.token = token
        self.repo = repo  # owner/repo
        self.api_base = "https://gitee.com/api/v5"
        self.filename = "engram.db.b64"

    def _params(self):
        return {"access_token": self.token}

    def _get_sha(self):
        r = requests.get(
            f"{self.api_base}/repos/{self.repo}/contents/{self.filename}",
            params=self._params(), timeout=15
        )
        return r.json().get("sha") if r.status_code == 200 else None

    def upload(self, local_path: Path) -> bool:
        try:
            content = base64.b64encode(local_path.read_bytes()).decode()
            sha = self._get_sha()
            payload = {"message": "engram sync", "content": content, "access_token": self.token}
            if sha:
                payload["sha"] = sha
            method = requests.put if sha else requests.post
            r = method(
                f"{self.api_base}/repos/{self.repo}/contents/{self.filename}",
                json=payload, timeout=30
            )
            return r.status_code in (200, 201)
        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download(self, local_path: Path) -> bool:
        try:
            r = requests.get(
                f"{self.api_base}/repos/{self.repo}/contents/{self.filename}",
                params=self._params(), timeout=15
            )
            if r.status_code != 200:
                return False
            content = base64.b64decode(r.json()["content"].replace("\n", ""))
            local_path.write_bytes(content)
            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            r = requests.get(
                f"{self.api_base}/repos/{self.repo}",
                params=self._params(), timeout=10
            )
            return r.status_code == 200
        except Exception:
            return False
