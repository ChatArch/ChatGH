# chatgh

`chatgh` is the ChatArch GitHub CLI and Python API package. It carries the PR, CI, Actions run/job log, repository permission, and token configuration features migrated from `chattool gh`. New scripts and docs should call `chatgh` directly; `chattool gh` is only a ChatTool-side compatibility entry point.

## Installation

```bash
pip install chatgh
# development
pip install -e ".[dev]"
```

## Configuration Model

Default behavior:

- `repo`: explicit `--repo owner/repo` wins; otherwise `chatgh` infers the repository from the current git remote.
- `token`: explicit `--token` wins, then the repo-scoped git credential, then `GITHUB_ACCESS_TOKEN` from typed env.
- Output: human-readable by default; commands with `--json-output` emit stable JSON for scripts.

### Token Sources

Token resolution order is stable:

1. Explicit `--token`.
2. Repo-scoped git credential keyed by normalized `owner/repo` without a `.git` suffix.
3. `GITHUB_ACCESS_TOKEN` from typed env.

Use `chatenv` to inspect or configure typed env:

```bash
chatenv init -t gh
chatenv cat -t gh
```

`ghp_xxx` and `github_pat_xxx` are GitHub Personal Access Tokens. Clone/fetch/push usually require contents read/write permissions; PR comments, merges, and Actions inspection may require additional repository permissions.

### Repository Inference

When `--repo` is omitted, `chatgh` checks git remotes in the current repository. It tries `origin` first, then other remotes. Supported forms:

- `https://github.com/octocat/Hello-World.git`
- `https://github.com/octocat/Hello-World`
- `git@github.com:octocat/Hello-World.git`
- `ssh://git@github.com/octocat/Hello-World.git`

When writing repo-scoped credentials, the credential path is normalized to `octocat/Hello-World`.

## CLI Entry Points

```bash
chatgh --help
chatgh pr --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

Command tree:

- `chatgh pr create`: create a pull request.
- `chatgh pr list`: list pull requests.
- `chatgh pr view`: show PR details including `mergeable` / `mergeable_state`.
- `chatgh pr checks`: summarize combined status, check runs, and workflow runs for the PR head commit.
- `chatgh pr comment`: add a PR comment.
- `chatgh pr merge`: merge a PR; `--check` performs a CI/mergeability guard first.
- `chatgh pr edit`: update title, body, state, or base branch.
- `chatgh run view`: show a workflow run and its jobs.
- `chatgh run logs`: show job logs, with tail and file output support.
- `chatgh repo-perms`: show token permissions and derived capabilities.
- `chatgh set-token`: configure a repo-scoped HTTPS token for the current GitHub repository.

## Common Workflows

### Create A PR

Prefer `--body-file` so shell quoting does not damage Markdown:

```bash
cat > /tmp/pr_body.md <<'EOF'
## Summary
- migrate GitHub helpers to chatgh

## Testing
- python -m pytest -q
EOF

chatgh pr create \
  --repo octocat/Hello-World \
  --base main \
  --head feature-branch \
  --title "feat: migrate github helpers" \
  --body-file /tmp/pr_body.md
```

When `base` / `head` / `title` are missing and the terminal is interactive, the command prompts for them. Explicit `-I` disables prompts.

### View PRs

```bash
chatgh pr list --repo octocat/Hello-World --state open --limit 20
chatgh pr view --repo octocat/Hello-World --number 123
chatgh pr view --repo octocat/Hello-World --number 123 --json-output
```

`pr view` output includes:

- PR number, title, state, author, and URL.
- base/head branches.
- `mergeable` and `mergeable_state`.
- created/updated/merged timestamps.

### Inspect And Wait For CI

```bash
chatgh pr checks --repo octocat/Hello-World --number 123
chatgh pr checks --repo octocat/Hello-World --number 123 --wait
chatgh pr checks --repo octocat/Hello-World --number 123 --wait --interval 10 --timeout 600
chatgh pr checks --repo octocat/Hello-World --number 123 --json-output
```

`pr checks` summarizes three layers for the PR head commit:

- combined status
- check runs
- workflow runs

`--wait` keeps polling until statuses, check runs, and workflow runs finish:

- No timeout by default.
- `--interval <seconds>` controls polling interval.
- Only explicit `--timeout <seconds>` enables timeout failure.

If the GitHub token cannot access the check-runs API, the command stores that error in the payload while still showing combined status and workflow runs when available.

### Inspect Actions Runs And Job Logs

```bash
chatgh run view --repo octocat/Hello-World --run-id 123456789
chatgh run view --repo octocat/Hello-World --run-id 123456789 --json-output

