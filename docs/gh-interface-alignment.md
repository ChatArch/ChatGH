# ChatGH 与官方 `gh` 接口对齐规范

ChatGH 是 ChatArch / Arch 系列工具的 GitHub 操作基础层。它应该让熟悉 GitHub CLI `gh` 的人和模型能低成本迁移，同时保留 ChatArch 自有的鉴权、安全门、JSON 输出和 Python API 复用能力。

## 基本原则

1. **官方 `gh` 先作接口参考**：新增常见 GitHub 能力前，先查看对应的官方 `gh <group> <command> --help` 和 GitHub REST/API 文档。
2. **不把官方 `gh` 当运行依赖**：官方 `gh` 只用于命令形态、参数命名、帮助文本和用户习惯参考；真实操作仍由 ChatGH 自己的 Python API / REST 实现完成。
3. **如果官方已有能力，优先借鉴形态**：命令名、位置参数、常见长参/短参应尽量兼容；如果与 ChatGH 语义冲突，要保留 ChatGH 更安全、更自动化友好的行为并在文档里说明差异。
4. **如果官方没有能力，再设计 ChatGH-native surface**：新设计也要保持命名清晰、JSON 稳定、可测试、可被 Python 调用。
5. **CLI + Python API 双落地**：CLI 是人和模型调用/review 的界面；背后的函数必须是可 import 的 Python API，供 ChatArch 自动化和其他 Arch 工具复用。

## 代码组织

新增接口应遵循当前分层：

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

规则：

- CLI 层只做参数解析、交互补问、输出格式选择。
- 业务流程函数放在 `chatgh.github.commands` 或更合适的 service module。
- GitHub API 细节放在 `chatgh.github.requests` / `api.py`。
- 人类输出与 JSON payload 分离：Python 函数返回 payload，CLI 只决定 table/summary 或 `--json-output`。
- 每个新增 CLI 应有同名或近似 Python API，例如 `chatgh repo view` 对应 `view_repo(...)`。

## CLI 兼容策略

- 官方有位置参数时，ChatGH 应考虑兼容位置参数。
- 官方常见短参/长参若无冲突，应提供 alias。例如 `-R/--repo`、`--org`、`--fork-name`。
- 保留 ChatGH 自有扩展：`--json-output`、`--token`、repo-local auth / ChatEnv token resolution、`--if-exists use`、PR merge safety gate。
- 对本地 git 有副作用的行为默认保持克制。`clone`、`remote`、`sync` 等能力必须有明确参数、清晰输出和测试，不能默认覆盖已有 checkout/remote。

## `repo fork` 对齐示例

官方 `gh repo fork` 的常见形态是位置参数 + `--org` / `--fork-name`。ChatGH 同时支持官方形态和显式自动化形态：

```bash
# gh-like, convenient for humans and model callers familiar with gh
chatgh repo fork Wei-Shaw/claude-relay-service --org ChatArch --fork-name claude-relay-service

# ChatGH explicit, convenient for automation and idempotent workflows
chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch --name claude-relay-service --if-exists use --json-output
```

映射：

- positional `REPO` -> `source`
- `--org` -> `owner` for organization targets
- `--fork-name` -> `name`
- `--json-output` and `--if-exists use` are ChatGH automation extensions

## 批量迁移优先级

### Phase 1：repo 命令族

- `repo view [REPO] [-R/--repo REPO] [--json-output]`
- `repo fork [REPO] --org/--owner ... --fork-name/--name ...`
- `repo clone REPO [DIR]`，默认不破坏已有 checkout/remote
- `repo sync [REPO]`，先明确 API/git 边界
- `repo edit` 小子集：description/homepage/default-branch/visibility

### Phase 2：PR lifecycle

当前已有 `create/list/view/comment/edit/checks/merge`。后续优先补：

- `pr status`
- `pr diff`
- `pr close`
- `pr reopen`
- `pr review`
- `pr ready`
- `pr update-branch`

`pr merge` 继续保持安全门；merge 命令是真实远端 mutation，不得当 dry-run 使用。

### Phase 3：Actions run

当前已有 `run view` / `run logs`。后续优先补：

- `run list`
- `run watch`，必须有 timeout
- `run rerun`
- `run cancel`
- `run download`

## 测试要求

每个新增接口至少覆盖：

1. Python API / request payload 行为。
2. CLI 参数映射、alias、错误语义、`--json-output`。
3. token 不泄漏。
4. 写操作的目标对象和安全边界。
5. 对本地 git 有副作用的命令必须测试不覆盖已有 remote/dirty checkout。

新增能力应先写失败测试，再实现最小代码，通过后再同步 README/docs。