# ChatGH 机器人定义

本文定义 ChatGH 里“机器人”的产品语义、配置边界、运行流程和 GitHub 接口映射。目标是让后续 `chatgh agent ...` / `chatgh agent-task ...` 设计有一个稳定词汇表，而不是把 GitHub App、bot user、GitHub Actions、Copilot agent task、本地 CLI agent 混成一个概念。

## 一句话定义

ChatGH 机器人是一个安装在 GitHub 组织、仓库或线程中的可审计工作成员。它有身份、触发方式、上下文范围、工具权限、运行时、输出约定和人工确认规则；它把 GitHub 里的 issue、PR、comment、webhook 或 workflow 事件转成可执行任务，再把进度和产物写回 GitHub。

它不是单纯的聊天窗口，也不是一个裸模型调用。

```text
机器人 = 身份 + 触发器 + 上下文 + 权限 + 技能/工具 + 运行时 + 任务状态 + 输出/审计
```

## 术语边界

| 术语 | ChatGH 语义 | 例子 |
|---|---|---|
| 机器人 | 可安装、可触发、可授权、可审计的工作成员 | `@chatgh-reviewer`、`release-manager` |
| 机器人身份 | GitHub 上显示的执行身份 | GitHub App `chatgh[bot]`、普通机器人用户 |
| 代理任务 | 一次被分配的工作单元 | “修复 issue #123 的失败测试” |
| 运行 / 会话 | 一次实际执行过程 | 运行器日志、工具调用、成本、状态 |
| 触发器 | 触发任务的事件或命令 | `@chatgh-agent fix this`、`workflow_dispatch` |
| 技能 | 可复用能力包 | 代码评审技能、发布说明技能 |
| 工具 | 可调用的外部能力 | GitHub API、shell、browser、MCP server |
| 策略 | 权限与安全策略 | 只读、可评论、可开 PR、合并前审批 |
| 产物 | 交付物 | PR、评论、release、patch、summary、log |

## 为什么不用单一“机器人”概念

GitHub 生态里“bot”经常指不同层：

1. 普通机器人用户：一个 GitHub 用户 + PAT。
2. GitHub App：安装在 org/repo 上，有 webhook、权限和 `xxx[bot]` 身份。
3. GitHub Actions 机器人：`github-actions[bot]` 在 workflow 中执行。
4. GitHub 托管 Copilot 代理：官方 `gh agent-task` 背后的托管编码代理。
5. 自托管 CLI 代理：Codex、Hermes、OpenHands、Claude Code 等本地或自托管运行器。

ChatGH 文档里应使用更精确的词：

- “GitHub App” 指安装和 webhook/installation token 模型。
- “bot user” 指普通 GitHub 用户和个人访问令牌。
- “agent task” 指任务对象。
- “运行器” 指真正执行任务的进程或服务。
- “agent” 指面向用户的机器人工作成员。

## 最小机器人配置清单

ChatGH 后续可以支持 `.chatgh/agents/<name>.yaml` 作为自托管机器人定义。这个文件不同于官方 `.github/agents/<name>.md`：后者是 GitHub 托管 Copilot 代理的自定义代理入口；前者是 ChatGH 自托管事件到运行器桥接的配置草案。

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
    examples:
      - "@chatgh-reviewer review this PR"
      - "/review focus on security and tests"
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

## 字段解释

### `metadata`

稳定的用户可见身份信息。

- `name`: 机器可读名称，适合作为命令和文件名。
- `displayName`: UI/评论里展示的名称。
- `description`: agent 的职责边界。
- `labels`: 便于目录、市场、组织策略筛选。

### `identity`

Agent 在 GitHub 上如何被识别。

- `github-app`: 推荐的组织级模式，适合 webhook、细粒度权限和审计。
- `bot-user`: 快速原型模式，普通 GitHub 用户 + PAT。
- `actions`: 通过 GitHub Actions 的 `GITHUB_TOKEN` 执行。
- `hosted-copilot`: 明确调用 GitHub hosted Copilot agent task。

### `scope`

Agent 可以看到和响应的范围。范围越小，越容易治理。

- organization scope：组织级安装。
- repository scope：仓库级安装。
- thread scope：issue/PR/comment 线程。
- branch/path scope：只处理某些 branch 或 path。

### `triggers`

Agent 如何被唤起。

常见模式：

```text
@chatgh-agent fix this
/chatgh fix
label: agent:review
workflow_dispatch
repository_dispatch
schedule
```

默认策略应是“显式触发”，避免 agent 在公共仓库或大社区里主动刷屏。

### `context`

运行前加载什么上下文。

可选上下文：

- issue/PR 标题和正文。
- thread comments。
- PR diff。
- check runs / workflow logs。
- repository files。
- project items。
- linked issues。
- organization memory。

上下文必须有上限，避免 prompt 爆炸和权限泄漏。

### `permissions`

权限分两层：

1. 平台权限：GitHub App / PAT / Actions token 能做什么。
2. ChatGH policy：即使 token 有权限，agent 也不一定能调用。

例如 token 可以写 PR，但 agent policy 可以禁止 merge。

### `tools`

工具是 agent 可执行能力，不等于权限本身。

推荐工具命名：

```text
chatgh.repo.view
chatgh.issue.comment
chatgh.pr.diff
chatgh.pr.create
chatgh.status.create
shell.pytest
mcp.github.search
```

工具清单应该默认 allowlist，而不是默认全开。

