# ChatGH 与官方 `gh` 接口对齐规范

ChatGH 是 ChatArch / Arch 系列工具的 GitHub 操作基础层。它应该让熟悉 GitHub CLI `gh` 的人和模型能低成本迁移，同时保留 ChatArch 自有的鉴权、安全门、JSON 输出和 Python API 复用能力。

## 基本原则

1. **官方 `gh` 先作接口参考**：新增常见 GitHub 能力前，先查看对应的官方 `gh <group> <command> --help` 和 GitHub REST/API 文档。
2. **不把官方 `gh` 当运行依赖**：官方 `gh` 只用于命令形态、参数命名、帮助文本和用户习惯参考；真实操作仍由 ChatGH 自己的 Python API / REST 实现完成。
3. **如果官方已有能力，优先借鉴形态**：命令名、位置参数、常见长参/短参应尽量兼容；如果与 ChatGH 语义冲突，要保留 ChatGH 更安全、更自动化友好的行为并在文档里说明差异。
4. **如果官方没有能力，再设计 ChatGH 原生命令面**：新设计也要保持命名清晰、JSON 稳定、可测试、可被 Python 调用。
5. **CLI + Python API 双落地**：CLI 是人和模型调用/review 的界面；背后的函数必须是可 import 的 Python API，供 ChatArch 自动化和其他 Arch 工具复用。

## 代码组织

新增接口应遵循当前分层：

```text
src/chatgh/
  cli.py                         # 顶层命令注册
  commands/pr.py                 # PR 命令组
  github/cli.py                  # repo/run/repo-perms/set-token 命令组
  github/commands.py             # Python 命令与服务函数；CLI 调用这里
  github/requests.py             # GitHub API 与载荷函数
  github/api.py                  # 令牌、仓库解析和底层辅助函数
  github/render.py               # 人类可读输出辅助函数
```

规则：

- CLI 层只做参数解析、交互补问、输出格式选择。
- 业务流程函数放在 `chatgh.github.commands` 或更合适的服务模块。
- GitHub API 细节放在 `chatgh.github.requests` / `api.py`。
- 人类输出与 JSON 载荷分离：Python 函数返回 payload，CLI 只决定表格或摘要、官方风格 `--json FIELDS` 字段投影或 `--json-output` 完整 payload。
- 每个新增 CLI 应有同名或近似 Python API，例如 `chatgh repo view` 对应 `view_repo(...)`。

## CLI 兼容策略

- 官方有位置参数时，ChatGH 应考虑兼容位置参数。
- 官方常见短参/长参若无冲突，应提供别名。例如 `-R/--repo`、`--org`、`--fork-name`。
- 对齐官方 `--json FIELDS`，同时保留 ChatGH 自有扩展：`--json-output`、`--token`、仓库本地鉴权与 ChatEnv 令牌解析、`--if-exists use`、PR 合并安全门。
- 对本地 git 有副作用的行为默认保持克制。`clone`、`remote`、`sync` 等能力必须有明确参数、清晰输出和测试，不能默认覆盖已有 checkout / remote。

## `repo fork` 对齐示例

官方 `gh repo fork` 的常见形态是位置参数 + `--org` / `--fork-name`。ChatGH 同时支持官方形态和显式自动化形态：

```bash
# 类官方 gh 形态，便于熟悉 gh 的人和模型调用
chatgh repo fork Wei-Shaw/claude-relay-service --org ChatArch --fork-name claude-relay-service

# ChatGH 显式形态，便于自动化和幂等流程
chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch --name claude-relay-service --if-exists use --json-output
```

映射：

- 位置参数 `REPO` -> `source`
- `--org` -> 面向组织目标的 `owner`
- `--fork-name` -> `name`
- `--json-output` 和 `--if-exists use` 是 ChatGH 自动化扩展

## 接口范围

### 当前仓库命令

ChatGH 当前提供这些仓库能力：

- `repo list [--owner OWNER] [--json FIELDS] [--json-output]`：列出用户或组织下的仓库。
- `repo create`：创建仓库，默认私有，公开仓库需要显式 `--public`。
- `repo view [REPOSITORY] [-R/--repo REPOSITORY]`：读取仓库基础信息。
- `repo clone REPOSITORY [DIRECTORY]`：安全克隆仓库，目标目录非空时拒绝覆盖。
- `repo sync [REPOSITORY]`：显式执行 `git fetch` 和 `git pull --ff-only`。
- `repo edit [REPOSITORY]`：编辑 description、homepage、default-branch、visibility 小子集；visibility 变更需要显式确认。
- `repo fork [REPOSITORY] --org/--owner ... --fork-name/--name ...`：创建 fork，并支持 `--if-exists use` 幂等复用匹配的已有 fork。
- `repo transfer [REPOSITORY] --owner/--org ...`：迁移仓库所有权；真实迁移必须显式确认后果。
- `repo protection`：检查默认分支保护、classic branch protection 和可读取的 repository rulesets。

