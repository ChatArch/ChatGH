# GitHub Agent Task And Bot Alignment

This document records what GitHub's official CLI and APIs currently expose around agents, tasks, skills, bots, GitHub Apps, and webhooks. It defines how ChatGH should grow an agent/bot surface without confusing GitHub-hosted Copilot agents with ChatGH's self-hosted CLI-agent bridge.

## Summary

- Official `gh` does not have a first-class `gh bot` command group.
- Official `gh` does have preview `gh agent-task` with aliases `agent-task`, `agent-tasks`, `agent`, and `agents`.
- Official `gh agent-task` is a GitHub Copilot agent task client. It starts and inspects GitHub-hosted coding-agent sessions, usually tied to a pull request.
- Official `gh skill` / `gh skills` is a preview command group for installing and managing agent skills from GitHub repositories.
- `gh api`, issue/PR comments, checks/statuses, workflow dispatch, GitHub Apps, and webhooks are the generic primitives for building custom bots.
- ChatGH should align naming with official `gh agent-task`, but implement self-hosted event-to-runner workflows separately from GitHub Copilot/CAPI.
- Agent identity, manifest fields, lifecycle, permissions, runtime, and output policy are defined in `docs/agent-definition.md`.

## Evidence Sources

Official GitHub CLI:

- Source: https://github.com/cli/cli
- Manual: https://cli.github.com/manual/
- GitHub CLI docs: https://docs.github.com/en/github-cli
- Relevant source path: `pkg/cmd/agent-task`
- Relevant source path: `pkg/cmd/skills`
- Relevant source path: `pkg/cmd/copilot`

GitHub API docs:

- Agent tasks REST docs: https://docs.github.com/en/rest/agent-tasks/agent-tasks
- GitHub Apps overview: https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps
- App installations API: https://docs.github.com/en/rest/apps/installations
- Webhooks: https://docs.github.com/en/webhooks/about-webhooks
- Repository webhooks: https://docs.github.com/en/rest/repos/webhooks
- Check runs: https://docs.github.com/en/rest/checks/runs
- Issue comments: https://docs.github.com/en/rest/issues/comments
- Workflow dispatch: https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

## What Official `gh agent-task` Does

The official CLI source defines:

```text
gh agent-task <command>
```

Aliases:

```text
gh agent-task
gh agent-tasks
gh agent
gh agents
```

Implemented preview subcommands:

```text
gh agent-task create [<task description>] [flags]
gh agent-task list [flags]
gh agent-task view [<session-id> | <pr-number> | <pr-url> | <pr-branch>] [flags]
```

The current implementation is a GitHub Copilot/CAPI client, not a general bot runner:

- `create` queues a GitHub-hosted agent job for a repository.
- The task input is a problem statement from an argument, `--from-file/-F`, stdin, or editor prompt.
- `--repo/-R` selects the target repository.
- `--base/-b` selects the PR base branch, defaulting to the repository default branch.
- `--custom-agent/-a` selects a custom agent defined in `.github/agents/<name>.md`.
- The returned job may produce a pull request and an agent session URL.
- `list` shows recent agent sessions for the viewer.
- `view` reads a session by session id, PR number, PR URL, or PR branch and can show logs.

Important implementation details observed in official source:

- Jobs are created through Copilot/CAPI, with a path shaped like `/agents/swe/v1/jobs`.
- Sessions are read through Copilot/CAPI paths shaped like `/agents/sessions`, `/agents/sessions/{id}`, `/agents/sessions/{id}/logs`, and `/agents/resource/{resource_type}/{resource_id}`.
- The CLI resolves the Copilot API endpoint through a GraphQL `viewer.copilotEndpoints.api` query.
- The command requires an OAuth/device-flow style token, not just any random PAT.
- Session display is PR-centric: session resources are hydrated through GitHub GraphQL pull request nodes, and URLs are displayed as `https://github.com/OWNER/REPO/pull/NUMBER/agent-sessions/SESSION_ID`.
- Logs contain chat-completion chunks and rendered tool calls, including shell and GitHub Actions/MCP-like tool calls.

Interpretation:

