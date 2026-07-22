# GitHub 代理任务与机器人对齐

本文记录 GitHub 官方 CLI 和 API 在代理、任务、技能、机器人、GitHub App 与 webhook 方面已经提供的能力，并定义 ChatGH 如何扩展机器人命令面，避免把 GitHub 托管的 Copilot 代理和 ChatGH 自托管 CLI 代理桥接混在一起。

## 摘要

- 官方 `gh` 没有一等 `gh bot` 命令组。
- 官方 `gh` 有预览版 `gh agent-task`，别名包括 `agent-task`、`agent-tasks`、`agent` 和 `agents`。
- 官方 `gh agent-task` 是 GitHub Copilot 代理任务客户端，用于创建和查看 GitHub 托管的编码代理会话，通常和 PR 关联。
- 官方 `gh skill` / `gh skills` 是预览命令组，用于从 GitHub 仓库安装和管理代理技能。
- `gh api`、issue / PR 评论、check / status、workflow dispatch、GitHub Apps 和 webhook 是构建自定义机器人的通用原语。
- ChatGH 命名应对齐官方 `gh agent-task`，但自托管事件到运行器流程必须和 GitHub Copilot / CAPI 分开实现。
- 代理身份、manifest 字段、生命周期、权限、运行时和输出策略见 `docs/agent-definition.md`。

## 证据来源

官方 GitHub CLI：

- 源码：https://github.com/cli/cli
- 手册：https://cli.github.com/manual/
- GitHub CLI 文档：https://docs.github.com/en/github-cli
- 相关源码路径：`pkg/cmd/agent-task`
- 相关源码路径：`pkg/cmd/skills`
- 相关源码路径：`pkg/cmd/copilot`

GitHub API 文档：

- 代理任务 REST 文档：https://docs.github.com/en/rest/agent-tasks/agent-tasks
- GitHub Apps 概览：https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/about-creating-github-apps
- App 安装接口：https://docs.github.com/en/rest/apps/installations
- Webhook 概览：https://docs.github.com/en/webhooks/about-webhooks
- 仓库 webhook：https://docs.github.com/en/rest/repos/webhooks
- 检查运行接口：https://docs.github.com/en/rest/checks/runs
- Issue 评论接口：https://docs.github.com/en/rest/issues/comments
- Workflow dispatch 接口：https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

## 官方 `gh agent-task` 做什么

官方 CLI 源码定义了：

```text
gh agent-task <command>
```

别名：

```text
gh agent-task
gh agent-tasks
gh agent
gh agents
```

已实现的预览子命令：

```text
gh agent-task create [<task description>] [flags]
gh agent-task list [flags]
gh agent-task view [<session-id> | <pr-number> | <pr-url> | <pr-branch>] [flags]
```

当前实现是 GitHub Copilot / CAPI 客户端，不是通用机器人运行器：

- `create` 会为某个仓库排队一个 GitHub 托管代理任务。
- 任务输入可以来自参数、`--from-file/-F`、stdin 或编辑器提示。
- `--repo/-R` 选择目标仓库。
- `--base/-b` 选择 PR base 分支，默认是仓库默认分支。
- `--custom-agent/-a` 选择 `.github/agents/<name>.md` 中定义的 custom agent。
- 返回的任务可能产生一个 PR 和一个代理会话 URL。
- `list` 显示当前查看者最近的代理会话。
- `view` 可通过会话 ID、PR 编号、PR URL 或 PR 分支读取会话，并可显示日志。

官方源码中观察到的重要实现细节：

- 任务通过 Copilot / CAPI 创建，路径形如 `/agents/swe/v1/jobs`。
- 会话通过 Copilot / CAPI 路径读取，形如 `/agents/sessions`、`/agents/sessions/{id}`、`/agents/sessions/{id}/logs` 和 `/agents/resource/{resource_type}/{resource_id}`。
- CLI 通过 GraphQL 查询 `viewer.copilotEndpoints.api` 解析 Copilot API 入口。
- 命令需要 OAuth / device-flow 风格的令牌，不只是任意 PAT。
- 会话展示以 PR 为中心：会话资源通过 GitHub GraphQL PR 节点补全，URL 显示为 `https://github.com/OWNER/REPO/pull/NUMBER/agent-sessions/SESSION_ID`。
- 日志包含聊天补全片段和渲染后的工具调用，包括 shell、GitHub Actions 和类似 MCP 的工具调用。

