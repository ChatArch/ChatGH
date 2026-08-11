# ChatGH Interface Tree

ChatGH follows a GitHub-familiar resource model for GitHub APIs, while keeping ChatGH-specific credential, JSON, safety, and Python API contracts. The current package is GitHub-only; Gitea/Forgejo exploration belongs in ChatTea or a future provider-neutral layer unless a ChatGH command has an explicit GitHub-compatible purpose.

## Current CLI Surface

Since `0.2.10`, this tree is generated live by `chatgh --tree` from the registered Click command surface; the docs keep a human-readable copy for review.

```text
chatgh  # GitHub helpers (PR, actions, repo).
├── --help  # Show this help message.
├── --version  # Show the installed package version.
├── --tree  # Print the registered command tree.
├── pr  # Pull request helpers.
│   ├── list [--repo <REPO>] [--state <STATE>] [--limit <LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # List pull requests.
│   ├── create [--repo <REPO>] [--base <BASE>] [--head <HEAD>] [--title <TITLE>] [--body <BODY>] [--body-file <BODY-FILE>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Create a pull request.
│   ├── view [NUMBER] [--repo <REPO>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Show pull request details.
│   ├── comment [NUMBER] [--repo <REPO>] [--body <BODY>] [--body-file <BODY-FILE>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Comment on a pull request.
│   ├── edit [NUMBER] [--repo <REPO>] [--title <TITLE>] [--body <BODY>] [--body-file <BODY-FILE>] [--state <STATE>] [--base <BASE>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Edit a pull request.
│   ├── checks [NUMBER] [--repo <REPO>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Show CI check status for a pull request.
│   ├── status [--repo <REPO>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Show current repository pull request status.
│   ├── diff [NUMBER] [--repo <REPO>] [--token <TOKEN>] [--interactive/--no-interactive]  # Show a pull request diff.
│   ├── close [NUMBER] [--repo <REPO>] [--comment <COMMENT>] [--delete-branch] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Close a pull request.
│   ├── reopen [NUMBER] [--repo <REPO>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Reopen a pull request.
│   ├── review [NUMBER] [--repo <REPO>] [--approve] [--request-changes] [--comment] [--body <BODY>] [--body-file <BODY-FILE>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Review a pull request.
│   ├── ready [NUMBER] [--repo <REPO>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Mark a draft pull request ready for review.
│   ├── update-branch [NUMBER] [--repo <REPO>] [--expected-head-sha <EXPECTED-HEAD-SHA>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Update a pull request branch from its base branch.
│   └── merge [NUMBER] [--repo <REPO>] [--method <METHOD>] [--title <TITLE>] [--message <MESSAGE>] [--message-file <MESSAGE-FILE>] [--check/--no-check] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Merge a pull request.
├── repo  # Repository helpers.
│   ├── list [--owner <OWNER>] [--limit <LIMIT>] [--sort <SORT>] [--direction <DIRECTION>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # List repositories for an owner or organization.
│   ├── view [REPO-ARG] [--repo <REPO-OPTION>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # View repository details.
│   ├── clone <REPO> [DIRECTORY] [--ssh] [--set-token/--no-set-token] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Clone a repository without overwriting an existing directory.
│   ├── sync [REPO-ARG] [--repo <REPO-OPTION>] [--branch <BRANCH>] [--remote <REMOTE>] [--ff-only/--no-ff-only] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Fetch and fast-forward the current checkout for a repository.
│   ├── edit [REPO-ARG] [--repo <REPO-OPTION>] [--description <DESCRIPTION>] [--homepage <HOMEPAGE>] [--default-branch <DEFAULT-BRANCH>] [--visibility <VISIBILITY>] [--accept-visibility-change-consequences] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Edit repository metadata.
│   ├── protection [--repo <REPO>] [--owner <OWNER>] [--limit <LIMIT>] [--jobs <JOBS>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Show default-branch protection and ruleset status.
│   ├── create [--owner <OWNER>] [--name <NAME>] [--description <DESCRIPTION>] [--public] [--if-exists <IF-EXISTS>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Create a repository. Repositories are private by default.
│   ├── fork [SOURCE-ARG] [--source <SOURCE>] [--owner <OWNER>] [--org <ORG>] [--name <NAME>] [--fork-name <FORK-NAME>] [--default-branch-only] [--if-exists <IF-EXISTS>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Fork a repository into a target owner or organization.
│   └── transfer [REPO-ARG] [--repo <REPO-OPTION>] [--owner <OWNER>] [--org <ORG>] [--team-id <TEAM-IDS>] [--dry-run] [--accept-transfer-consequences] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Transfer a repository to another GitHub owner or organization.
├── project  # GitHub Projects helpers.
│   ├── item  # Manage project items.
│   │   ├── list [NUMBER] [--owner <OWNER>] [--limit <LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # List project items.
│   │   ├── add [NUMBER] [--owner <OWNER>] [--url <URL>] [--content-id <CONTENT-ID>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Add an issue or pull request item to a project.
│   │   ├── create [NUMBER] [--owner <OWNER>] [--title <TITLE>] [--body <BODY>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Create a draft issue item.
│   │   ├── edit [NUMBER] [--owner <OWNER>] [--id <ITEM-ID>] [--field-id <FIELD-ID>] [--field-name <FIELD-NAME>] [--text <TEXT>] [--number <NUMBER-VALUE>] [--date <DATE>] [--single-select-option-id <SINGLE-SELECT-OPTION-ID>] [--iteration-id <ITERATION-ID>] [--clear] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Edit a project item field value.
│   │   ├── archive [NUMBER] [--owner <OWNER>] [--id <ITEM-ID>] [--undo] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Archive or unarchive a project item.
│   │   └── delete [NUMBER] [--owner <OWNER>] [--id <ITEM-ID>] [--confirm <CONFIRM>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Delete a project item.
│   ├── field  # Manage project fields.
│   │   ├── list [NUMBER] [--owner <OWNER>] [--limit <LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # List project fields.
│   │   ├── create [NUMBER] [--owner <OWNER>] [--name <NAME>] [--data-type <DATA-TYPE>] [--single-select-option <OPTIONS>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Create a project field.
│   │   └── delete [NUMBER] [--owner <OWNER>] [--field-id <FIELD-ID>] [--confirm <CONFIRM>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Delete a project field.
│   ├── list [--owner <OWNER>] [--limit <LIMIT>] [--closed] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # List projects for an owner.
│   ├── view [NUMBER] [--owner <OWNER>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # View a project.
│   ├── create [--owner <OWNER>] [--title <TITLE>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Create a project.
│   ├── edit [NUMBER] [--owner <OWNER>] [--title <TITLE>] [--description <DESCRIPTION>] [--readme <README>] [--visibility <VISIBILITY>] [--accept-visibility-change-consequences] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Edit a project.
│   ├── close [NUMBER] [--owner <OWNER>] [--undo] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Close or reopen a project.
│   ├── delete [NUMBER] [--owner <OWNER>] [--confirm <CONFIRM>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Delete a project.
│   ├── copy [NUMBER] [--owner <OWNER>] [--target-owner <TARGET-OWNER>] [--title <TITLE>] [--drafts/--no-drafts] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Copy a project.
│   ├── link [NUMBER] [--owner <OWNER>] [--repo-id <REPO-ID>] [--team-id <TEAM-ID>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Link a repository or team to a project.
│   ├── unlink [NUMBER] [--owner <OWNER>] [--repo-id <REPO-ID>] [--team-id <TEAM-ID>] [--confirm <CONFIRM>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Unlink a repository or team from a project.
│   └── mark-template [NUMBER] [--owner <OWNER>] [--undo] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Mark or unmark a project as a template.
├── run  # GitHub Actions helpers.
│   ├── list [--repo <REPO>] [--branch <BRANCH>] [--status <STATUS>] [--event <EVENT>] [--limit <LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # List workflow runs.
│   ├── watch [RUN-ID-ARG] [--repo <REPO>] [--run-id <RUN-ID>] [--interval <INTERVAL>] [--timeout <TIMEOUT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Watch a workflow run until it completes.
│   ├── rerun [RUN-ID-ARG] [--repo <REPO>] [--run-id <RUN-ID>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Rerun a workflow run.
│   ├── cancel [RUN-ID-ARG] [--repo <REPO>] [--run-id <RUN-ID>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Cancel a workflow run.
│   ├── download [RUN-ID-ARG] [--repo <REPO>] [--run-id <RUN-ID>] [--name <NAME>] [--dir <OUTPUT-DIR>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Download workflow run artifacts.
│   ├── view [--repo <REPO>] [--run-id <RUN-ID>] [--job-limit <JOB-LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Show a workflow run and its jobs.
│   └── logs [--repo <REPO>] [--job-id <JOB-ID>] [--tail <TAIL>] [--output <OUTPUT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>] [--interactive/--no-interactive]  # Show logs for a workflow job.
├── invitation  # Repository invitation helpers.
│   ├── list [--limit <LIMIT>] [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # List repository invitations for the authenticated user.
│   ├── accept <INVITATION-ID> [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Accept a repository invitation by id.
│   └── decline <INVITATION-ID> [--json <FIELDS>] [--json-output] [--token <TOKEN>]  # Decline a repository invitation by id.
├── repo-perms [--repo <REPO>] [--json <FIELDS>] [--json-output] [--full-json] [--token <TOKEN>]  # Show repository permissions for the current token.
└── set-token [--token <TOKEN>] [--save-env]  # Configure HTTPS credentials for the current GitHub repository.
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
- `pages`
- `agent-task` / `agent` / `agents`
- `skill` / `skills`

ChatGH-specific custom commands stay:

- `set-token`: configure repo-local HTTPS auth header and optionally ChatEnv `GITHUB_ACCESS_TOKEN`.
- `repo-perms`: inspect token permissions and derived ChatGH capabilities.
- `agent event ...`: future local event-to-runner bridge, if implemented; this should not pretend to be GitHub Copilot's hosted agent runtime.

## Responsibilities

- `set-token`: store a GitHub token for the current repository in repo-local git config, optionally saving it to ChatEnv.
- `repo-perms`: resolve the current token, read repository permissions, and derive ChatGH capabilities.
- `repo list/view/create/edit/fork/transfer/clone/sync/protection`: cover repository inventory, mutation, ownership transfer, local checkout, fork creation, and governance inspection.
- `pr list/create/view/comment/edit/checks/merge/status/diff/close/reopen/review/ready/update-branch`: cover PR lifecycle, review, merge gating, and CI inspection.
- `project ...`: cover GitHub Projects v2 through ChatGH's Project/item/field command tree, not the official `gh project` flat aliases.
- `run list/view/logs/watch/rerun/cancel/download`: cover GitHub Actions workflow run operations and job logs.
- `invitation list/accept/decline`: cover authenticated user repository invitations.
- Future `repo pages` / `pages`: inspect and configure GitHub Pages source (`branch`/`path`) and build mode. Current docs deploys only rely on repository workflow files plus the repository's existing Pages setting.
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
chatgh repo transfer          -> chatgh.github.commands.transfer_repo
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

See `docs/agent-definition.en.md` for the ChatGH robot/Agent product definition, manifest shape, lifecycle, GitHub-native flow, permissions, runtime, and bilingual configuration examples. See `docs/agent-task-bot-alignment.en.md` for the evidence-bound design around official `gh agent-task`, GitHub Copilot agent tasks, `gh skill`, GitHub Apps, webhooks, and self-hosted CLI agent runners.

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