`gh agent-task` is GitHub's CLI surface for GitHub-hosted coding-agent work. It is closest to "assign a task to Copilot coding agent and track the resulting PR/session." It is not the same thing as "run my own local Codex/Hermes/OpenHands bot when someone comments on an issue."

## What Official `gh skill` Does

The official CLI source defines:

```text
gh skill <command>
```

Alias:

```text
gh skills
```

Relevant preview subcommands include:

```text
gh skill install <repository> [<skill[@version]>]
gh skill list
gh skill search <query>
gh skill preview <repository> <skill>
gh skill update
```

Observed behavior:

- Skills are discovered in GitHub repositories and local directories.
- The convention is based on `skills/*/SKILL.md` and the Agent Skills specification at https://agentskills.io/specification.
- The installer also knows hidden/local agent skill directories such as `.agents/skills` and selected agent host destinations.
- Installed skills include source tracking metadata so `gh skill update` can detect upstream changes.
- The CLI warns that skills are not verified by GitHub and may contain prompt injections, hidden instructions, or malicious scripts.

Interpretation:

GitHub is separating "agent tasks" from "agent skills":

- `agent-task` is a run/session/work item.
- `skill` is a reusable capability package installed into an agent host.

This is useful for ChatGH because it suggests a clean vocabulary:

- `agent-task`: a repo-bound unit of work.
- `skill`: a reusable agent capability from a repository.
- `custom-agent`: an agent profile/role file, such as `.github/agents/name.md`.

## Generic Bot Primitives In GitHub

Official `gh` exposes many primitives that can be composed into bots even without `gh bot`:

```bash
gh api METHOD PATH
gh issue comment
gh pr comment
gh pr review
gh workflow run
gh run watch
gh run view
gh run download
```

For ChatGH, the underlying GitHub APIs matter more than shelling out to official `gh`:

- Issue comments: `POST /repos/{owner}/{repo}/issues/{issue_number}/comments`
- PR reviews: `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews`
- Commit statuses: `POST /repos/{owner}/{repo}/statuses/{sha}`
- Check runs: `POST /repos/{owner}/{repo}/check-runs` with `checks:write`, typically a GitHub App permission.
- Workflow dispatch: `POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`
- Repository dispatch: `POST /repos/{owner}/{repo}/dispatches`
- Repository webhooks: `/repos/{owner}/{repo}/hooks`
- Organization webhooks: `/orgs/{org}/hooks`
- GitHub App installation tokens: `/app/installations/{installation_id}/access_tokens`

## Common Bot Operations With Official `gh`

Official `gh` can perform many bot actions, even though it does not provide a full bot runtime. Use this as an evidence-backed command vocabulary for ChatGH design, not as a required runtime dependency.

### Identity And Credential Setup

| Operation | Official `gh` support | Notes |
|---|---|---|
| Create a normal bot user | Not a CLI operation | Register the GitHub user in the browser, then add it to org/repo permissions. |
| Login as bot user | `gh auth login` | Suitable for local/manual setup; automation usually uses `GH_TOKEN` / `GITHUB_TOKEN`. |
| Show active token | `gh auth token` | Useful for debugging; do not print in logs. |
| Create fine-grained PAT | Not a CLI operation | Created through GitHub UI. |
| Create GitHub App | Not a normal CLI operation | Usually created through GitHub UI or app manifest flow. |
| Create installation token | `gh api` if you already have an app JWT | ChatGH should implement this directly if GitHub App support becomes first-class. |

### Webhook Operations

```bash
# Create a repository webhook.
gh api repos/OWNER/REPO/hooks \
  -X POST \
  -f name=web \
  -F active=true \
  -F events[]=issue_comment \
  -F events[]=commit_comment \
  -F events[]=pull_request \
  -F config[url]=https://example.com/github/webhook \
  -F config[content_type]=json \
  -F config[secret]="$WEBHOOK_SECRET"

# List repository webhooks.
gh api repos/OWNER/REPO/hooks

# Test a repository webhook.
gh api repos/OWNER/REPO/hooks/HOOK_ID/tests -X POST

# Delete a repository webhook.
gh api repos/OWNER/REPO/hooks/HOOK_ID -X DELETE
```

