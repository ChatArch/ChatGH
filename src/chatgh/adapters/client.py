"""httpx.Client 工厂，注入 GitHub API base_url 和认证 token。"""

from __future__ import annotations

import subprocess
from typing import Optional

import httpx


GITHUB_API_BASE = "https://api.github.com"


def _token_from_git_credentials() -> Optional[str]:
    """从 git credential fill 取 github.com 的 token。"""
    credential_input = "protocol=https\nhost=github.com\n\n"
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input=credential_input,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            if key.strip() == "password":
                return value.strip() or None
    return None


def make_client(token: Optional[str] = None) -> httpx.Client:
    """
    构造 GitHub API httpx.Client。

    Token 解析顺序：
    1. 显式传入的 token 参数
    2. git credential fill（读取 ~/.git-credentials 或系统 keychain）
    3. 环境变量 GITHUB_TOKEN
    4. 无认证（匿名，60 次/小时限速）
    """
    import os

    resolved = (
        token
        or _token_from_git_credentials()
        or os.environ.get("GITHUB_TOKEN")
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "chatgh",
    }
    if resolved:
        headers["Authorization"] = f"Bearer {resolved}"

    return httpx.Client(base_url=GITHUB_API_BASE, headers=headers, timeout=30)
