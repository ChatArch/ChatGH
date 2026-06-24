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
- `token`: explicit `--token` wins, then the repo-local HTTPS auth header in the current repository's `.git/config`, then `GITHUB_ACCESS_TOKEN` from typed env.
- Output: human-readable by default; commands with `--json-output` emit stable JSON for scripts.

### Token Sources

Token resolution order is stable:

1. Explicit `--token`.
2. Repo-local HTTPS auth header in the current repository's `.git/config`, with the path normalized to `https://github.com/owner/repo.git`.
3. `GITHUB_ACCESS_TOKEN` from typed env.

Use `chatenv` to inspect or configure typed env:

```bash
chatenv init -t gh
chatenv cat -t gh
```

After `chatgh` is installed, it registers `GitHubConfig` through the `chatenv.configs` entry point, so `chatenv list` shows a `[GitHub]` group and `-t gh` / `-t github` resolve to the same GitHub typed env.

`ghp_xxx` and `github_pat_xxx` are GitHub Personal Access Tokens. Clone/fetch/push usually require contents read/write permissions; PR comments, merges, and Actions inspection may require additional repository permissions.

### Repository Inference

When `--repo` is omitted, `chatgh` checks git remotes in the current repository. It tries `origin` first, then other remotes. Supported forms:

- `https://github.com/octocat/Hello-World.git`
- `https://github.com/octocat/Hello-World`
- `git@github.com:octocat/Hello-World.git`
- `ssh://git@github.com/octocat/Hello-World.git`

When writing a repo-local HTTPS auth header, the path is normalized to `https://github.com/octocat/Hello-World.git`.

## CLI Entry Points

```bash
chatgh --help
chatgh pr --help
chatgh repo --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

Command tree:

- `chatgh pr list`: generated-layer PR list.
- `chatgh pr view NUMBER`: generated-layer PR details.
- `chatgh pr checks NUMBER`: generated-layer PR head commit check runs.
- `chatgh repo list`: list repositories for a user/org; defaults to table output and supports `--json-output`, `--limit`, `--sort updated|created|pushed|name|stars|open-prs|open-issues`, and `--direction asc|desc`, with visibility, stars, open PRs/issues, and timestamps.
- `chatgh repo create`: create a repository; defaults to private and supports `--public`.
- `chatgh repo fork`: fork a source repository into a target user/org, with optional target name, `--default-branch-only`, `--if-exists use`, and JSON output.
- `chatgh repo protection`: inspect default-branch protection and repository rulesets for one repo or for an owner inventory; use this instead of crowding governance fields into `repo list`.
- The public `chatgh pr` command surface includes `list/create/view/comment/edit/checks/merge`; write commands use the same ChatGH token resolution and keep secrets out of output.
- `chatgh run view`: show a workflow run and its jobs.
- `chatgh run logs`: show job logs, with tail and file output support.
- `chatgh repo-perms`: show token permissions and derived capabilities.
- `chatgh set-token`: configure a repo-scoped HTTPS token for the current GitHub repository.

## Common Workflows

### Create A PR

```bash
chatgh pr create --repo octocat/Hello-World --base main --head rex/feature --title "Add feature" --body-file pr-body.md
chatgh pr create --repo octocat/Hello-World --base main --head rex/feature --title "Add feature" --body "Short body" --json-output
```

`pr create` uses the existing ChatGH token resolution flow and does not print tokens. Missing `base/head/title` values can be prompted interactively; use `-I` to fail clearly in non-interactive mode.

### View PRs

```bash
chatgh pr list --repo octocat/Hello-World --state open --limit 20
chatgh pr view 123 --repo octocat/Hello-World
chatgh pr view 123 --repo octocat/Hello-World --json-output
```

`pr view` output includes:

- PR number, title, state, author, and URL.
- base/head branches.
- `mergeable` and `mergeable_state`.
- created/updated/merged timestamps.

### Inspect CI

```bash
chatgh pr checks 123 --repo octocat/Hello-World
chatgh pr checks 123 --repo octocat/Hello-World --json-output
```

`pr checks` summarizes three layers for the PR head commit:

- combined status
- check runs
- workflow runs

The public CLI currently does not expose `--wait` / `--interval` / `--timeout`; when a terminal CI result is needed, poll `chatgh pr checks` from the surrounding workflow.

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
chatgh pr comment 123 --repo octocat/Hello-World --body-file review-note.md
chatgh pr edit 123 --repo octocat/Hello-World --title "New title" --body-file pr-body.md
chatgh pr merge 123 --repo octocat/Hello-World --method squash --check
```

`pr merge` defaults to `--method squash` and `--check`, reading PR checks before merge and refusing non-green states. Merging is still a high-risk remote mutation; confirm PR status and user authorization before running it.

### Fork Repositories

```bash
chatgh repo fork --source octocat/Hello-World --owner ChatArch
chatgh repo fork --source octocat/Hello-World --owner ChatArch --name hello-world-copy --default-branch-only
chatgh repo fork --source octocat/Hello-World --owner ChatArch --if-exists use --json-output
```

`repo fork` uses the GitHub Fork API. The target repository name defaults to the source repository name. Organization targets send GitHub's `organization` field; user-account targets require `--owner` to match the authenticated user. `--if-exists use` only reuses an existing fork when it matches the requested source, avoiding false success on an unrelated same-name repository.

### Inspect Repository Protection

```bash
chatgh repo protection --repo octocat/Hello-World
chatgh repo protection --repo octocat/Hello-World --json-output
chatgh repo protection --owner octocat --limit 50 --jobs 8
chatgh repo protection --owner octocat --limit 50 --jobs 8 --json-output
```

`repo protection` reports the default branch, whether it is protected, classic branch protection details such as required PR reviews / review count / force-push and deletion flags, and repository ruleset summaries when GitHub exposes them. Some private repositories may return a GitHub plan/visibility error for rulesets; the command preserves that error in JSON while still reporting the branch protection state when available. Owner inventory mode lists repositories first, then checks each repository concurrently with `--jobs` while preserving stable output order.

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

`set-token` only works when the current directory has a recognizable GitHub remote. By default it writes only the current repository's `.git/config`:

```ini
[http "https://github.com/octocat/Hello-World.git"]
    extraHeader = Authorization: Basic <base64(x-access-token:TOKEN)>
```

Do not put tokens in remote URLs, and do not log raw `extraHeader` values. With `--save-env`, `set-token` also writes typed env `GITHUB_ACCESS_TOKEN`.

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
- Poll `chatgh pr checks` from the surrounding workflow when you need a terminal CI result; do not rely on a one-shot snapshot.

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