规划中的仓库能力：

- `repo pages` / `pages`：检查和配置 GitHub Pages source 分支、路径和构建模式；这应和文档 workflow 文件修改分开处理。

### 当前 PR 命令

ChatGH 当前提供这些 PR 能力：

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

`pr merge` 继续保持安全门；merge 命令是真实远端变更，不得当 dry-run 使用。

### 当前 Actions 运行命令

ChatGH 当前提供这些 Actions 运行能力：

- `run list`
- `run view`
- `run logs`
- `run watch`，必须有 timeout
- `run rerun`
- `run cancel`
- `run download`

### 机器人对齐方向

官方 GitHub CLI 当前没有 `gh bot` 命令组，但源码中已有预览版 `gh agent-task`，并注册了 `agent-task`、`agent-tasks`、`agent`、`agents` 别名。它的语义是 GitHub / Copilot 托管代理任务：在仓库里创建一个代理任务，通常产生 PR 和代理会话，并可通过 `list/view` 查看会话与日志。官方还提供预览版 `gh skill` / `gh skills`，用于从 GitHub 仓库安装和管理代理技能。

ChatGH 的机器人方向必须遵守：

- 命名上优先参考官方 `gh agent-task` / `gh skill`，避免凭空发明与 GitHub 心智冲突的顶层命令面。
- 语义上明确区分 GitHub 托管 Copilot / CAPI 代理任务与 ChatGH 自托管事件到运行器桥接；不能让同一个命令静默混用两种运行时。
- 机器人命令应围绕 GitHub webhook 载荷标准化、签名验证、线程评论与 status 写回、CLI 运行器调用展开。
- 每个机器人命令都要在 `docs/agent-task-bot-alignment.md` 中有证据来源、职责、安全边界和 CLI 到 Python API 映射。

### 不在当前范围

这些命令不属于当前公开能力，除非先补充独立安全设计：

- `repo delete`
- `repo archive`
- `repo rename`
- `pr checkout`
- 任意默认覆盖本地 checkout、remote 或 dirty worktree 的命令
- 静默调用 GitHub Copilot / CAPI 的代理命令

## 当前 CLI 到 Python API 映射

### 仓库

| 命令 | Python API | 说明 |
|---|---|---|
| `chatgh repo list` | `list_repos(owner, limit, sort, direction, token)` | 列出用户或组织仓库，支持字段投影和完整 JSON。 |
| `chatgh repo create ...` | `create_repo(...)` | 创建仓库，公开仓库需要显式参数。 |
| `chatgh repo view [REPOSITORY] [-R/--repo REPOSITORY]` | `view_repo(repo, token)` | 读取仓库基础载荷，支持 JSON。 |
| `chatgh repo clone REPOSITORY [DIRECTORY]` | `clone_repo(repo, directory, ssh, token)` | 安全 clone；目标目录非空则拒绝覆盖；不默认改 workspace remote。 |
| `chatgh repo sync [REPOSITORY]` | `sync_repo(repo, branch, remote, ff_only, token)` | 显式 `git fetch` + `git pull --ff-only`，默认当前 checkout / 当前分支。 |
| `chatgh repo edit [REPOSITORY]` | `edit_repo(repo, description, homepage, default_branch, visibility, accept_visibility_change_consequences, token)` | 小子集：description / homepage / default-branch / visibility；visibility 必须显式确认后果。 |
| `chatgh repo fork ...` | `fork_repo(...)` | 支持类官方 gh 位置参数、`--org`、`--fork-name` 和 ChatGH `--if-exists use`。 |
| `chatgh repo transfer ...` | `transfer_repo(repo, owner, team_ids, dry_run, accept_transfer_consequences, token)` | 调 GitHub Repository Transfer API；支持 `--dry-run`，真实远端迁移必须显式确认后果。 |
| `chatgh repo protection ...` | `inspect_repo_protection(...)` / `list_repo_protections(...)` | 检查分支保护和 repository rulesets。 |

### PR

