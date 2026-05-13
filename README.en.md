<div align="center">
    <a href="https://pypi.python.org/pypi/chatgh">
        <img src="https://img.shields.io/pypi/v/chatgh.svg" alt="PyPI version" />
    </a>
</div>

<div align="center">

[English](README.en.md) | [简体中文](README.md)
</div>

# chatgh

`chatgh` provides GitHub pull request, repository permission, token, and GitHub Actions helpers migrated from `chattool gh`. Use `chatgh` as the primary runtime entry point.

## Quick Start

```bash
pip install -e ".[dev]"
chatgh --help
chatgh pr --help
python -m pytest -q
```

## Common Workflows

Create a PR:

```bash
chatgh pr create --repo OWNER/REPO --base main --head feature-branch --title "Update docs" --body-file pr-body.md --token "$GITHUB_ACCESS_TOKEN"
```

View PRs:

```bash
chatgh pr list --repo OWNER/REPO --state open
chatgh pr view --repo OWNER/REPO --number 123
```

Wait for CI:

```bash
chatgh pr checks --repo OWNER/REPO --number 123 --wait --interval 15 --timeout 600
chatgh pr checks --repo OWNER/REPO --number 123 --json-output
```

Inspect workflow runs and job logs:

```bash
chatgh run view --repo OWNER/REPO --run-id 123456789
chatgh run logs --repo OWNER/REPO --job-id 987654321 --tail 200
chatgh run logs --repo OWNER/REPO --job-id 987654321 --output job.log
```

Configure a token:

```bash
chatgh repo-perms --repo OWNER/REPO --json-output
chatgh set-token --token "$GITHUB_ACCESS_TOKEN"
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

Token resolution order is explicit `--token`, repo-scoped git credential, then `GITHUB_ACCESS_TOKEN` from typed env. Recoverable missing parameters are resolved through `chatstyle`; `-I/--no-interactive` disables prompts and returns a clear error.

## Python API

```python
from chatgh.github.client import GitHubClient

client = GitHubClient(user_name="octocat", token="ghp_...")
prs = client.get_pull_requests("Hello-World")
```

Default local tests use mocks and do not call the live GitHub API.
