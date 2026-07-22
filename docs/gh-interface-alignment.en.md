# ChatGH Interface Alignment With Official `gh`

ChatGH is the GitHub operations foundation for ChatArch / Arch-series tooling. It should be easy for people and model callers familiar with GitHub CLI `gh` to use, while preserving ChatArch-specific authentication, safety gates, stable JSON output, and reusable Python APIs.

## Core Principles

1. **Use official `gh` as the first interface reference**: before adding a common GitHub capability, inspect the corresponding official `gh <group> <command> --help` and GitHub REST/API documentation.
2. **Do not depend on official `gh` at runtime**: official `gh` is only a reference for command shape, option names, help text, and user expectations. Real operations must be implemented through ChatGH's own Python API / REST path.
3. **If official `gh` has the capability, borrow the shape first**: prefer compatible command names, positional arguments, common aliases, and help wording where they do not conflict with ChatGH semantics.
4. **If official `gh` does not have the capability, design a ChatGH-native surface**: keep naming clear, JSON stable, behavior testable, and remote/local mutations explicit.
5. **Land CLI and Python API together**: CLI is the stable human/model-facing interface; importable Python functions are the reusable automation surface for ChatArch and other Arch tools.

## Code Organization

New capabilities should follow the existing layering:

```text
src/chatgh/
  cli.py                         # top-level command registration
  commands/pr.py                 # PR CLI command group
  github/cli.py                  # repo/run/repo-perms/set-token CLI groups
  github/commands.py             # Python command/service functions; CLI calls here
  github/requests.py             # GitHub API / payload functions
  github/api.py                  # token, repo resolution, low-level helpers
  github/render.py               # human-readable output helpers
```

Rules:

- The CLI layer should only parse parameters, resolve interactive prompts, and select output format.
- Workflow functions belong in `chatgh.github.commands` or an equivalent service module.
- GitHub API details belong in `chatgh.github.requests` / `api.py`.
- Human-readable output and JSON payloads stay separate: Python functions return payloads; CLI chooses table/summary, official-style `--json FIELDS` projection, or `--json-output` full payload output.
- Every new CLI should have a matching or near-matching Python API, such as `chatgh repo view` -> `view_repo(...)`.

## CLI Compatibility Strategy

- When official `gh` uses positional arguments, ChatGH should consider compatible positionals.
- When official short/long options do not conflict, provide aliases such as `-R/--repo`, `--org`, and `--fork-name`.
- Align official `--json FIELDS` while preserving ChatGH extensions: `--json-output`, `--token`, repo-local auth / ChatEnv token resolution, `--if-exists use`, and PR merge safety gates.
- Be conservative about local git side effects. `clone`, `remote`, and `sync` capabilities must have explicit parameters, clear output, and tests; they must not overwrite existing checkouts/remotes by default.

## `repo fork` Alignment Example

Official `gh repo fork` commonly uses a positional repository plus `--org` / `--fork-name`. ChatGH supports both the official-like shape and the explicit automation-friendly shape:

```bash
# gh-like, convenient for humans and model callers familiar with gh
chatgh repo fork Wei-Shaw/claude-relay-service --org ChatArch --fork-name claude-relay-service

# ChatGH explicit, convenient for automation and idempotent workflows
chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch --name claude-relay-service --if-exists use --json-output
```

Mapping:

- positional `REPO` -> `source`
- `--org` -> `owner` for organization targets
- `--fork-name` -> `name`
- `--json-output` and `--if-exists use` are ChatGH automation extensions

## Interface Scope

### Current Repository Commands

ChatGH currently provides these repository capabilities:

- `repo list [--owner OWNER] [--json FIELDS] [--json-output]`: list repositories for a user or organization.
- `repo create`: create a repository; private is the default and public requires explicit `--public`.
- `repo view [REPOSITORY] [-R/--repo REPOSITORY]`: read repository metadata.
- `repo clone REPOSITORY [DIRECTORY]`: safely clone a repository and refuse non-empty target directories.
- `repo sync [REPOSITORY]`: explicitly run `git fetch` and `git pull --ff-only`.
- `repo edit [REPOSITORY]`: edit the small description/homepage/default-branch/visibility subset; visibility changes require explicit acknowledgement.
- `repo fork [REPOSITORY] --org/--owner ... --fork-name/--name ...`: create a fork and support `--if-exists use` for idempotent reuse of matching forks.
- `repo transfer [REPOSITORY] --owner/--org ...`: transfer repository ownership; real transfers require explicit consequence acknowledgement.
- `repo protection`: inspect default branch protection, classic branch protection, and readable repository rulesets.