Organization webhooks use the same pattern under `orgs/ORG/hooks`. The bot runtime must still receive HTTP requests, verify `X-Hub-Signature-256`, and deduplicate delivery IDs; official `gh` does not do that part.

### Thread And Review Operations

```bash
# Create an issue for an agent task.
gh issue create --repo OWNER/REPO --title "Agent task" --body "Please investigate ..."

# Comment on an issue.
gh issue comment 123 --repo OWNER/REPO --body "Agent started."

# Comment on a PR.
gh pr comment 12 --repo OWNER/REPO --body "Agent review complete."

# Submit a PR review.
gh pr review 12 --repo OWNER/REPO --comment --body "Reviewed by agent."
```

### Work Artifact Operations

```bash
# Create a PR after a local bot branch has been pushed.
gh pr create \
  --repo OWNER/REPO \
  --base main \
  --head bot/fix-123 \
  --title "Fix issue 123" \
  --body "Generated by agent."

# Create a release.
gh release create v1.2.3 --repo OWNER/REPO --notes "Generated release notes."

# Trigger a workflow.
gh workflow run agent.yml --repo OWNER/REPO -f issue=123

# Trigger a repository dispatch event.
gh api repos/OWNER/REPO/dispatches \
  -X POST \
  -f event_type=chatgh-agent \
  -f client_payload='{"issue":123}'
```

### Status And Check Operations

```bash
# Create a commit status.
gh api repos/OWNER/REPO/statuses/SHA \
  -X POST \
  -f state=pending \
  -f context=chatgh-agent \
  -f description="Agent is running"

# Create a check run. This typically requires a GitHub App token with checks:write.
gh api repos/OWNER/REPO/check-runs \
  -X POST \
  -f name=chatgh-agent \
  -f head_sha=SHA \
  -f status=in_progress
```

### Hosted Agent And Skill Operations

```bash
# GitHub-hosted Copilot agent task, preview.
gh agent-task create "fix the failing tests" --repo OWNER/REPO --base main

gh agent-task list

gh agent-task view SESSION_ID

# Agent skills, preview.
gh skill search code-review
gh skill install OWNER/SKILL_REPO skill-name
gh skill list
```

Design implication for ChatGH:

- Use official `gh` command shapes as vocabulary.
- Implement the bot runtime pieces official `gh` does not own: event receiving, signature verification, command parsing, permission checks, task state, runner invocation, audit logs, retries, and provider-neutral normalization.
- Prefer direct Python/API implementation in ChatGH over shelling out to `gh`, so ChatGH keeps stable JSON, token resolution, safety gates, and tests.

## Existing GitHub Bot Pattern: Julia Registrator

Julia's package ecosystem is a good concrete precedent for repository-native bots.

Relevant projects:

- Registrator: https://github.com/JuliaRegistries/Registrator.jl
- General registry: https://github.com/JuliaRegistries/General
- TagBot: https://github.com/JuliaRegistries/TagBot
- RegistryCI / AutoMerge: https://github.com/JuliaRegistries/RegistryCI.jl

Registrator's user experience:

```text
@JuliaRegistrator register
@JuliaRegistrator register branch=name-of-your-branch
```

A package maintainer comments on a commit, issue, or PR. Registrator receives the GitHub event, checks the caller and repository state, reads the Julia `Project.toml`, and creates or updates a registration pull request against the Julia General registry. The registry PR is then checked and may be automatically merged by registry CI/AutoMerge. TagBot later creates Git tags, GitHub releases, and changelogs in the package repository after a version is registered.

Registrator's implementation model is a hybrid:

- A GitHub App is installed on package repositories.
- The app subscribes to issue comments and commit comments.
- The app uses a webhook URL and webhook secret to receive and verify GitHub events.
- The app's repository permissions are read-oriented: contents, issues, metadata, and commit statuses.
- A separate bot account/PAT can be used for posting comments, creating registry PRs, and working with private registries.
- The bot validates whether the commenter is allowed to register, for example collaborator or organization membership checks.
- The bot parses a small command language from the comment body.
- The bot posts status/comments back to the source thread and opens a PR in a target registry repository.

Interfaces visible from the source/docs:

