# ChatGH Interface Tree

ChatGH follows a GitHub-familiar resource model for GitHub APIs, while keeping ChatGH-specific credential, JSON, safety, and Python API contracts. The current package is GitHub-only; Gitea/Forgejo exploration belongs in ChatTea or a future provider-neutral layer unless a ChatGH command has an explicit GitHub-compatible purpose.

## Current CLI Surface

```text
chatgh
├── pr
│   ├── list
│   ├── create
│   ├── view
│   ├── comment
│   ├── edit
│   ├── checks
│   ├── merge
│   ├── status
│   ├── diff
│   ├── close
│   ├── reopen
│   ├── review
│   ├── ready
│   └── update-branch
├── repo
│   ├── list
│   ├── create
│   ├── fork
│   ├── protection
│   ├── view
│   ├── clone
│   ├── sync
│   └── edit
├── project
│   ├── list
│   ├── view
│   ├── create
│   ├── edit
│   ├── close
│   ├── delete
│   ├── copy
│   ├── link
│   ├── unlink
│   ├── mark-template
│   ├── item
│   │   ├── list
│   │   ├── add
│   │   ├── create
│   │   ├── edit
│   │   ├── archive
│   │   └── delete
│   └── field
│       ├── list
│       ├── create
│       └── delete
├── run
│   ├── list
│   ├── view
│   ├── logs
│   ├── watch
│   ├── rerun
│   ├── cancel
│   └── download
├── invitation
│   ├── list
│   ├── accept
│   └── decline
├── repo-perms
└── set-token
```

## Target CLI Direction

Future API work should grow only when it is backed by one of these evidence sources:

1. An official `gh` command shape or help page.
2. A GitHub REST or GraphQL endpoint.
3. A GitHub App/webhook model documented by GitHub.
4. An explicitly designed ChatGH local capability, such as credential setup, webhook payload normalization, or a runner bridge.

Confirmed target domains:

- `repo`
- `issue`
- `pr`
- `project`
- `run`
- `workflow`
- `job`
- `artifact`
- `check-run`
- `status`
- `webhook`
- `app`
- `agent-task` / `agent` / `agents`
- `skill` / `skills`

ChatGH-specific custom commands stay:

- `set-token`: configure repo-local HTTPS auth header and optionally ChatEnv `GITHUB_ACCESS_TOKEN`.
- `repo-perms`: inspect token permissions and derived ChatGH capabilities.
- `agent event ...`: future local event-to-runner bridge, if implemented; this should not pretend to be GitHub Copilot's hosted agent runtime.

## Responsibilities

- `set-token`: store a GitHub token for the current repository in repo-local git config, optionally saving it to ChatEnv.
- `repo-perms`: resolve the current token, read repository permissions, and derive ChatGH capabilities.
- `repo list/view/create/edit/fork/clone/sync/protection`: cover repository inventory, mutation, local checkout, fork creation, and governance inspection.
- `pr list/create/view/comment/edit/checks/merge/status/diff/close/reopen/review/ready/update-branch`: cover PR lifecycle, review, merge gating, and CI inspection.
- `project ...`: cover GitHub Projects v2 through ChatGH's Project/item/field command tree, not the official `gh project` flat aliases.
- `run list/view/logs/watch/rerun/cancel/download`: cover GitHub Actions workflow run operations and job logs.
- `invitation list/accept/decline`: cover authenticated user repository invitations.
- Future `webhook`: create/list/test/delete repository or organization webhooks, plus verify/normalize webhook payloads.
- Future `app`: manage GitHub App installation token flows and app installation inventory.
- Future `agent-task`: align naming with official `gh agent-task`, while keeping ChatGH implementation provider-neutral unless explicitly integrating GitHub Copilot/CAPI.
- Future `skill`: align with official `gh skill` and Agent Skills conventions when ChatGH needs to inspect or install repository-published agent skills.

## CLI To Python Function Mapping

Every public CLI command should have an importable Python function or method behind it. Integrations, gateway services, MCP tools, and future agent runtimes should call Python APIs directly instead of shelling out when possible.

