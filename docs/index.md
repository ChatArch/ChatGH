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
- `token`：优先使用显式 `--token`，其次读取当前仓库对应的 git credential，再回退 typed env 里的 `GITHUB_ACCESS_TOKEN`。
- 输出：默认是人类可读格式；支持 `--json-output` 的命令会输出稳定 JSON，适合脚本消费。

### Token 来源

Token 解析顺序稳定为：

1. 显式 `--token`。
2. repo-scoped git credential，路径为规范化后的 `owner/repo`，不带 `.git` 后缀。
3. typed env 中的 `GITHUB_ACCESS_TOKEN`。

可以用 `chatenv` 查看或配置 typed env：

```bash
chatenv init -t gh
chatenv cat -t gh
```

`ghp_xxx` / `github_pat_xxx` 都是 GitHub Personal Access Token。通常 clone/fetch/push 至少需要 contents 读写权限；PR 评论、合并和 Actions 读取按仓库策略补充对应权限。

### 仓库推断

未传 `--repo` 时，`chatgh` 会检查当前仓库 remote，并优先使用 `origin`，再尝试其它 remote。支持：

- `https://github.com/octocat/Hello-World.git`
- `https://github.com/octocat/Hello-World`
- `git@github.com:octocat/Hello-World.git`
- `ssh://git@github.com/octocat/Hello-World.git`

写入 repo-scoped credential 时，path 会规范化为 `octocat/Hello-World`。

## CLI 入口

```bash
chatgh --help
chatgh pr --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

命令树：

- `chatgh pr list`：generated-layer PR 列表。
- `chatgh pr view NUMBER`：generated-layer PR 详情。
- `chatgh pr checks NUMBER`：generated-layer PR head commit check runs。
- `chatgh pr create/comment/merge/edit`：PR 创建、评论、合并和编辑操作。
- `chatgh run view`：查看 workflow run 和 jobs。
- `chatgh run logs`：查看 job 日志，支持 tail 和落盘。
- `chatgh repo-perms`：查看 token 权限和派生 capabilities。
- `chatgh set-token`：为当前 GitHub 仓库配置 repo 级 HTTPS token。

## 常用流程

### 创建 PR

优先使用 `--body-file`，避免 shell 转义破坏 Markdown：

```bash
cat > /tmp/pr_body.md <<'EOF'
## Summary
- migrate GitHub helpers to chatgh

## Testing
- python -m pytest -q
EOF

chatgh pr create \
  --repo octocat/Hello-World \
  --base main \
  --head feature-branch \
  --title "feat: migrate github helpers" \
  --body-file /tmp/pr_body.md
```

缺少 `base` / `head` / `title` 且终端可交互时，命令会自动补问；显式 `-I` 会禁用补问。

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

### 查看和等待 CI

```bash
chatgh pr checks 123 --repo octocat/Hello-World
chatgh pr checks --repo octocat/Hello-World --number 123 --wait
chatgh pr checks --repo octocat/Hello-World --number 123 --wait --interval 10 --timeout 600
chatgh pr checks 123 --repo octocat/Hello-World --json-output
```

`pr checks` 按 PR head commit 汇总三层信息：

- combined status
- check runs
- workflow runs

`--wait` 会持续轮询直到 statuses、check runs 和 workflow runs 都结束：

- 默认不设超时，会一直等。
- `--interval <seconds>` 控制轮询间隔。
- 只有显式传 `--timeout <seconds>` 时才会超时报错。

如果 GitHub token 无权读取 check-runs API，命令会把 check-runs 错误放进 payload，同时仍尽量展示 combined status 和 workflow runs。

### 查看 Actions run 和 job logs

```bash
chatgh run view --repo octocat/Hello-World --run-id 123456789
chatgh run view --repo octocat/Hello-World --run-id 123456789 --json-output

chatgh run logs --repo octocat/Hello-World --job-id 987654321
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 0
chatgh run logs --repo octocat/Hello-World --job-id 987654321 --tail 200 --output job.log
```

`run logs` 默认只输出尾部日志；`--tail 0` 输出完整日志；`--output` 会把完整日志写入文件，终端仍显示 tail。

### 评论、合并和编辑 PR

```bash
chatgh pr comment --repo octocat/Hello-World --number 123 --body "Looks good"

chatgh pr merge --repo octocat/Hello-World --number 123 --method squash
chatgh pr merge --repo octocat/Hello-World --number 123 --method squash --check

chatgh pr edit --repo octocat/Hello-World --number 123 --title "New title"
chatgh pr edit --repo octocat/Hello-World --number 123 --body-file /tmp/pr_body.md
chatgh pr edit --repo octocat/Hello-World --number 123 --state closed
chatgh pr edit --repo octocat/Hello-World --number 123 --base main
```

`pr merge --check` 会在合并前拒绝以下情况：

- PR 当前 `mergeable=False`。
- `mergeable_state` 为 `dirty`、`blocked`、`behind`、`draft` 或 `unknown`。
- combined status、check runs 或 workflow runs 存在失败、取消或未完成项。

不带 `--check` 时，命令保持直接调用 GitHub merge API 的行为。

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

`set-token` 只在当前目录能识别 GitHub remote 时生效。默认只写入 repo-scoped git credential；传 `--save-env` 时会同步写入 typed env 的 `GITHUB_ACCESS_TOKEN`。

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
- CI 需要终态时用 `chatgh pr checks --wait`，不要只看一次快照。

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

扩展 `chatgh` 时优先查官方文档：

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