- Webhook events: issue comments and commit comments.
- GitHub App auth: app id + private key -> JWT -> installation access token.
- Bot-user auth: configured GitHub username + PAT for actions that should happen as the bot user.
- Source repo reads: branch/commit lookup, file contents, tags, project metadata.
- Write-back: issue/commit comments and commit statuses.
- Target repo mutation: create or update pull requests in the registry repository.

TagBot uses a different but complementary pattern:

- It is a GitHub Action installed in each package repository as `.github/workflows/TagBot.yml`.
- The canonical workflow listens to `issue_comment` and `workflow_dispatch`.
- It only runs automatically when the actor is `JuliaTagBot` or when manually dispatched.
- It uses `GITHUB_TOKEN`, an optional PAT, or an SSH deploy key to create tags and GitHub releases.

Implication for ChatGH:

- A useful bot does not need a new chat UI. A comment command inside GitHub can be enough.
- The durable unit is a repository thread plus a generated PR/status/release artifact.
- GitHub App webhooks are best for event delivery and scoped reads.
- Bot-user tokens or installation tokens are still needed for write actions, depending on the desired identity and permissions.
- The ChatGH self-hosted agent bridge can follow this same shape: install/listen -> parse command -> check permissions -> run agent -> write comment/status/PR.

## Bot Integration Modes

### Mode 1: Bot User + Fine-Grained PAT

Fastest prototype:

1. Create a normal GitHub user, such as `chatgh-bot`.
2. Add that user to a repo or organization with limited permissions.
3. Configure a fine-grained PAT through ChatGH token resolution.
4. Let ChatGH read events and post comments/PRs/statuses as that user.

Pros:

- Fits current ChatGH token resolution.
- Easy to test with existing `pr comment`, `pr create`, `repo-perms`, and `run` commands.
- The identity is visible in issue and PR threads.

Cons:

- Coarser permission and audit model than GitHub Apps.
- Token rotation and least privilege are weaker.
- Harder to install across many repos as an app.

### Mode 2: GitHub App

Best long-term organization/community model:

1. Register a GitHub App.
2. Install it on selected repos/orgs.
3. Subscribe to webhook events.
4. Exchange app JWT + installation id for short-lived installation access tokens.
5. Act as `<app-slug>[bot]` with app-scoped permissions.

Pros:

- First-class bot identity.
- Installation-scoped permissions.
- Native webhook delivery and audit model.
- Suitable for organization-level rollout.

Cons:

- Requires JWT/private-key support.
- Requires setup UX and secret management.
- Requires new ChatGH credential mode beyond PAT.

### Mode 3: Webhook Event Bridge

Best first ChatGH-native bot loop:

1. Receive GitHub webhook events in a small gateway service.
2. Verify the webhook signature.
3. Call `chatgh agent event normalize ...` to produce a provider-neutral task payload.
4. Invoke a local CLI agent runner, such as Codex, Hermes, OpenHands, or Claude Code.
5. Use ChatGH to post progress and final comments back to the original thread.

This mode is closest to the user's product idea: a repository/community thread becomes an agent task surface.

### Mode 4: GitHub Actions Runner

For safer repo-bound automation:

- A comment or label triggers an Actions workflow.
- The workflow invokes a CLI agent in a controlled runner.
- ChatGH reports artifacts, logs, PR links, and statuses.

This mode can use GitHub's native logs/secrets/permissions, but it may be slower and less interactive than a webhook gateway.

## Proposed ChatGH Command Direction

ChatGH should reserve official-compatible naming while clearly separating GitHub-hosted agent tasks from self-hosted agent tasks.

### Phase 0: Documentation And API Evidence

No public placeholder commands.

- Document official `gh agent-task`, `gh skill`, GitHub Apps, webhooks, and REST evidence.
- Keep `docs/interface-tree.md` and this document as the source of command direction.

### Phase 1: Self-Hosted Event Normalization

Suggested command surface:

```bash
chatgh agent event verify \
  --provider github \
  --payload-file payload.json \
  --signature "$X_HUB_SIGNATURE_256" \
  --secret-env CHATGH_WEBHOOK_SECRET

chatgh agent event normalize \
  --provider github \
  --event issue_comment \
  --payload-file payload.json \
  --json-output

chatgh agent event handle \
  --provider github \
  --event issue_comment \
  --payload-file payload.json \
  --runner-command 'codex --json' \
  --json-output
```

Aliases may include `agent-task` and `bot`, but the canonical self-hosted namespace should be chosen deliberately before implementation.

### Phase 2: Task Comments And Statuses

Suggested command surface:

```bash
chatgh agent task comment \
  --provider github \
  --repo OWNER/REPO \
  --issue 123 \
  --body-file result.md

chatgh agent status create \
  --repo OWNER/REPO \
  --sha SHA \
  --state pending \
  --description "Agent running"
```

### Phase 3: Webhook Management

Suggested command surface:

```bash
chatgh agent webhook list --repo OWNER/REPO
chatgh agent webhook create --repo OWNER/REPO --url https://example.com/webhook --events issue_comment,pull_request,workflow_run
chatgh agent webhook test --repo OWNER/REPO --id 123
chatgh agent webhook delete --repo OWNER/REPO --id 123 --confirm
```

### Phase 4: GitHub App Auth

Suggested command surface:

```bash
chatgh app installations list --app-id APP_ID --private-key-file key.pem
chatgh app token --installation-id ID --app-id APP_ID --private-key-file key.pem --json-output
```

Keep `app` separate from `agent` because GitHub App auth is GitHub-specific and should not leak into provider-neutral task handling.

### Phase 5: GitHub-Hosted Agent Task Interop

Only implement if we explicitly want to call GitHub Copilot/CAPI or GitHub Agent Tasks REST endpoints.

Possible shape:

```bash
chatgh agent-task create "fix the failing tests" --repo OWNER/REPO --base main --custom-agent my-agent
chatgh agent-task list --limit 20 --json-output
chatgh agent-task view SESSION_ID --repo OWNER/REPO --json-output
```

Rules:

- If a command calls GitHub-hosted Copilot/CAPI, say so in help text.
- If a command invokes a local runner, call it self-hosted/local in help text.
- Do not silently mix both models under the same behavior.

## Normalized Event Schema

Future event handling should normalize GitHub webhook payloads into a stable schema before calling any runner.

```json
{
  "provider": "github",
  "host": "https://github.com",
  "event_type": "issue_comment",
  "action": "created",
  "delivery_id": "...",
  "repo": "owner/repo",
  "thread": {
    "kind": "issue_or_pr",
    "number": 123,
    "comment_id": 456,
    "url": "..."
  },
  "actor": {
    "login": "alice",
    "association": "MEMBER"
  },
  "command": {
    "raw": "@chatgh-bot fix this",
    "agent": "default",
    "args": "fix this"
  },
  "context": {
    "title": "Bug report",
    "body": "...",
    "labels": ["bug"],
    "base_branch": "main",
    "head_sha": "..."
  }
}
```

## Safety Contract

Agent/bot commands must be stricter than normal read-only CLI commands:

- Only respond to explicit mention or slash command by default.
- Ignore bot-authored comments unless explicitly allowed.
- Verify webhook signatures before handling payloads.
- Deduplicate webhook delivery IDs.
- Require repo/org allowlists for webhook handlers.
- Start with read-only or comment-only behavior for public/community repos.
- Require human approval before push, merge, delete, visibility changes, or secret changes.
- Post visible progress for long-running work.
- Keep actor, repo, command, token source, runner, and final action in an audit log.
- Never print tokens, webhook secrets, GitHub App private keys, or raw Authorization headers.

## ChatTea / Gitea Carry-Over

Gitea does not have GitHub's exact hosted Copilot agent-task model. For Gitea/ChatTea, the closest equivalent is:

- Bot user + access token.
- Repository/organization/system webhooks.
- Issue/PR comments as task threads.
- Commit statuses and Actions runner APIs for progress and CI.

Therefore:

- ChatGH should stay GitHub-first for official `gh` alignment.
- ChatTea should own Gitea-native routes and local Gitea lifecycle.
- A future provider-neutral layer may share event schemas and runner contracts across GitHub and Gitea.
