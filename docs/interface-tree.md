# ChatGH 接口树

ChatGH 按 GitHub 用户熟悉的资源模型组织接口，同时保留 ChatGH 自己的凭据解析、JSON 输出、安全门和 Python API 契约。当前包只面向 GitHub；Gitea / Forgejo 的探索应放在 ChatTea 或未来的跨平台抽象层，除非某个 ChatGH 命令明确是 GitHub 兼容能力。

## 当前命令面

从 `0.2.13` 起，实际 `chatgh --tree` / `chatgh --tree-brief` 的注册结果为准；文档保留一份用于人类阅读和审阅。

```text
chatgh
├── --help  # Show this message and exit.
├── --version  # Show the version and exit.
├── --tree  # Print the registered CLI tree and exit.
├── --tree-brief  # Print the registered CLI tree without parameter signatures and exit.
├── fetch [REMOTE] [REFSPEC] [--token TOKEN]  # Fetch from the current branch upstream or an explicit remote.
├── invitation  # Repository invitation helpers.
│   ├── accept <INVITATION-ID> [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Accept a repository invitation by id.
│   ├── decline <INVITATION-ID> [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Decline a repository invitation by id.
│   └── list [--limit LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # List repository invitations for the authenticated user.
├── pr  # Pull request helpers.
│   ├── checks [NUMBER] [--repo REPO] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Show CI check status for a pull request.
│   ├── close [NUMBER] [--repo REPO] [--comment COMMENT] [--delete-branch] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Close a pull request.
│   ├── comment [NUMBER] [--repo REPO] [--body BODY] [--body-file BODY-FILE] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Comment on a pull request.
│   ├── create [--repo REPO] [--base BASE] [--head HEAD] [--title TITLE] [--body BODY] [--body-file BODY-FILE] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Create a pull request.
│   ├── diff [NUMBER] [--repo REPO] [--token TOKEN] [--interactive]  # Show a pull request diff.
│   ├── edit [NUMBER] [--repo REPO] [--title TITLE] [--body BODY] [--body-file BODY-FILE] [--state STATE] [--base BASE] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Edit a pull request.
│   ├── list [--repo REPO] [--state STATE] [--limit LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # List pull requests.
│   ├── merge [NUMBER] [--repo REPO] [--method METHOD] [--title TITLE] [--message MESSAGE] [--message-file MESSAGE-FILE] [--check] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Merge a pull request.
│   ├── ready [NUMBER] [--repo REPO] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Mark a draft pull request ready for review.
│   ├── reopen [NUMBER] [--repo REPO] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Reopen a pull request.
│   ├── review [NUMBER] [--repo REPO] [--approve] [--request-changes] [--comment] [--body BODY] [--body-file BODY-FILE] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Review a pull request.
│   ├── status [--repo REPO] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Show current repository pull request status.
│   ├── update-branch [NUMBER] [--repo REPO] [--expected-head-sha EXPECTED-HEAD-SHA] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Update a pull request branch from its base branch.
│   └── view [NUMBER] [--repo REPO] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Show pull request details.
├── project  # GitHub Projects helpers.
│   ├── close [NUMBER] [--owner OWNER] [--undo] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Close or reopen a project.
│   ├── copy [NUMBER] [--owner OWNER] [--target-owner TARGET-OWNER] [--title TITLE] [--drafts] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Copy a project.
│   ├── create [--owner OWNER] [--title TITLE] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Create a project.
│   ├── delete [NUMBER] [--owner OWNER] [--confirm CONFIRM] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Delete a project.
│   ├── edit [NUMBER] [--owner OWNER] [--title TITLE] [--description DESCRIPTION] [--readme README] [--visibility VISIBILITY] [--accept-visibility-change-consequences] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Edit a project.
│   ├── field  # Manage project fields.
│   │   ├── create [NUMBER] [--owner OWNER] [--name NAME] [--data-type DATA-TYPE] [--single-select-option OPTIONS] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Create a project field.
│   │   ├── delete [NUMBER] [--owner OWNER] [--field-id FIELD-ID] [--confirm CONFIRM] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Delete a project field.
│   │   └── list [NUMBER] [--owner OWNER] [--limit LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # List project fields.
│   ├── item  # Manage project items.
│   │   ├── add [NUMBER] [--owner OWNER] [--url URL] [--content-id CONTENT-ID] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Add an issue or pull request item to a project.
│   │   ├── archive [NUMBER] [--owner OWNER] [--id ITEM-ID] [--undo] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Archive or unarchive a project item.
│   │   ├── create [NUMBER] [--owner OWNER] [--title TITLE] [--body BODY] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Create a draft issue item.
│   │   ├── delete [NUMBER] [--owner OWNER] [--id ITEM-ID] [--confirm CONFIRM] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Delete a project item.
│   │   ├── edit [NUMBER] [--owner OWNER] [--id ITEM-ID] [--field-id FIELD-ID] [--field-name FIELD-NAME] [--text TEXT] [--number NUMBER-VALUE] [--date DATE] [--single-select-option-id SINGLE-SELECT-OPTION-ID] [--iteration-id ITERATION-ID] [--clear] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Edit a project item field value.
│   │   └── list [NUMBER] [--owner OWNER] [--limit LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # List project items.
│   ├── link [NUMBER] [--owner OWNER] [--repo-id REPO-ID] [--team-id TEAM-ID] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Link a repository or team to a project.
│   ├── list [--owner OWNER] [--limit LIMIT] [--closed] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # List projects for an owner.
│   ├── mark-template [NUMBER] [--owner OWNER] [--undo] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Mark or unmark a project as a template.
│   ├── unlink [NUMBER] [--owner OWNER] [--repo-id REPO-ID] [--team-id TEAM-ID] [--confirm CONFIRM] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Unlink a repository or team from a project.
│   └── view [NUMBER] [--owner OWNER] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # View a project.
├── pull [REMOTE] [BRANCH] [--ff-only] [--rebase] [--token TOKEN]  # Pull safely from the current branch upstream or an explicit target.
├── push [REMOTE] [REFSPEC] [--set-upstream] [--dry-run] [--tags] [--token TOKEN]  # Push a validated refspec or tags without force modes.
├── repo  # Repository helpers.
│   ├── clone <REPO> [DIRECTORY] [--ssh] [--set-token] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Clone a repository without overwriting an existing directory.
│   ├── create [--owner OWNER] [--name NAME] [--description DESCRIPTION] [--public] [--if-exists IF-EXISTS] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Create a repository. Repositories are private by default.
│   ├── edit [REPO-ARG] [--repo REPO-OPTION] [--description DESCRIPTION] [--homepage HOMEPAGE] [--default-branch DEFAULT-BRANCH] [--visibility VISIBILITY] [--accept-visibility-change-consequences] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Edit repository metadata.
│   ├── fork [SOURCE-ARG] [--source SOURCE] [--owner OWNER] [--org ORG] [--name NAME] [--fork-name FORK-NAME] [--default-branch-only] [--if-exists IF-EXISTS] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Fork a repository into a target owner or organization.
│   ├── list [--owner OWNER] [--limit LIMIT] [--sort SORT] [--direction DIRECTION] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # List repositories for an owner or organization.
│   ├── protection [--repo REPO] [--owner OWNER] [--limit LIMIT] [--jobs JOBS] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Show default-branch protection and ruleset status.
│   ├── sync [REPO-ARG] [--repo REPO-OPTION] [--branch BRANCH] [--remote REMOTE] [--ff-only] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Fetch and fast-forward the current checkout for a repository.
│   ├── transfer [REPO-ARG] [--repo REPO-OPTION] [--owner OWNER] [--org ORG] [--team-id TEAM-IDS] [--dry-run] [--accept-transfer-consequences] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Transfer a repository to another GitHub owner or organization.
│   └── view [REPO-ARG] [--repo REPO-OPTION] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # View repository details.
├── repo-perms [--repo REPO] [--json JSON-FIELDS] [--json-output] [--full-json] [--token TOKEN]  # Show repository permissions for the current token.
├── run  # GitHub Actions helpers.
│   ├── cancel [RUN-ID-ARG] [--repo REPO] [--run-id RUN-ID] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Cancel a workflow run.
│   ├── download [RUN-ID-ARG] [--repo REPO] [--run-id RUN-ID] [--name NAME] [--dir OUTPUT-DIR] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Download workflow run artifacts.
│   ├── list [--repo REPO] [--branch BRANCH] [--status STATUS] [--event EVENT] [--limit LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # List workflow runs.
│   ├── logs [--repo REPO] [--job-id JOB-ID] [--tail TAIL] [--output OUTPUT] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Show logs for a workflow job.
│   ├── rerun [RUN-ID-ARG] [--repo REPO] [--run-id RUN-ID] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Rerun a workflow run.
│   ├── view [--repo REPO] [--run-id RUN-ID] [--job-limit JOB-LIMIT] [--json JSON-FIELDS] [--json-output] [--token TOKEN] [--interactive]  # Show a workflow run and its jobs.
│   └── watch [RUN-ID-ARG] [--repo REPO] [--run-id RUN-ID] [--interval INTERVAL] [--timeout TIMEOUT] [--json JSON-FIELDS] [--json-output] [--token TOKEN]  # Watch a workflow run until it completes.
├── set-token [--token TOKEN] [--save-env] [--from-config] [--file REPO-FILE] [--dry-run] [--json-output]  # Set or update the repository GitHub HTTPS token configuration.
└── unset-token  # Remove exactly the repository config item written by set-token.
```