Planned repository capabilities:

- `repo pages` / `pages`: inspect and configure GitHub Pages source branch, path, and build mode. This should stay separate from docs workflow file edits.

### Current PR Commands

ChatGH currently provides these PR capabilities:

- `pr list`
- `pr create`
- `pr view`
- `pr comment`
- `pr edit`
- `pr checks`
- `pr merge`
- `pr status`
- `pr diff`
- `pr close`
- `pr reopen`
- `pr review`
- `pr ready`
- `pr update-branch`

`pr merge` must keep safety gates; merge commands are real remote mutations and must never be used as dry-runs.

### Current Actions Run Commands

ChatGH currently provides these Actions run capabilities:

- `run list`
- `run view`
- `run logs`
- `run watch`, with mandatory timeout
- `run rerun`
- `run cancel`
- `run download`

### Agent And Bot Alignment Direction

Official GitHub CLI does not currently have a `gh bot` command group, but the source contains preview `gh agent-task` with aliases `agent-task`, `agent-tasks`, `agent`, and `agents`. Its semantics are GitHub / Copilot hosted agent tasks: create an agent task in a repository, usually produce a PR and an agent session, and inspect sessions and logs through `list/view`. Official CLI also has preview `gh skill` / `gh skills` for installing and managing agent skills from GitHub repositories.

ChatGH's agent and bot direction must follow these rules:

- Prefer official `gh agent-task` / `gh skill` naming where it matches GitHub user expectations.
- Clearly distinguish GitHub-hosted Copilot/CAPI agent tasks from ChatGH's self-hosted event-to-runner bridge; one command must not silently mix both runtimes.
- Agent commands should center on GitHub webhook payload normalization, signature verification, thread comment/status write-back, and CLI runner invocation.
- Every agent command needs evidence, responsibility, safety boundaries, and CLI-to-Python API mapping in `docs/agent-task-bot-alignment.en.md`.

### Out Of Current Scope

These commands are not part of the current public surface unless they first receive dedicated safety design:

- `repo delete`
- `repo archive`
- `repo rename`
- `pr checkout`
- any command that overwrites local checkouts, remotes, or dirty worktrees by default
- agent commands that silently call GitHub Copilot/CAPI

## Current CLI To Python API Mapping

### Repository

| Command | Python API | Notes |
|---|---|---|
| `chatgh repo list` | `list_repos(owner, limit, sort, direction, token)` | Lists user or organization repositories; supports field projection and full JSON. |
| `chatgh repo create ...` | `create_repo(...)` | Creates a repository; public repositories require an explicit option. |
| `chatgh repo view [REPOSITORY] [-R/--repo REPOSITORY]` | `view_repo(repo, token)` | Reads the repository payload; supports JSON output. |
| `chatgh repo clone REPOSITORY [DIRECTORY]` | `clone_repo(repo, directory, ssh, token)` | Safe clone; refuses to overwrite a non-empty target directory and does not change workspace remotes by default. |
| `chatgh repo sync [REPOSITORY]` | `sync_repo(repo, branch, remote, ff_only, token)` | Explicit `git fetch` + `git pull --ff-only`; defaults to current checkout/current branch. |
| `chatgh repo edit [REPOSITORY]` | `edit_repo(repo, description, homepage, default_branch, visibility, accept_visibility_change_consequences, token)` | Small safe subset: description/homepage/default-branch/visibility; visibility changes require explicit consequence acknowledgement. |
| `chatgh repo fork ...` | `fork_repo(...)` | Supports gh-like positional repository, `--org`, `--fork-name`, and ChatGH `--if-exists use`. |
| `chatgh repo transfer ...` | `transfer_repo(repo, owner, team_ids, dry_run, accept_transfer_consequences, token)` | Uses GitHub Repository Transfer API; supports `--dry-run` and requires explicit consequence acknowledgement before remote mutation. |
| `chatgh repo protection ...` | `inspect_repo_protection(...)` / `list_repo_protections(...)` | Inspects branch protection and repository rulesets. |