chatgh run logs --repo octocat/Hello-World --job-id 987654321
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 0
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 200 --output job.log
```

`run logs` shows tail output by default; `--tail 0` prints the full log; `--output` writes the full log to a file while the terminal still shows the selected tail.

### Comment, Merge, And Edit PRs

```bash
chatgh pr comment --repo octocat/Hello-World --number 123 --body "Looks good"

chatgh pr merge --repo octocat/Hello-World --number 123 --method squash
chatgh pr merge --repo octocat/Hello-World --number 123 --method squash --check

chatgh pr edit --repo octocat/Hello-World --number 123 --title "New title"
chatgh pr edit --repo octocat/Hello-World --number 123 --body-file /tmp/pr_body.md
chatgh pr edit --repo octocat/Hello-World --number 123 --state closed
chatgh pr edit --repo octocat/Hello-World --number 123 --base main
```

`pr merge --check` refuses to merge when:

- The PR is currently `mergeable=False`.
- `mergeable_state` is `dirty`, `blocked`, `behind`, `draft`, or `unknown`.
- combined status, check runs, or workflow runs have failed, cancelled, or incomplete items.

Without `--check`, the command keeps the direct GitHub merge API behavior.

### Configure And Inspect Tokens

```bash
chatgh repo-perms --repo octocat/Hello-World --json-output
chatgh repo-perms --repo octocat/Hello-World --full-json

chatgh set-token --token "$GITHUB_ACCESS_TOKEN"
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

`repo-perms` shows:

- token source and masked token.
- `permissions` returned by GitHub.
- derived capabilities: `can_read_pr`, `can_comment_pr`, `can_merge_pr`, `can_view_checks`, `can_view_actions`.

`set-token` only works when the current directory has a recognizable GitHub remote. By default it writes only a repo-scoped git credential; `--save-env` also writes `GITHUB_ACCESS_TOKEN` to typed env.

## Interactive Mode

Recoverable missing parameters are handled through `chatstyle`:

- Default mode: prompt automatically when a terminal is interactive and required values are missing.
- `-i/--interactive`: force prompting.
- `-I/--no-interactive`: disable prompts and fail clearly when required values are missing.

Token inputs use password prompts and are not echoed.

## Recommended PR/CI Workflow

Before creating a PR, reporting CI status, or preparing to merge, fetch the latest base:

```bash
git fetch origin main
```

Then confirm:

- `chatgh pr view` / `chatgh pr checks` do not show `mergeable=False` or `mergeable_state=dirty`.
- You have locally merged or rebased against the latest base and run the most relevant tests on that result.
- Use `chatgh pr checks --wait` when you need a terminal CI result; do not rely on a one-shot snapshot.

## Python API

```python
from chatgh.github.client import GitHubClient

client = GitHubClient(user_name="octocat", token="ghp_...")
prs = client.get_pull_requests("Hello-World")
view = client.get_pr_view("octocat/Hello-World", 1)
checks = client.get_pr_checks("octocat/Hello-World", 1)
```

Lower-level modules are also available:

- `chatgh.github.api`: token, repository inference, git credential, and REST request helpers.
- `chatgh.github.commands`: workflow functions used by the CLI.
- `chatgh.github.requests`: PR/checks/actions payload construction.
- `chatgh.github.render`: human-readable output, merge blockers, and tail helpers.

## Relationship With ChatTool

The long-term `chattool gh` implementation has moved to `chatgh`. ChatTool may keep a thin wrapper for compatibility, but it should not maintain a forked GitHub implementation. ChatTool helpers that need GitHub token/remote logic should import `chatgh.github.api`.

## Development Reference

When extending `chatgh`, prefer official documentation:

- GitHub REST API: https://docs.github.com/en/rest
- Pull requests API: https://docs.github.com/en/rest/pulls/pulls
- Check runs API: https://docs.github.com/en/rest/checks/runs
- Workflow runs API: https://docs.github.com/en/rest/actions/workflow-runs
- Workflow jobs API: https://docs.github.com/en/rest/actions/workflow-jobs
- Commit statuses API: https://docs.github.com/en/rest/commits/statuses
- PyGithub: https://pygithub.readthedocs.io/

Local validation:

```bash
python -m pytest -q
python -m build
mkdocs build --strict
```

Default tests use mock/fake payloads and temporary paths. They do not call the live GitHub API or write real git credentials or env config.
