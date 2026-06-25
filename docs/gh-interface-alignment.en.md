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
- Human-readable output and JSON payloads stay separate: Python functions return payloads; CLI chooses table/summary or `--json-output`.
- Every new CLI should have a matching or near-matching Python API, such as `chatgh repo view` -> `view_repo(...)`.

## CLI Compatibility Strategy

- When official `gh` uses positional arguments, ChatGH should consider compatible positionals.
- When official short/long options do not conflict, provide aliases such as `-R/--repo`, `--org`, and `--fork-name`.
- Preserve ChatGH extensions: `--json-output`, `--token`, repo-local auth / ChatEnv token resolution, `--if-exists use`, and PR merge safety gates.
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

## Batch Migration Priorities

### Phase 1: repository commands

- `repo view [REPO] [-R/--repo REPO] [--json-output]`
- `repo fork [REPO] --org/--owner ... --fork-name/--name ...`
- `repo clone REPO [DIR]`, without destructive checkout/remote behavior by default
- `repo sync [REPO]`, after clarifying API/git boundaries
- Small `repo edit` subset: description/homepage/default-branch/visibility

### Phase 2: PR lifecycle

Currently available: `create/list/view/comment/edit/checks/merge`. Next priorities:

- `pr status`
- `pr diff`
- `pr close`
- `pr reopen`
- `pr review`
- `pr ready`
- `pr update-branch`

`pr merge` must keep safety gates; merge commands are real remote mutations and must never be used as dry-runs.

### Phase 3: Actions runs

Currently available: `run view` / `run logs`. Next priorities:

- `run list`
- `run watch`, with mandatory timeout
- `run rerun`
- `run cancel`
- `run download`


## Implemented Scope In This PR (2026-06-25)

Following this design, the current `repo fork` PR now also lands the remaining common interfaces with the same CLI + Python API layering:

### Repo

| Command | Python API | Status | Notes |
|---|---|---|---|
| `chatgh repo view [REPOSITORY] [-R/--repo REPOSITORY]` | `view_repo(repo, token)` | Implemented | Reads the repository payload; supports JSON output. |
| `chatgh repo clone REPOSITORY [DIRECTORY]` | `clone_repo(repo, directory, ssh, token)` | Implemented | Safe clone; refuses to overwrite a non-empty target directory and does not change workspace remotes by default. |
| `chatgh repo sync [REPOSITORY]` | `sync_repo(repo, branch, remote, ff_only, token)` | Implemented | Explicit `git fetch` + `git pull --ff-only`; defaults to current checkout/current branch. |
| `chatgh repo edit [REPOSITORY]` | `edit_repo(repo, description, homepage, default_branch, visibility, accept_visibility_change_consequences, token)` | Implemented | Small safe subset: description/homepage/default-branch/visibility; visibility changes require explicit consequence acknowledgement. |
| `chatgh repo fork ...` | `fork_repo(...)` | Implemented | Supports gh-like positional repository, `--org`, `--fork-name`, and ChatGH `--if-exists use`. |

### PR

| Command | Python API | Status | Notes |
|---|---|---|---|
| `chatgh pr status` | `status_prs(repo, token)` | Implemented | Current implementation summarizes open PRs; authored/review-requested can be expanded later. |
| `chatgh pr diff NUMBER` | `diff_pr(repo, number, token)` | Implemented | Emits GitHub diff text for review workflows. |
| `chatgh pr close NUMBER` | `close_pr(repo, number, comment, delete_branch, token)` | Implemented | Closes a remote PR; `--delete-branch` currently records the request but does not delete branches by default. |
| `chatgh pr reopen NUMBER` | `reopen_pr(repo, number, token)` | Implemented | Reopens a PR. |
| `chatgh pr review NUMBER` | `review_pr(repo, number, event, body, token)` | Implemented | Supports `--approve`, `--request-changes`, `--comment`, and body/body-file. |
| `chatgh pr ready NUMBER` | `ready_pr(repo, number, token)` | Implemented | Draft -> ready_for_review. |
| `chatgh pr update-branch NUMBER` | `update_pr_branch(repo, number, expected_head_sha, token)` | Implemented | Calls GitHub's update-branch API. |

### Actions run

| Command | Python API | Status | Notes |
|---|---|---|---|
| `chatgh run list` | `list_runs(repo, branch, status, event, limit, token)` | Implemented | Supports branch/status/event/limit and JSON output. |
| `chatgh run watch RUN_ID` | `watch_run(repo, run_id, interval, timeout, token)` | Implemented | Requires timeout to avoid hanging agent runs. |
| `chatgh run rerun RUN_ID` | `rerun_run(repo, run_id, token)` | Implemented | Remote mutation; outputs run id/status. |
| `chatgh run cancel RUN_ID` | `cancel_run(repo, run_id, token)` | Implemented | Remote mutation; outputs run id/status. |
| `chatgh run download RUN_ID` | `download_run_artifacts(repo, run_id, name, output_dir, token)` | Implemented | Downloads and extracts artifacts; output location is explicit through `--dir`/current directory. |

This PR still excludes high-risk commands such as `repo delete/archive/rename` and `pr checkout`; those need separate safety gates and user confirmation before implementation.

## Testing Requirements

Every new interface should cover at least:

1. Python API / request payload behavior.
2. CLI parameter mapping, aliases, error semantics, and `--json-output`.
3. Token non-disclosure.
4. Target object and safety boundaries for write operations.
5. For commands with local git side effects, tests proving they do not overwrite existing remotes or dirty checkouts.

Write failing tests first, implement the smallest code that passes, then update README/docs.
