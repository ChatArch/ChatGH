<div align="center">
    <a href="https://pypi.python.org/pypi/chatgh">
        <img src="https://img.shields.io/pypi/v/chatgh.svg" alt="PyPI version" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# chatgh

`chatgh` provides GitHub pull request, repository permission, token, and GitHub Actions helpers migrated from `chattool gh`. New workflows should use `chatgh` directly; any `chattool gh` entry point is a compatibility concern for ChatTool rather than the primary runtime.

## 快速开始

```bash
pip install -e ".[dev]"
chatgh --help
chatgh pr --help
python -m pytest -q
```

## 常用流程

创建 PR：

```bash
chatgh pr create --repo OWNER/REPO --base main --head feature-branch --title "Update docs" --body-file pr-body.md --token "$GITHUB_ACCESS_TOKEN"
```

查看 PR：

```bash
chatgh pr list --repo OWNER/REPO --state open
chatgh pr view --repo OWNER/REPO --number 123
```

等待 CI：

```bash
chatgh pr checks --repo OWNER/REPO --number 123 --wait --interval 15 --timeout 600
chatgh pr checks --repo OWNER/REPO --number 123 --json-output
```

查看 workflow run 和 job logs：

```bash
chatgh run view --repo OWNER/REPO --run-id 123456789
chatgh run logs --repo OWNER/REPO --job-id 987654321 --tail 200
chatgh run logs --repo OWNER/REPO --job-id 987654321 --output job.log
```

配置 token：

```bash
chatgh repo-perms --repo OWNER/REPO --json-output
chatgh set-token --token "$GITHUB_ACCESS_TOKEN"
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

Token 解析顺序保持为显式 `--token`、仓库级 git credential、typed env 中的 `GITHUB_ACCESS_TOKEN`。缺少可恢复参数时，命令通过 `chatstyle` 支持默认交互补全；`-I/--no-interactive` 会禁用交互并返回清晰错误。

## Python API

```python
from chatgh.github.client import GitHubClient

client = GitHubClient(user_name="octocat", token="ghp_...")
prs = client.get_pull_requests("Hello-World")
```

底层模块也可按需导入：`chatgh.github.api`、`chatgh.github.commands`、`chatgh.github.requests`、`chatgh.github.render`。

## 开发

```bash
python -m pytest -q
```

真实 GitHub API 调用不属于默认本地验收；默认测试使用 mock/fake payload，避免污染真实 git credential 或 env 配置。