## 目标命令方向

后续新增接口必须先有证据来源，不能只因为名字看起来合理就加占位命令。可接受的证据来源包括：

1. 官方 `gh` 命令形态或帮助页。
2. GitHub REST 或 GraphQL 接口。
3. GitHub 官方文档里的 GitHub App 或 webhook 模型。
4. 明确设计过的 ChatGH 本地能力，例如凭据配置、webhook 载荷标准化或运行器桥接。

已确认可发展的资源域：

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

保留 ChatGH 自有命令：

- `set-token`：为当前仓库配置仓库本地 HTTPS 授权头，并可选写入 ChatEnv 的 `GITHUB_ACCESS_TOKEN`。
- `unset-token`：与 set 选择同一 origin 优先目标，删除 set 写入的精确 Git 配置项；不判断 token 内容，不清理其它目标。
- `fetch` / `pull` / `push`：调用范围内的 GitHub HTTPS Git 传输。没有显式 target 时只读取当前分支 upstream；不会从无关 remote/branch 猜测目标。
- `repo-perms`：检查当前令牌权限，并推导 ChatGH 能力。
- `agent event ...`：未来的本地事件到运行器桥接；如果实现，不能伪装成 GitHub Copilot 的托管代理运行时。

## 职责边界

- `set-token`：把 GitHub 令牌保存到当前仓库的本地 git 配置，并可选保存到 ChatEnv。
- `unset-token`：只从当前仓库 local config 删除选中 GitHub HTTPS remote 的 token header；输出安全 JSON，不输出 token 或掩码。
- `fetch` / `pull` / `push`：分别验证 Git 生效的 fetch/push URL（含 rewrite 与 `pushurl`），只允许无凭据 `github.com` HTTPS；调用范围内清空旧 header/helper，并用一次性 helper 供应当前解析出的 token。
- `repo-perms`：解析当前令牌、读取仓库权限，并推导 ChatGH 能力。
- `repo list/view/create/edit/fork/transfer/clone/sync/protection`：覆盖仓库清单、仓库变更、所有权迁移、本地检出、fork 创建和治理检查。
- `pr list/create/view/comment/edit/checks/merge/status/diff/close/reopen/review/ready/update-branch`：覆盖 PR 生命周期、评审、合并门禁和 CI 检查。
- `project ...`：通过 ChatGH 的 Project / item / field 命令树覆盖 GitHub Projects v2，不沿用官方 `gh project` 的扁平别名。
- `run list/view/logs/watch/rerun/cancel/download`：覆盖 GitHub Actions 工作流运行、作业日志和产物。
- `invitation list/accept/decline`：覆盖认证用户收到的仓库邀请。
- 未来 `repo pages` / `pages`：检查和配置 GitHub Pages 的 source 分支、路径和构建模式。当前文档部署只依赖仓库工作流文件和仓库已有 Pages 设置。
- 未来 `webhook`：创建、列出、测试、删除仓库或组织 webhook，并验证或标准化 webhook 载荷。
- 未来 `app`：管理 GitHub App 安装令牌流程和安装清单。
- 未来 `agent-task`：命名上对齐官方 `gh agent-task`，但除非明确接入 GitHub Copilot / CAPI，否则 ChatGH 实现应保持运行器中立。
- 未来 `skill`：当 ChatGH 需要检查或安装仓库发布的代理技能时，对齐官方 `gh skill` 和 Agent Skills 约定。

