# chatgh 文档

`chatgh` 是 ChatArch 的 GitHub CLI 与 Python API 包，承载从 `chattool gh` 迁移出的 PR、CI、Actions run/job logs、仓库权限和 token 配置能力。新脚本和文档应直接使用 `chatgh`；`chattool gh` 只作为 ChatTool 侧兼容入口。

## 安装

```bash
pip install chatgh
# 开发态
pip install -e ".[dev]"
```

## 配置模型

默认行为：

- `repo`：优先使用显式 `--repo owner/repo`，未传时从当前 git remote 推断。
- `token`：优先使用显式 `--token`，其次读取当前仓库 `.git/config` 中 repo-local HTTPS auth header，再回退 typed env 里的 `GITHUB_ACCESS_TOKEN`。
- 输出：默认是人类可读格式；支持 `--json-output` 的命令会输出稳定 JSON，适合脚本消费。

### Token 来源

Token 解析顺序稳定为：

1. 显式 `--token`。
2. 当前仓库 `.git/config` 中的 repo-local HTTPS auth header，路径为规范化后的 `https://github.com/owner/repo.git`。
3. typed env 中的 `GITHUB_ACCESS_TOKEN`。

可以用 `chatenv` 查看或配置 typed env：

```bash
chatenv init -t gh
chatenv cat -t gh
```

安装 `chatgh` 后，它会通过 `chatenv.configs` entry point 注册 `GitHubConfig`，所以 `chatenv list` 会出现 `[GitHub]` 分组，`-t gh` / `-t github` 可以解析到同一份 GitHub typed env。

`ghp_xxx` / `github_pat_xxx` 都是 GitHub Personal Access Token。通常 clone/fetch/push 至少需要 contents 读写权限；PR 评论、合并和 Actions 读取按仓库策略补充对应权限。

### 仓库推断

未传 `--repo` 时，`chatgh` 会检查当前仓库 remote，并优先使用 `origin`，再尝试其它 remote。支持：

- `https://github.com/octocat/Hello-World.git`
- `https://github.com/octocat/Hello-World`
- `git@github.com:octocat/Hello-World.git`
- `ssh://git@github.com/octocat/Hello-World.git`

写入 repo-local HTTPS auth header 时，path 会规范化为 `https://github.com/octocat/Hello-World.git`。

## CLI 入口