| 命令 | Python API | 说明 |
|---|---|---|
| `chatgh pr list` | `list_prs(repo, state, limit, token)` | 列出 PR。 |
| `chatgh pr create ...` | `create_pr(...)` | 创建 PR，支持 body/body-file 和 JSON 输出。 |
| `chatgh pr view NUMBER` | `view_pr(repo, number, token)` | 查看 PR 基础信息、分支、mergeability 和时间戳。 |
| `chatgh pr comment NUMBER` | `comment_pr(repo, number, body, token)` | 发表评论。 |
| `chatgh pr edit NUMBER` | `edit_pr(repo, number, title, body, token)` | 编辑标题或正文。 |
| `chatgh pr checks NUMBER` | `check_pr(repo, number, token)` | 汇总 combined status、check run 和 workflow run。 |
| `chatgh pr merge NUMBER` | `merge_pr(repo, number, method, check, token)` | 合并前可执行安全门检查。 |
| `chatgh pr status` | `status_prs(repo, token)` | 汇总 open PR。 |
| `chatgh pr diff NUMBER` | `diff_pr(repo, number, token)` | 直接输出 GitHub diff 文本，用于评审。 |
| `chatgh pr close NUMBER` | `close_pr(repo, number, comment, delete_branch, token)` | 远端关闭 PR；`--delete-branch` 只记录请求，不默认删分支。 |
| `chatgh pr reopen NUMBER` | `reopen_pr(repo, number, token)` | 重新打开 PR。 |
| `chatgh pr review NUMBER` | `review_pr(repo, number, event, body, token)` | 支持 `--approve` / `--request-changes` / `--comment` 与 body / body-file。 |
| `chatgh pr ready NUMBER` | `ready_pr(repo, number, token)` | 将 draft PR 标记为 ready_for_review。 |
| `chatgh pr update-branch NUMBER` | `update_pr_branch(repo, number, expected_head_sha, token)` | 调 GitHub update-branch API。 |

### Actions 运行

| 命令 | Python API | 说明 |
|---|---|---|
| `chatgh run list` | `list_runs(repo, branch, status, event, limit, token)` | 支持 branch / status / event / limit 与 JSON。 |
| `chatgh run view RUN_ID` | `view_run(repo, run_id, token)` | 查看 workflow run 和 job。 |
| `chatgh run logs` | `run_logs(repo, job_id, tail, output, token)` | 查看 job 日志，支持 tail 和落盘。 |
| `chatgh run watch RUN_ID` | `watch_run(repo, run_id, interval, timeout, token)` | 必须有 timeout，避免长时间阻塞。 |
| `chatgh run rerun RUN_ID` | `rerun_run(repo, run_id, token)` | 远端变更，输出 run id / status。 |
| `chatgh run cancel RUN_ID` | `cancel_run(repo, run_id, token)` | 远端变更，输出 run id / status。 |
| `chatgh run download RUN_ID` | `download_run_artifacts(repo, run_id, name, output_dir, token)` | 下载并解压产物，默认显式 `--dir`/当前目录。 |

## 测试要求

每个新增接口至少覆盖：

1. Python API 与请求载荷行为。
2. CLI 参数映射、别名、错误语义、`--json-output`。
3. 令牌不泄漏。
4. 写操作的目标对象和安全边界。
5. 对本地 git 有副作用的命令必须测试不覆盖已有 remote/dirty checkout。

新增能力应先写失败测试，再实现最小代码，通过后再同步 README/docs。

## GitHub 项目 v2

`chatgh project` 不按官方 `gh project` 扁平树复刻。官方 `gh project` 只作为能力/语义参考；ChatGH 的 Project CLI 以自己的结构为准：`project list/view/create/edit/close/delete/copy` 管 Project 本体，`project item list/add/create/edit/archive/delete` 管 Project item，`project field list/create/delete` 管字段结构，`link/unlink/mark-template` 暂保留在顶层。ChatGH 不保留 `item-add` / `field-list` 这类 item / field 扁平兼容入口。运行时仍使用 ChatGH 自有鉴权、JSON 输出、安全门、ChatStyle 缺参补问和可导入 Python API。`project` 命令默认可在交互终端自动补问，`CHATARCH_AUTO_PROMPT=0/false/no/off` 关闭默认补问，`-i` 强制交互，`-I` 禁用交互；危险确认仍必须显式传 `--confirm`。`project item edit` 是字段值编辑入口，需要展开 text / number / date / single-select / iteration / clear 等不同形态。