解读：

`gh agent-task` 是 GitHub 面向托管编码代理工作的 CLI 入口，最接近“把任务分配给 Copilot 编码代理，并跟踪生成的 PR / 会话”。它不等同于“有人在 issue 里评论时运行我自己的本地 Codex / Hermes / OpenHands 机器人”。

## 官方 `gh skill` 做什么

官方 CLI 源码定义了：

```text
gh skill <command>
```

别名：

```text
gh skills
```

相关预览子命令包括：

```text
gh skill install <repository> [<skill[@version]>]
gh skill list
gh skill search <query>
gh skill preview <repository> <skill>
gh skill update
```

观察到的行为：

- 技能从 GitHub 仓库和本地目录发现。
- 约定基于 `skills/*/SKILL.md` 和 Agent Skills 规范：https://agentskills.io/specification。
- 安装器也知道隐藏或本地代理技能目录，例如 `.agents/skills` 以及部分代理宿主的目标目录。
- 已安装技能带有来源跟踪元数据，因此 `gh skill update` 可以检测上游变化。
- CLI 会警告技能未经 GitHub 验证，可能包含提示注入、隐藏指令或恶意脚本。

解读：

GitHub 正在把“代理任务”和“代理技能”分开：

- `agent-task` 是一次运行、会话或工作项。
- `skill` 是安装到代理宿主里的可复用能力包。

这对 ChatGH 有价值，因为它给出了一套清晰词汇：

- `agent-task`：绑定仓库的工作单元。
- `skill`：来自仓库的可复用代理能力。
- `custom-agent`：代理画像或角色文件，例如 `.github/agents/name.md`。

## GitHub 通用机器人原语

即使没有 `gh bot`，官方 `gh` 也暴露了很多可以组合成机器人的原语：

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

对 ChatGH 来说，底层 GitHub API 比 shell 调用官方 `gh` 更重要：

- Issue 评论：`POST /repos/{owner}/{repo}/issues/{issue_number}/comments`
- PR 评审：`POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews`
- 提交状态：`POST /repos/{owner}/{repo}/statuses/{sha}`
- Check run：`POST /repos/{owner}/{repo}/check-runs`，通常需要 GitHub App 的 `checks:write` 权限。
- Workflow dispatch 接口：`POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches`
- 仓库 dispatch：`POST /repos/{owner}/{repo}/dispatches`
- 仓库 webhook：`/repos/{owner}/{repo}/hooks`
- 组织 webhook：`/orgs/{org}/hooks`
- GitHub App 安装令牌：`/app/installations/{installation_id}/access_tokens`

## 官方 `gh` 能完成的常见机器人操作

官方 `gh` 可以完成很多机器人动作，但它不提供完整机器人运行时。ChatGH 设计时可把这些能力作为有证据的命令词汇，而不是把官方 `gh` 变成运行时依赖。

### 身份和凭据设置

| 操作 | 官方 `gh` 支持 | 说明 |
|---|---|---|
| 创建普通机器人用户 | 不是 CLI 操作 | 在 GitHub 浏览器页面注册用户，再给它添加组织或仓库权限。 |
| 以机器人用户登录 | `gh auth login` | 适合本地或人工配置；自动化通常使用 `GH_TOKEN` / `GITHUB_TOKEN`。 |
| 显示当前令牌 | `gh auth token` | 适合调试；不要写入日志。 |
| 创建 fine-grained PAT | 不是 CLI 操作 | 通过 GitHub UI 创建。 |
| 创建 GitHub App | 不是普通 CLI 操作 | 通常通过 GitHub UI 或 app manifest flow 创建。 |
| 创建 installation token | 已有 app JWT 时可用 `gh api` | 如果 GitHub App 支持成为一等能力，ChatGH 应直接实现。 |

