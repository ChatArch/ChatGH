# ChatGH Agent Definition

This document defines what an agent/robot means in ChatGH. It gives future `chatgh agent ...` and `chatgh agent-task ...` work a stable vocabulary instead of mixing GitHub Apps, bot users, GitHub Actions, Copilot agent tasks, and local CLI runners into one overloaded "bot" concept.

## One-Line Definition

A ChatGH agent is an auditable work member installed into a GitHub organization, repository, or thread. It has identity, triggers, context scope, permissions, tools, runtime, output rules, and approval policy. It turns GitHub issues, pull requests, comments, webhooks, or workflows into executable tasks and writes progress and artifacts back to GitHub.

```text
agent = identity + triggers + context + permissions + tools + runtime + task state + output/audit
```

## Core Terms

| Term | ChatGH meaning | Examples |
|---|---|---|
| Agent / robot | An installable, triggerable, authorized, auditable work member | `@chatgh-reviewer`, `release-manager` |
| Bot identity | The identity GitHub shows for actions | GitHub App `chatgh[bot]`, normal bot user |
| Agent task | A unit of assigned work | "fix failing tests in issue #123" |
| Run / session | One execution attempt | runner logs, tool calls, status |
| Trigger | Event or command that starts work | `@chatgh-agent fix this`, `workflow_dispatch` |
| Skill | Reusable capability package | code review skill, release notes skill |
| Tool | Callable external capability | GitHub API, shell, browser, MCP server |
| Policy | Permission and safety rules | read-only, can comment, can open PR, approval before merge |
| Artifact | Delivered output | PR, comment, release, patch, summary, log |

## Why Not Just "Bot"

In the GitHub ecosystem, "bot" can mean several different layers:

1. A normal bot user with a PAT.
2. A GitHub App with webhook events, scoped permissions, and an `xxx[bot]` identity.
3. A GitHub Actions bot using `github-actions[bot]`.
4. A GitHub-hosted Copilot agent task behind official `gh agent-task`.
5. A self-hosted CLI agent such as Codex, Hermes, OpenHands, or Claude Code.

ChatGH docs should use precise names:

- "GitHub App" for installation, webhooks, and installation tokens.
- "bot user" for a normal GitHub user plus PAT.
- "agent task" for work items.
- "runner" for the execution process or service.
- "agent" for the user-facing robot work member.

## Minimal Agent Manifest

A future ChatGH self-hosted agent could use `.chatgh/agents/<name>.yaml`. This is intentionally separate from official `.github/agents/<name>.md`, which belongs to GitHub-hosted Copilot custom agents.

```yaml
apiVersion: chatgh.chatarch.org/v1alpha1
kind: Agent
metadata:
  name: reviewer
  displayName: Code Reviewer
  description: Reviews pull requests and posts actionable comments.
  labels:
    role: reviewer
    domain: code
spec:
  identity:
    mode: github-app
    appSlug: chatgh-reviewer
    fallbackBotUser: chatgh-bot
  scope:
    organizations:
      - ChatArch
    repositories:
      - ChatArch/ChatGH
    threads:
      - issues
      - pull_requests
  triggers:
    mentions:
      - "@chatgh-reviewer"
    slashCommands:
      - "/review"
    webhookEvents:
      - issue_comment
      - pull_request
  commandParsing:
    defaultAction: review
    allowFreeform: true
  context:
    include:
      - thread
      - pull_request_diff
      - check_runs
      - repository_files
    maxFiles: 50
    maxThreadComments: 100
  permissions:
    github:
      contents: read
      issues: write
      pull_requests: write
      checks: read
      statuses: write
    local:
      filesystem: sandbox
      network: restricted
  tools:
    allow:
      - chatgh.pr.view
      - chatgh.pr.diff
      - chatgh.pr.comment
      - chatgh.pr.checks
      - shell.pytest
    deny:
      - chatgh.pr.merge
      - chatgh.repo.edit
  runtime:
    type: command
    command: "codex --json"
    timeoutSeconds: 1800
    workingDirectory: checkout
  memory:
    scope: repository
    retentionDays: 30
  output:
    progress: issue-comment
    final: issue-comment
    artifacts:
      - summary
      - patch
      - pull_request
  approvals:
    requiredFor:
      - push
      - merge
      - release
      - repository_settings
  audit:
    logLevel: standard
    includeToolCalls: true
```

## Field Groups