```bash
chatgh --help
chatgh pr --help
chatgh repo --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

命令树：

- `chatgh pr list`：generated-layer PR 列表。
- `chatgh pr view NUMBER`：generated-layer PR 详情。
- `chatgh pr checks NUMBER`：generated-layer PR head commit check runs。
- `chatgh repo list`：列出 user/org 下的仓库；默认 table，支持 `--json-output`、`--limit`、`--sort updated|created|pushed|name|stars|open-prs|open-issues`、`--direction asc|desc`，字段包含 visibility、stars、open PRs、open issues、created/updated time 等。
- `chatgh repo create`：创建仓库；默认 private，可用 `--public` 显式创建公开仓库。
- `chatgh repo fork`：把 source 仓库 fork 到目标 user/org，兼容 `gh` 风格位置参数、`--org`、`--fork-name`，并保留 ChatGH 显式 `--source`、`--owner`、`--name`、`--default-branch-only`、`--if-exists use` 和 JSON 输出。
- `chatgh repo protection`：查看单个仓库或 owner 下仓库的默认分支保护与 repository rulesets；治理/规则审计不挤进 `repo list` 默认表格。
- 当前公开 `chatgh pr` 命令面包含 `list/create/view/comment/edit/checks/merge`；写操作复用 ChatGH token resolution，且不会打印 token。
- `chatgh run view`：查看 workflow run 和 jobs。
- `chatgh run logs`：查看 job 日志，支持 tail 和落盘。
- `chatgh repo-perms`：查看 token 权限和派生 capabilities。
- `chatgh set-token`：为当前 GitHub 仓库配置 repo 级 HTTPS token。

## 常用流程

### Repo view / clone / sync / edit

```bash
chatgh repo view ChatArch/ChatGH --json-output
chatgh repo clone ChatArch/ChatGH ./ChatGH-copy
chatgh repo sync --repo ChatArch/ChatGH --branch master --remote origin --json-output
chatgh repo edit ChatArch/ChatGH --description "GitHub helpers" --json-output
chatgh repo edit ChatArch/ChatGH --visibility private --accept-visibility-change-consequences --json-output
```

`repo clone` 会拒绝覆盖已有非空目录；`repo sync` 默认使用 `git pull --ff-only`。`repo edit` 当前只支持 description、homepage、default-branch 和 visibility 小子集；设置 `--visibility` 时必须显式传 `--accept-visibility-change-consequences`。

### PR lifecycle / review

```bash
chatgh pr status --repo ChatArch/ChatGH --json-output
chatgh pr diff 14 --repo ChatArch/ChatGH
chatgh pr close 14 --repo ChatArch/ChatGH --comment "Superseded" --json-output
chatgh pr reopen 14 --repo ChatArch/ChatGH --json-output
chatgh pr review 14 --repo ChatArch/ChatGH --approve --body-file review.md
chatgh pr ready 14 --repo ChatArch/ChatGH --json-output
chatgh pr update-branch 14 --repo ChatArch/ChatGH --expected-head-sha SHA --json-output
```

`close/reopen/review/ready/update-branch` 都是远端写操作；执行前应确认目标 PR。

### 创建 PR

```bash
chatgh pr create --repo octocat/Hello-World --base main --head rex/feature --title "Add feature" --body-file pr-body.md
chatgh pr create --repo octocat/Hello-World --base main --head rex/feature --title "Add feature" --body "Short body" --json-output
```

`pr create` 会使用当前 ChatGH token resolution 逻辑，不会打印 token。缺少 `base/head/title` 时，可在交互终端自动补问；非交互可用 `-I` 明确失败。

### 查看 PR

```bash
chatgh pr list --repo octocat/Hello-World --state open --limit 20
chatgh pr view 123 --repo octocat/Hello-World
chatgh pr view 123 --repo octocat/Hello-World --json-output
```

`pr view` 输出会包含：

- PR number、title、state、author、URL。
- base/head branch。
- `mergeable` 和 `mergeable_state`。
- created/updated/merged timestamps。

### 查看 CI

```bash
chatgh pr checks 123 --repo octocat/Hello-World
chatgh pr checks 123 --repo octocat/Hello-World --json-output
```

`pr checks` 按 PR head commit 汇总三层信息：

- combined status
- check runs
- workflow runs

当前公开 CLI 不提供 `--wait` / `--interval` / `--timeout` 参数；需要等待终态时，在外层流程中轮询 `chatgh pr checks`。

如果 GitHub token 无权读取 check-runs API，命令会把 check-runs 错误放进 payload，同时仍尽量展示 combined status 和 workflow runs。

### 查看 Actions run 和 job logs

```bash
chatgh run list --repo octocat/Hello-World --limit 20
chatgh run watch 123456789 --repo octocat/Hello-World --timeout 600
chatgh run rerun 123456789 --repo octocat/Hello-World --json-output
chatgh run cancel 123456789 --repo octocat/Hello-World --json-output
chatgh run download 123456789 --repo octocat/Hello-World --dir ./artifacts

chatgh run view --repo octocat/Hello-World --run-id 123456789
chatgh run view --repo octocat/Hello-World --run-id 123456789 --json-output

chatgh run logs --repo octocat/Hello-World --job-id 987654321
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 0
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 200 --output job.log
```

`run logs` 默认只输出尾部日志；`--tail 0` 输出完整日志；`--output` 会把完整日志写入文件，终端仍显示 tail。

### 评论、合并和编辑 PR

```bash
chatgh pr comment 123 --repo octocat/Hello-World --body-file review-note.md
chatgh pr edit 123 --repo octocat/Hello-World --title "New title" --body-file pr-body.md
chatgh pr merge 123 --repo octocat/Hello-World --method squash --check
```

`pr merge` 默认使用 `--method squash` 和 `--check`，会在合并前读取 PR checks 并拒绝非绿色状态。合并仍然是高风险远程 mutation，实际执行前应先确认 PR 状态和用户授权。

### Fork 仓库

```bash
# gh-like 形态
chatgh repo fork octocat/Hello-World --org ChatArch
chatgh repo fork octocat/Hello-World --org ChatArch --fork-name hello-world-copy --default-branch-only

# ChatGH 显式/自动化形态
chatgh repo fork --source octocat/Hello-World --owner ChatArch
chatgh repo fork --source octocat/Hello-World --owner ChatArch --name hello-world-copy --default-branch-only
chatgh repo fork --source octocat/Hello-World --owner ChatArch --if-exists use --json-output
```

`repo fork` 通过 GitHub Fork API 创建目标仓库；目标仓库名默认沿用 source repo 名。它兼容官方 `gh repo fork [<repository>] --org ... --fork-name ...` 的常见形态，同时保留 ChatGH 的显式 `--source/--owner/--name` 和 `--json-output/--if-exists use` 自动化扩展。目标为 organization 时会传递 GitHub API 的 `organization` 字段；目标为 user account 时，`--owner` 必须匹配当前认证用户。`--if-exists use` 只会复用已存在且匹配 source 的 fork，避免把同名非匹配仓库误当成功结果。

### 查看仓库保护规则

```bash
chatgh repo protection --repo octocat/Hello-World
chatgh repo protection --repo octocat/Hello-World --json-output
chatgh repo protection --owner octocat --limit 50 --jobs 8
chatgh repo protection --owner octocat --limit 50 --jobs 8 --json-output
```

`repo protection` 会展示默认分支、是否 protected、classic branch protection 细节（例如是否要求 PR、review 数量、是否允许 force push / deletion），以及 GitHub 可读取时的 repository ruleset 摘要。部分 private 仓库可能因为 GitHub plan/visibility 限制读取 rulesets 返回错误；命令会在 JSON 里保留该错误，同时尽量展示 branch protection 状态。owner inventory 模式会先列仓库，再用 `--jobs` 并发检查每个仓库，输出顺序保持稳定。

### 配置和检查 token

```bash
chatgh repo-perms --repo octocat/Hello-World --json-output
chatgh repo-perms --repo octocat/Hello-World --full-json