### Webhook 操作

```bash
# 创建仓库 webhook。
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

# 列出仓库 webhook。
gh api repos/OWNER/REPO/hooks

# 测试仓库 webhook。
gh api repos/OWNER/REPO/hooks/HOOK_ID/tests -X POST

# 删除仓库 webhook。
gh api repos/OWNER/REPO/hooks/HOOK_ID -X DELETE
```

组织 webhook 使用同样模式，路径是 `orgs/ORG/hooks`。机器人运行时仍必须接收 HTTP 请求、验证 `X-Hub-Signature-256` 并对 delivery ID 去重；官方 `gh` 不负责这一部分。

### 线程和评审操作

```bash
# 为代理任务创建 issue。
gh issue create --repo OWNER/REPO --title "代理任务" --body "Please investigate ..."

# 评论 issue。
gh issue comment 123 --repo OWNER/REPO --body "Agent started."

# 评论 PR。
gh pr comment 12 --repo OWNER/REPO --body "Agent review complete."

# 提交 PR review。
gh pr review 12 --repo OWNER/REPO --comment --body "Reviewed by agent."
```

### 工作产物操作

```bash
# 本地机器人分支推送后创建 PR。
gh pr create \
  --repo OWNER/REPO \
  --base main \
  --head bot/fix-123 \
  --title "Fix issue 123" \
  --body "Generated by agent."

# 创建 release。
gh release create v1.2.3 --repo OWNER/REPO --notes "Generated release notes."

# 触发 workflow。
gh workflow run agent.yml --repo OWNER/REPO -f issue=123

# 触发 repository dispatch 事件。
gh api repos/OWNER/REPO/dispatches \
  -X POST \
  -f event_type=chatgh-agent \
  -f client_payload='{"issue":123}'
```

### 状态和检查操作

```bash
# 创建 commit status。
gh api repos/OWNER/REPO/statuses/SHA \
  -X POST \
  -f state=pending \
  -f context=chatgh-agent \
  -f description="Agent is running"

# 创建 check run；通常需要带 checks:write 权限的 GitHub App token。
gh api repos/OWNER/REPO/check-runs \
  -X POST \
  -f name=chatgh-agent \
  -f head_sha=SHA \
  -f status=in_progress
```

### 托管代理和技能操作

```bash
# GitHub 托管 Copilot 代理任务，预览能力。
gh agent-task create "fix the failing tests" --repo OWNER/REPO --base main

gh agent-task list

gh agent-task view SESSION_ID

# 代理技能，预览能力。
gh skill search code-review
gh skill install OWNER/SKILL_REPO skill-name
gh skill list
```

对 ChatGH 的设计含义：

- 用官方 `gh` 命令形态作为词汇参考。
- 实现官方 `gh` 不负责的机器人运行时部分：事件接收、签名验证、命令解析、权限检查、任务状态、运行器调用、审计日志、重试和跨提供方标准化。
- ChatGH 应优先直接实现 Python / API 层，而不是 shell 调用 `gh`，这样才能保持稳定 JSON、令牌解析、安全门和测试。

## 现有 GitHub 机器人案例：Julia Registrator

Julia 包生态是仓库原生机器人的具体先例。

相关项目：

- Registrator 项目：https://github.com/JuliaRegistries/Registrator.jl
- General registry 项目：https://github.com/JuliaRegistries/General
- TagBot 项目：https://github.com/JuliaRegistries/TagBot
- RegistryCI / AutoMerge 项目：https://github.com/JuliaRegistries/RegistryCI.jl

Registrator 的用户体验：

```text
@JuliaRegistrator register
@JuliaRegistrator register branch=name-of-your-branch
```

包维护者在 commit、issue 或 PR 上评论。Registrator 接收 GitHub 事件，检查调用者和仓库状态，读取 Julia `Project.toml`，然后向 Julia General registry 创建或更新 registration PR。这个 registry PR 随后由 registry CI / AutoMerge 检查并可能自动合并。版本注册后，TagBot 会在包仓库里创建 Git tag、GitHub release 和 changelog。