- `metadata`: stable user-visible identity: name, display name, description, and labels.
- `identity`: how the agent acts on GitHub: `github-app`, `bot-user`, `actions`, or `hosted-copilot`.
- `scope`: where the agent can see and respond: organization, repository, thread, branch, or path.
- `triggers`: how work starts: mention, slash command, label, webhook, dispatch, schedule.
- `context`: what ChatGH loads before a run: thread, PR diff, checks, logs, files, project items, linked issues.
- `permissions`: platform permissions plus ChatGH policy. A token may be able to merge, but policy can still deny merge.
- `tools`: allowlisted callable capabilities such as `chatgh.pr.diff`, `chatgh.pr.comment`, or `shell.pytest`.
- `runtime`: execution backend: local command, container, GitHub Actions, GitHub-hosted Copilot, or external webhook service.
- `memory`: scoped retention: thread, repository, organization, or none.
- `approvals`: high-risk actions requiring a human gate.
- `audit`: what run data must be recorded.

## Lifecycle

```text
draft
  -> installed
  -> enabled
  -> triggered
  -> authorized
  -> queued
  -> running
  -> waiting_approval
  -> completed | failed | cancelled
  -> archived
```

## GitHub-Native Flow

### 1. Install

```text
Admin installs GitHub App on org/repo
  -> GitHub sends installation event
  -> ChatGH stores installation id and allowed repos
  -> Admin selects an agent manifest or template
```

A bot user + PAT can work for a prototype, but GitHub Apps are the better organization model.

### 2. Trigger

```text
User comments: @chatgh-reviewer review this PR
  -> GitHub sends issue_comment webhook
  -> ChatGH verifies signature
  -> ChatGH normalizes event
  -> ChatGH parses command and selects agent
```

### 3. Authorize

```text
Check actor permission
Check repo allowlist
Check thread type
Check command allowlist
Check tool policy
Create audit record
```

### 4. Execute

```text
Build task context
Resolve installation token or bot token
Prepare checkout/sandbox
Invoke runner
Stream progress as comments/status/checks
```

### 5. Deliver

```text
Post final comment
Create/update PR if needed
Set commit status or check run
Attach artifacts/logs
Record final audit event
```

## Three Common Agent Types

### Code Review Agent

Reads PR diff and CI, then posts actionable review comments.

Typical permissions:

```text
contents: read
pull_requests: write
checks: read
statuses: write
```

Default denies: push, merge, release, repository settings.

### Issue Fix Agent

Creates a branch, edits code, runs tests, and opens a PR.

Typical permissions:

```text
contents: write
issues: write
pull_requests: write
statuses: write
```

High-risk actions: push, workflow edits, external service calls.

### Registry / Release Agent

Follows the Julia Registrator / TagBot pattern.

```text
@agent register
  -> read package metadata
  -> open registry PR
  -> post status/comment
  -> after merge create tag/release
```

This proves that GitHub issue or commit comments can be task entry points without a new UI.

## Relationship With Official GitHub Agents

Official `gh agent-task` is a GitHub-hosted Copilot agent task client:

```bash
gh agent-task create "fix the failing tests" --repo OWNER/REPO --base main
gh agent-task list
gh agent-task view SESSION_ID
```

ChatGH self-hosted agents are different:

- GitHub-hosted: `gh agent-task` / Copilot / CAPI.
- ChatGH self-hosted: webhook event -> local/remote runner -> GitHub write-back.

ChatGH should align naming and user expectations, but help text and docs must clearly separate these runtime models.

## Recommended ChatGH Command Direction

Start with composable primitives, not a full server:

```bash
chatgh agent event verify
chatgh agent event normalize
chatgh agent event handle
chatgh agent task comment
chatgh agent status create
chatgh agent webhook create
chatgh app token
```

Then add lifecycle commands:

```bash
chatgh agent install
chatgh agent list
chatgh agent enable
chatgh agent disable
chatgh agent run view
chatgh agent run logs
chatgh agent approve
```

## Minimal MVP

```text
GitHub issue_comment webhook
  -> chatgh agent event normalize
  -> permission check
  -> local runner command
  -> issue comment final response
```

Required first pieces:

- webhook signature verification.
- event normalization.
- mention/slash command parser.
- comment write-back.
- local runner contract.
- audit log.

Not required in the first version:

- full GitHub App UI.
- marketplace.
- multi-agent scheduling.
- hosted Copilot CAPI.
- cross-provider Gitea support.

## Design Principles

- Prefer explicit triggers; do not default to ambient monitoring.
- Default to read-only; enable write permissions gradually.
- Every agent has an owner and scope.
- Every run records actor, trigger, repo, commit, tool calls, and final artifact.
- Dangerous actions must be explainable, approvable, and auditable.
- Docs and commands must always say whether a path is GitHub-hosted or self-hosted.