### `runtime`

运行时可以是：

- `command`: 调本地 CLI，如 `codex --json`。
- `container`: 在 Docker/E2B/Firecracker 沙盒里跑。
- `actions`: 触发 GitHub Actions workflow。
- `hosted-copilot`: 调 GitHub agent task。
- `webhook`: 转发给外部 agent service。

### `memory`

记忆必须有 scope。

- `thread`: 只记住当前 issue/PR。
- `repository`: 记住仓库级偏好和历史任务。
- `organization`: 记住组织级规范。
- `none`: 无持久记忆。

默认不应把 private thread 信息泄漏到更广 scope。

### `approvals`

高风险动作必须人工确认。

建议默认需要确认：

- push 到受保护分支。
- merge PR。
- 创建 release。
- 修改 workflow。
- 修改 repository settings。
- 删除、归档、改 visibility。
- 读取或写入 secrets。

## 机器人生命周期

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

解释：

- `draft`: 定义存在，但未安装。
- `installed`: 已安装到 org/repo，但未必启用。
- `enabled`: 可以响应事件。
- `triggered`: 收到 webhook 或命令。
- `authorized`: 通过 actor、repo、policy 检查。
- `queued`: 已创建任务，等待运行器。
- `running`: 运行器正在执行。
- `waiting_approval`: 等人类批准高风险动作。
- `completed`: 已交付结果。
- `failed`: 执行失败，已写回错误或日志。
- `cancelled`: 人类或系统取消。
- `archived`: 历史任务归档。

## GitHub 原生流程

### 1. 安装

```text
Admin installs GitHub App on org/repo
  -> GitHub sends installation event
  -> ChatGH stores installation id and allowed repos
  -> Admin selects agent manifest or template
```

快速原型可以用 bot user + PAT 跳过 GitHub App，但正式组织场景应优先 GitHub App。

### 2. 触发

```text
User comments: @chatgh-reviewer review this PR
  -> GitHub sends issue_comment webhook
  -> ChatGH verifies signature
  -> ChatGH normalizes event
  -> ChatGH parses command and selects agent
```

### 3. 授权

```text
检查 actor 权限
检查仓库 allowlist
检查线程类型
检查命令 allowlist
检查工具策略
创建审计记录
```

### 4. 执行

```text
构建任务上下文
解析 installation token 或 bot token
准备 checkout / sandbox
调用运行器
用评论、status 或 check 流式回传进度
```

### 5. 交付

```text
发布最终评论
按需创建或更新 PR
设置 commit status 或 check run
附加产物和日志
记录最终审计事件
```

## 三种典型机器人

### 代码评审机器人

职责：读 PR diff 和 CI，发评审评论。

默认权限：

```text
contents: read
pull_requests: write
checks: read
statuses: write
```

默认禁止：

```text
push
merge
release
repo settings
```

### 问题修复机器人

职责：根据 issue 创建分支、修复、测试、开 PR。

需要权限：

```text
contents: write
issues: write
pull_requests: write
statuses: write
```

高风险点：push、修改 workflow、触发外部服务。

### 注册与发布机器人

职责：类似 Julia Registrator / TagBot。

Flow：

```text
@agent register
  -> read package metadata
  -> open registry PR
  -> post status/comment
  -> after merge create tag/release
```

这类 agent 证明 GitHub issue/commit comment 本身就可以成为任务入口，不需要先做新 UI。

## 与官方 GitHub 代理的关系

官方 `gh agent-task` 是 GitHub 托管 Copilot 代理任务。它使用 GitHub/Copilot 后端，支持：

```bash
gh agent-task create "fix the failing tests" --repo octocat/Hello-World --base main
gh agent-task list
gh agent-task view SESSION_ID
```

ChatGH 自托管 agent 不是这个东西。ChatGH 应对齐命名和用户心智，但在帮助文案和文档中明确区分：

- GitHub 托管: `gh agent-task` / Copilot / CAPI。
- ChatGH 自托管：webhook 事件 -> 本地或远端运行器 -> 写回 GitHub。

## ChatGH 命令方向

建议第一批不要直接做完整 server，而是先做可组合 primitives：

```bash
chatgh agent event verify
chatgh agent event normalize
chatgh agent event handle
chatgh agent task comment
chatgh agent status create
chatgh agent webhook create
chatgh app token
```

再逐步加：

```bash
chatgh agent install
chatgh agent list
chatgh agent enable
chatgh agent disable
chatgh agent run view
chatgh agent run logs
chatgh agent approve
```

## 最小可用能力

```text
GitHub issue_comment webhook
  -> chatgh agent event normalize
  -> permission check
  -> 本地运行器命令
  -> issue 评论最终回复
```

最小可用闭环需要：

- webhook secret verification。
- event normalization。
- mention / slash command 解析器。
- comment 写回。
- 本地运行器契约。
- 审计日志。

不属于最小闭环：

- 完整 GitHub App UI。
- marketplace。
- 多机器人调度。
- 托管 Copilot CAPI。
- 跨提供方 Gitea 支持。

## 设计原则

- 显式触发优先，不默认 ambient monitoring。
- 默认只读，写权限逐步打开。
- 每个 agent 都有 owner 和 scope。
- 每次运行都记录 actor、trigger、repo、commit、工具调用和最终产物。
- 所有危险动作必须可解释、可审批、可撤销或可追踪。
- 文档和命令要同时说明“GitHub 托管”和“自托管”的区别。