```text
chatgh set-token              -> chatgh.github.commands.configure_github_https_token / save_github_token_to_env
chatgh repo-perms             -> chatgh.github.commands.get_repo_permissions / derive_repo_capabilities
chatgh repo list              -> chatgh.github.commands.list_repos
chatgh repo create            -> chatgh.github.commands.create_repo
chatgh repo fork              -> chatgh.github.commands.fork_repo
chatgh repo protection        -> chatgh.github.commands.inspect_repo_protection / list_repo_protections
chatgh repo view              -> chatgh.github.commands.view_repo
chatgh repo clone             -> chatgh.github.commands.clone_repo
chatgh repo sync              -> chatgh.github.commands.sync_repo
chatgh repo edit              -> chatgh.github.commands.edit_repo
chatgh pr list                -> chatgh.github.commands.list_prs
chatgh pr create              -> chatgh.github.commands.create_pr
chatgh pr view                -> chatgh.github.commands.view_pr
chatgh pr comment             -> chatgh.github.commands.comment_pr
chatgh pr edit                -> chatgh.github.commands.edit_pr
chatgh pr checks              -> chatgh.github.commands.check_pr
chatgh pr merge               -> chatgh.github.commands.merge_pr
chatgh pr status              -> chatgh.github.commands.status_prs
chatgh pr diff                -> chatgh.github.commands.diff_pr
chatgh pr close               -> chatgh.github.commands.close_pr
chatgh pr reopen              -> chatgh.github.commands.reopen_pr
chatgh pr review              -> chatgh.github.commands.review_pr
chatgh pr ready               -> chatgh.github.commands.ready_pr
chatgh pr update-branch       -> chatgh.github.commands.update_pr_branch
chatgh run list               -> chatgh.github.commands.list_runs
chatgh run view               -> chatgh.github.commands.view_run
chatgh run logs               -> chatgh.github.commands.run_logs
chatgh run watch              -> chatgh.github.commands.watch_run
chatgh run rerun              -> chatgh.github.commands.rerun_run
chatgh run cancel             -> chatgh.github.commands.cancel_run
chatgh run download           -> chatgh.github.commands.download_run_artifacts
chatgh invitation list        -> chatgh.github.commands.list_invitations
chatgh invitation accept      -> chatgh.github.commands.accept_invitation
chatgh invitation decline     -> chatgh.github.commands.decline_invitation
chatgh project ...            -> chatgh.github.projects + chatgh.github.project_cli thin wrappers
```

## Agent And Bot Direction

See `docs/agent-definition.md` for the ChatGH robot/Agent product definition, manifest shape, lifecycle, GitHub-native flow, permissions, runtime, and bilingual configuration examples. See `docs/agent-task-bot-alignment.md` for the evidence-bound design around official `gh agent-task`, GitHub Copilot agent tasks, `gh skill`, GitHub Apps, webhooks, and self-hosted CLI agent runners.

Short version:

- Official `gh` does not expose `gh bot`.
- Official `gh` does expose preview `gh agent-task` with aliases `agent-task`, `agent-tasks`, `agent`, and `agents`.
- Official `gh agent-task` is currently a GitHub Copilot/CAPI workflow, not a generic self-hosted bot runtime.
- ChatGH should use the official naming as precedent, but its first bot bridge should normalize GitHub webhook events into local CLI agent tasks.

## Non-Goals

- Do not add placeholder commands only because official `gh` or GitHub Docs mention a domain.
- Do not make official `gh` a runtime dependency or fallback.
- Do not put token, webhook secret, or GitHub App private key material in examples, logs, or JSON fixtures.
- Do not implement GitHub Copilot/CAPI behavior unless the command explicitly says it is using GitHub-hosted agent tasks.
- Do not make repository, project, issue, PR, or run IDs ChatEnv fields; they are request parameters.

## Test And CI Contract

Each implemented domain should have these gates:

1. Unit tests for API path, method, payload, token resolution, and error handling.
2. Direct Python function tests for non-trivial command behavior.
3. CLI smoke tests for help, success, JSON output, and expected failures.
4. Safety tests for remote mutations and destructive operations.
5. `python -m pytest -q`, `python -m build`, `mkdocs build --strict`, and `git diff --check` before PR readiness.