### PR

| Command | Python API | Notes |
|---|---|---|
| `chatgh pr list` | `list_prs(repo, state, limit, token)` | Lists PRs. |
| `chatgh pr create ...` | `create_pr(...)` | Creates a PR; supports body/body-file and JSON output. |
| `chatgh pr view NUMBER` | `view_pr(repo, number, token)` | Shows PR metadata, branches, mergeability, and timestamps. |
| `chatgh pr comment NUMBER` | `comment_pr(repo, number, body, token)` | Posts a comment. |
| `chatgh pr edit NUMBER` | `edit_pr(repo, number, title, body, token)` | Edits title or body. |
| `chatgh pr checks NUMBER` | `check_pr(repo, number, token)` | Summarizes combined status, check runs, and workflow runs. |
| `chatgh pr merge NUMBER` | `merge_pr(repo, number, method, check, token)` | Can run safety checks before merge. |
| `chatgh pr status` | `status_prs(repo, token)` | Summarizes open PRs. |
| `chatgh pr diff NUMBER` | `diff_pr(repo, number, token)` | Emits GitHub diff text for review workflows. |
| `chatgh pr close NUMBER` | `close_pr(repo, number, comment, delete_branch, token)` | Closes a remote PR; `--delete-branch` records the request but does not delete branches by default. |
| `chatgh pr reopen NUMBER` | `reopen_pr(repo, number, token)` | Reopens a PR. |
| `chatgh pr review NUMBER` | `review_pr(repo, number, event, body, token)` | Supports `--approve`, `--request-changes`, `--comment`, and body/body-file. |
| `chatgh pr ready NUMBER` | `ready_pr(repo, number, token)` | Draft -> ready_for_review. |
| `chatgh pr update-branch NUMBER` | `update_pr_branch(repo, number, expected_head_sha, token)` | Calls GitHub's update-branch API. |

### Actions Run

| Command | Python API | Notes |
|---|---|---|
| `chatgh run list` | `list_runs(repo, branch, status, event, limit, token)` | Supports branch/status/event/limit and JSON output. |
| `chatgh run view RUN_ID` | `view_run(repo, run_id, token)` | Shows a workflow run and its jobs. |
| `chatgh run logs` | `run_logs(repo, job_id, tail, output, token)` | Shows job logs; supports tailing and writing to disk. |
| `chatgh run watch RUN_ID` | `watch_run(repo, run_id, interval, timeout, token)` | Requires timeout to avoid hanging agent runs. |
| `chatgh run rerun RUN_ID` | `rerun_run(repo, run_id, token)` | Remote mutation; outputs run id/status. |
| `chatgh run cancel RUN_ID` | `cancel_run(repo, run_id, token)` | Remote mutation; outputs run id/status. |
| `chatgh run download RUN_ID` | `download_run_artifacts(repo, run_id, name, output_dir, token)` | Downloads and extracts artifacts; output location is explicit through `--dir`/current directory. |

## Testing Requirements

Every new interface should cover at least:

1. Python API / request payload behavior.
2. CLI parameter mapping, aliases, error semantics, and `--json-output`.
3. Token non-disclosure.
4. Target object and safety boundaries for write operations.
5. For commands with local git side effects, tests proving they do not overwrite existing remotes or dirty checkouts.

Write failing tests first, implement the smallest code that passes, then update README/docs.

## GitHub Projects v2

`chatgh project` does not copy the official flat `gh project` tree. Official `gh project` is only a capability/semantic reference. ChatGH uses its own structure: `project list/view/create/edit/close/delete/copy` manages project lifecycle, `project item list/add/create/edit/archive/delete` manages items, `project field list/create/delete` manages field structure, and `link/unlink/mark-template` remain top-level for now. ChatGH intentionally does not keep flat item/field compatibility entries such as `item-add` or `field-list`. Runtime behavior still uses ChatGH auth, JSON output, safety gates, ChatStyle missing-input prompts, and importable Python APIs. `project` commands auto-prompt by default on interactive terminals, `CHATARCH_AUTO_PROMPT=0/false/no/off` disables default prompting for machine/CI callers, `-i` forces interaction, and `-I` disables interaction; destructive confirmations still require explicit `--confirm`. `project item edit` is the field-value editing entry and expands text/number/date/single-select/iteration/clear shapes.
