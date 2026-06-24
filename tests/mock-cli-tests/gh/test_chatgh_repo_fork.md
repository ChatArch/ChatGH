# test_chatgh_repo_fork

## 目标

验证 `chatgh repo fork` 作为可复用仓库管理能力存在，能把指定 source 仓库 fork 到目标 user/org，并支持复用已存在的匹配 fork。

## Cases

### CLI 默认目标仓库名

初始环境：mock `chatgh.github.cli.fork_repo`，不访问 GitHub。

预期过程和结果：
1. 执行 `chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch`。
2. CLI 将 `source=Wei-Shaw/claude-relay-service`、`owner=ChatArch`、`name=None`、`default_branch_only=False`、`if_exists=error` 传给命令层。
3. 普通输出展示 fork 结果和 URL。

参考执行脚本：

```sh
chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch
```

### CLI JSON 输出和复用已有 fork

初始环境：mock `chatgh.github.cli.fork_repo`，返回 `created=false`。

预期过程和结果：
1. 执行 `chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch --if-exists use --json-output`。
2. CLI 输出 JSON，包含 `full_name`、`source_full_name`、`created=false`。

参考执行脚本：

```sh
chatgh repo fork --source Wei-Shaw/claude-relay-service --owner ChatArch --if-exists use --json-output
```

### 请求层复用匹配已有 fork

初始环境：mock `requests.get` 返回一个已存在的 fork，其 `source.full_name` 与 source 一致。

预期过程和结果：
1. 调用 `post_repo_fork(..., if_exists="use")`。
2. 不发送 POST；返回已存在仓库 payload，且 `created=false`。

参考执行脚本：

```sh
pytest tests/mock-cli-tests/gh/test_chatgh_basic.py -q
```