## 命令到 Python 函数映射

每个公开 CLI 命令背后都应有可导入的 Python 函数或方法。集成服务、网关、MCP 工具和未来代理运行时，在可行时应直接调用 Python API，而不是再 shell 调用 CLI。

```text
chatgh set-token              -> chatgh.github.commands.set_token / token_config.set_repository_tokens
chatgh unset-token            -> chatgh.github.transport.unset_token
chatgh fetch                  -> chatgh.github.transport.fetch
chatgh pull                   -> chatgh.github.transport.pull
chatgh push                   -> chatgh.github.transport.push
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

## 机器人方向

ChatGH 机器人的产品定义、manifest 形态、生命周期、GitHub 原生流程、权限、运行时和双语配置示例见 `docs/agent-definition.md`。官方 `gh agent-task`、GitHub Copilot 代理任务、`gh skill`、GitHub Apps、webhook 和自托管 CLI 代理运行器的证据边界见 `docs/agent-task-bot-alignment.md`。

简要结论：

- 官方 `gh` 没有公开 `gh bot` 命令。
- 官方 `gh` 有预览版 `gh agent-task`，别名包括 `agent-task`、`agent-tasks`、`agent` 和 `agents`。
- 官方 `gh agent-task` 当前是 GitHub Copilot / CAPI 工作流，不是通用自托管机器人运行时。
- ChatGH 应参考官方命名，但第一版机器人桥接应把 GitHub webhook 事件标准化为本地 CLI 代理任务。

## 非目标

- 不因为官方 `gh` 或 GitHub 文档提到某个领域就添加占位命令。
- 不把官方 `gh` 作为运行时依赖或 fallback。
- 不在示例、日志或 JSON fixture 中放置令牌、webhook secret 或 GitHub App private key。
- 不实现 GitHub Copilot / CAPI 行为，除非命令明确说明它在调用 GitHub 托管代理任务。
- 不把 repository、project、issue、PR 或 run ID 做成 ChatEnv 字段；这些都应是请求参数。

## 测试与 CI 契约

每个已实现资源域都应有这些门禁：

1. API 路径、方法、载荷、令牌解析和错误处理的单元测试。
2. 覆盖非平凡命令行为的直接 Python 函数测试。
3. 覆盖帮助、成功路径、JSON 输出和预期失败的 CLI 冒烟测试。
4. 远端变更和危险操作的安全门测试。
5. PR 就绪前运行 `python -m pytest -q`、`python -m build`、`mkdocs build --strict` 和 `git diff --check`。