Registrator 的实现模型是混合模式：

- 一个 GitHub App 安装在包仓库上。
- App 订阅 issue comment 和 commit comment 事件。
- App 使用 webhook URL 和 webhook secret 接收并验证 GitHub 事件。
- App 仓库权限以读取为主：contents、issues、metadata 和 commit statuses。
- 单独的机器人账号 / PAT 可用于发表评论、创建 registry PR 和处理私有 registry。
- 机器人会验证评论者是否允许注册，例如 collaborator 或组织成员检查。
- 机器人从评论正文解析一套很小的命令语言。
- 机器人把状态或评论写回源线程，并在目标 registry 仓库打开 PR。

从源码和文档可见的接口：

- Webhook 事件：issue comment 和 commit comment。
- GitHub App 鉴权：app id + private key -> JWT -> installation access token。
- Bot-user auth：配置 GitHub 用户名 + PAT，用于需要以机器人用户身份完成的动作。
- 源仓库读取：分支、commit、文件内容、tag、项目元数据。
- 写回：issue / commit 评论和 commit status。
- 目标仓库变更：在 registry 仓库创建或更新 PR。

TagBot 使用另一种互补模式：

- 它是安装在每个包仓库里的 GitHub Action，路径通常是 `.github/workflows/TagBot.yml`。
- 典型 workflow 监听 `issue_comment` 和 `workflow_dispatch`。
- 只有 actor 是 `JuliaTagBot` 或手动触发时才自动运行。
- 它使用 `GITHUB_TOKEN`、可选 PAT 或 SSH deploy key 创建 tag 和 GitHub release。

对 ChatGH 的含义：

- 有用的机器人不一定需要新的聊天 UI；GitHub 里的评论命令就可能足够。
- 持久工作单元是仓库线程，以及生成的 PR、status 或 release 产物。
- GitHub App webhook 最适合事件投递和范围化读取。
- 写动作仍需要机器人用户令牌或 installation token，具体取决于期望身份和权限。
- ChatGH 自托管代理桥接可遵循同样形态：安装并监听 -> 解析命令 -> 检查权限 -> 运行代理 -> 写回评论、status 或 PR。

## 机器人接入模式

### 模式一：机器人用户加 fine-grained PAT

最快原型：

1. 创建普通 GitHub 用户，例如 `chatgh-bot`。
2. 把该用户加入仓库或组织，并只授予有限权限。
3. 通过 ChatGH 令牌解析配置 fine-grained PAT。
4. 让 ChatGH 以该用户身份读取事件并发布评论、PR 或 status。

优点：

- 符合当前 ChatGH 令牌解析方式。
- 可以直接用已有 `pr comment`、`pr create`、`repo-perms` 和 `run` 命令测试。
- 身份会显示在 issue 和 PR 线程里。

缺点：

- 权限和审计模型比 GitHub Apps 粗。
- 令牌轮换和最小权限较弱。
- 很难像 app 一样安装到大量仓库。

### 模式二：GitHub App

最适合长期组织或社区模型：

1. 注册 GitHub App。
2. 安装到选定仓库或组织。
3. 订阅 webhook 事件。
4. 用 app JWT + installation id 换取短期 installation access token。
5. 以 `<app-slug>[bot]` 身份和 app 范围化权限执行动作。

优点：

- 一等机器人身份。
- 安装范围化权限。
- 原生 webhook 投递和审计模型。
- 适合组织级部署。

缺点：

- 需要 JWT / private-key 支持。
- 需要设置体验和密钥管理。
- 需要 PAT 之外的新 ChatGH 凭据模式。

### 模式三：Webhook 事件桥接

最适合第一版 ChatGH 原生机器人闭环：

1. 在一个小网关服务中接收 GitHub webhook 事件。
2. 验证 webhook 签名。
3. 调用 `chatgh agent event normalize ...` 生成跨提供方的任务载荷。
4. 调用本地 CLI 代理运行器，例如 Codex、Hermes、OpenHands 或 Claude Code。
5. 使用 ChatGH 把进度和最终评论写回原始线程。

