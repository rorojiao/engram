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

    def upload(self, local_path: Path, remote_name: str = None) -> bool:
        try:
            fname = remote_name or self.filename
            content = base64.b64encode(local_path.read_bytes()).decode()
            url = f"{self.api_base}/repos/{self.repo}/contents/{fname}"
            # Get SHA for this specific file
            r = requests.get(url, headers=self.headers, timeout=15)
            sha = r.json().get("sha") if r.status_code == 200 else None
            payload = {"message": "engram sync", "content": content}
            if sha:
                payload["sha"] = sha
            r = requests.put(url, headers=self.headers, json=payload, timeout=30)
            return r.status_code in (200, 201)
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"Upload failed: {e}")
            return False

    def download(self, local_path: Path, remote_name: str = None) -> bool:
        try:
            fname = remote_name or self.filename
            url = f"{self.api_base}/repos/{self.repo}/contents/{fname}"
            r = requests.get(url, headers=self.headers, timeout=15)
            if r.status_code != 200:
                return False
            content = base64.b64decode(r.json()["content"].replace("\n", ""))
            local_path.write_bytes(content)
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"Download failed: {e}")
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

    def _get_sha_for(self, filename: str):
        r = requests.get(
            f"{self.api_base}/repos/{self.repo}/contents/{filename}",
            params=self._params(), timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                return data.get("sha")
        return None

    def _upload_file(self, local_path: Path, remote_name: str) -> bool:
        try:
            content = base64.b64encode(local_path.read_bytes()).decode()
            sha = self._get_sha_for(remote_name)
            payload = {"message": "engram sync", "content": content, "access_token": self.token}
            if sha:
                payload["sha"] = sha
            method = requests.put if sha else requests.post
            r = method(
                f"{self.api_base}/repos/{self.repo}/contents/{remote_name}",
                json=payload, timeout=30
            )
            return r.status_code in (200, 201)
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"Upload {remote_name} failed: {e}")
            return False

    def upload(self, local_path: Path, remote_name: str = None) -> bool:
        """上传单个文件。remote_name 指定远端文件名。"""
        fname = remote_name or local_path.name
        return self._upload_file(local_path, fname)

    def download(self, local_path: Path, remote_name: str = None) -> bool:
        """下载单个文件。remote_name 指定远端文件名。"""
        fname = remote_name or self.filename
        try:
            r = requests.get(
                f"{self.api_base}/repos/{self.repo}/contents/{fname}",
                params=self._params(), timeout=15
            )
            if r.status_code != 200:
                return False
            content = base64.b64decode(r.json()["content"].replace("\n", ""))
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)
            return True
        except Exception as e:
            import logging; logging.getLogger("engram").warning(f"Download {fname} failed: {e}")
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