chatgh set-token --token "$GITHUB_ACCESS_TOKEN"
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

`repo-perms` 会展示：

- token 来源和 mask 后的 token。
- GitHub 返回的 `permissions`。
- 派生 capabilities：`can_read_pr`、`can_comment_pr`、`can_merge_pr`、`can_view_checks`、`can_view_actions`。

`set-token` 只在当前目录能识别 GitHub remote 时生效。默认只写入当前仓库自己的 `.git/config`：

```ini
[http "https://github.com/octocat/Hello-World.git"]
    extraHeader = Authorization: Basic <base64(x-access-token:TOKEN)>
```

不要把 token 写进 remote URL，也不要把 raw `extraHeader` 输出到日志。传 `--save-env` 时会同步写入 typed env 的 `GITHUB_ACCESS_TOKEN`。

## 交互模式

所有缺少可恢复关键参数的命令都走 `chatstyle`：

- 默认模式：终端可交互且缺参时自动补问。
- `-i/--interactive`：强制进入补问流程。
- `-I/--no-interactive`：完全禁用补问，缺参时直接报错。

token 类输入使用 password prompt，不会明文回显。

## 推荐的 PR/CI 工作流

在创建 PR、汇报“CI 是否通过”或准备 merge 前，先同步最新 base：

```bash
git fetch origin main
```

然后确认：

- `chatgh pr view` / `chatgh pr checks` 显示 `mergeable` 不是 `False`，`mergeable_state` 不是 `dirty`。
- 本地基于最新 base 做过 merge 或 rebase 演练，并在该结果上跑过最相关测试。
- CI 需要终态时，在外层流程中轮询 `chatgh pr checks`，不要只看一次快照。

## Python API

```python
from chatgh.github.client import GitHubClient

client = GitHubClient(user_name="octocat", token="ghp_...")
prs = client.get_pull_requests("Hello-World")
view = client.get_pr_view("octocat/Hello-World", 1)
checks = client.get_pr_checks("octocat/Hello-World", 1)
```

底层模块也可按需导入：

- `chatgh.github.api`：token、仓库解析、git credential 和 REST 请求基础能力。
- `chatgh.github.commands`：CLI 使用的业务流程函数。
- `chatgh.github.requests`：PR/checks/actions payload 构造。
- `chatgh.github.render`：人类可读输出、merge blocker 和 tail helper。

## 与 ChatTool 的关系

`chattool gh` 的长期实现已迁移到 `chatgh`。ChatTool 可以保留薄 wrapper 兼容旧命令，但不应继续维护一份 forked GitHub 实现。ChatTool 内涉及 GitHub token/remote 的辅助逻辑也应导入 `chatgh.github.api`。

## 开发参考

扩展 `chatgh` 时应先看项目内接口规范：`docs/gh-interface-alignment.md`。常见 GitHub 能力要先参考官方 GitHub CLI `gh` 的命令形态和帮助文本；如果官方已有能力，优先兼容其命名、位置参数和常见 alias，再结合 ChatGH 的鉴权、JSON、安全门和 Python API 落地；如果官方没有，才设计 ChatGH-native surface。官方 `gh` 只作接口参考，不作为运行依赖、CI/ops fallback 或真实操作路径。

扩展时也要查官方 API 文档：

- GitHub REST API: https://docs.github.com/en/rest
- Pull requests API: https://docs.github.com/en/rest/pulls/pulls
- Check runs API: https://docs.github.com/en/rest/checks/runs
- Workflow runs API: https://docs.github.com/en/rest/actions/workflow-runs
- Workflow jobs API: https://docs.github.com/en/rest/actions/workflow-jobs
- Commit statuses API: https://docs.github.com/en/rest/commits/statuses
- PyGithub: https://pygithub.readthedocs.io/

本地验证：

```bash
python -m pytest -q
python -m build
mkdocs build --strict
```

默认测试使用 mock/fake payload 和临时目录，不调用真实 GitHub API，也不会污染真实 git credential 或 env 配置。