这个模式最接近用户的产品想法：仓库或社区线程成为代理任务入口。

### 模式四：GitHub Actions 运行器

适合更安全的仓库内自动化：

- 评论或 label 触发 Actions workflow。
- workflow 在受控 runner 中调用 CLI 代理。
- ChatGH 回报产物、日志、PR 链接和 status。

这个模式可以复用 GitHub 原生日志、secrets 和权限，但可能比 webhook 网关更慢、交互性更弱。

## 建议的 ChatGH 命令方向

ChatGH 应保留和官方兼容的命名，同时清楚地区分 GitHub 托管代理任务和自托管代理任务。

### 第零阶段：文档和 API 证据

不发布公开占位命令。

- 记录官方 `gh agent-task`、`gh skill`、GitHub Apps、webhook 和 REST 证据。
- 让 `docs/interface-tree.md` 和本文档作为命令方向来源。

### 第一阶段：自托管事件标准化

建议命令面：

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

别名可包含 `agent-task` 和 `bot`，但真正实现前应先明确自托管命名空间。

### 第二阶段：任务评论和状态

建议命令面：

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

### 第三阶段：Webhook 管理

建议命令面：

```bash
chatgh agent webhook list --repo OWNER/REPO
chatgh agent webhook create --repo OWNER/REPO --url https://example.com/webhook --events issue_comment,pull_request,workflow_run
chatgh agent webhook test --repo OWNER/REPO --id 123
chatgh agent webhook delete --repo OWNER/REPO --id 123 --confirm
```

### 第四阶段：GitHub App 鉴权

建议命令面：

```bash
chatgh app installations list --app-id APP_ID --private-key-file key.pem
chatgh app token --installation-id ID --app-id APP_ID --private-key-file key.pem --json-output
```

`app` 应和 `agent` 分开，因为 GitHub App 鉴权是 GitHub 专属能力，不应泄漏进跨提供方任务处理。

### 第五阶段：GitHub 托管代理任务互操作

只有在明确要调用 GitHub Copilot / CAPI 或 GitHub Agent Tasks REST 接口时才实现。

可能形态：

```bash
chatgh agent-task create "fix the failing tests" --repo OWNER/REPO --base main --custom-agent my-agent
chatgh agent-task list --limit 20 --json-output
chatgh agent-task view SESSION_ID --repo OWNER/REPO --json-output
```

规则：

- 如果命令调用 GitHub 托管 Copilot / CAPI，要在帮助文本里明说。
- 如果命令调用本地运行器，也要在帮助文本里明说是自托管或本地。
- 不要在同一个行为里静默混用两种模型。

## 标准化事件结构

未来事件处理应先把 GitHub webhook 载荷标准化成稳定结构，再调用任何运行器。

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

## 安全契约

机器人命令必须比普通只读 CLI 命令更严格：

- 默认只响应明确 mention 或 slash command。
- 默认忽略机器人自己发布的评论，除非显式允许。
- 处理载荷前验证 webhook 签名。
- 对 webhook delivery ID 去重。
- webhook handler 必须有仓库或组织 allowlist。
- 公共或社区仓库先从只读或仅评论行为开始。
- push、merge、delete、visibility 变更或 secret 变更前需要人工确认。
- 长任务要发布可见进度。
- 审计日志要保留 actor、repo、command、token source、runner 和最终动作。
- 绝不打印令牌、webhook secret、GitHub App private key 或原始 Authorization header。

## ChatTea / Gitea 可迁移经验

Gitea 没有 GitHub 完全相同的托管 Copilot agent-task 模型。对 Gitea / ChatTea 来说，最接近的等价物是：

- 机器人用户 + access token。
- 仓库、组织或系统 webhook。
- issue / PR 评论作为任务线程。
- commit status 和 Actions runner API 用于进度与 CI。

因此：

- ChatGH 应保持 GitHub-first，以对齐官方 `gh`。
- ChatTea 应负责 Gitea 原生命令和本地 Gitea 生命周期。
- 未来的跨提供方层可以在 GitHub 和 Gitea 之间共享事件结构和运行器契约。
