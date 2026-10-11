# Token 更新、清理与批量维护

| 目的 | 命令 | 影响范围 |
|---|---|---|
| 从当前配置刷新仓库旧值 | `chatgh set-token --from-config` | 当前仓库的一个 Git token 配置项 |
| 删除之前设置的仓库值 | `chatgh unset-token` | 与 set 相同目标、相同配置键 |
| 按维护文件更新多个仓库 | `chatgh set-token --from-config --file repositories.json` | 文件中预检通过的仓库目标 |

## 设置与清理是同一项配置的对称动作

`set-token` 写入或更新仓库 Git 配置中的 HTTPS token。`unset-token` 使用同一个 origin 优先的 GitHub remote 选择规则，删除 set 写入的精确配置项。当前分支跟踪其它 upstream 不会让 unset 清理另一个 remote。

unset 不解码、判断或验证 token；过期、损坏或者空的已配置值都按同一配置项移除。它不读取默认 token、不扫描其它配置项，也不处理其它仓库。没有该项时成功返回 `removed_count=0`。

```bash
chatgh set-token --from-config
chatgh unset-token
```

这两个命令操作仓库 Git 配置，不是 GitHub 令牌吊销接口。原有 API 与传输的令牌来源顺序不变：显式值、匹配仓库配置、当前类型化配置。

## 从配置刷新值

`--from-config` 读取当前 GitHub 类型化配置，不复用仓库里的旧 token，因此适合默认配置已经更新后的刷新。它与 `--token` 互斥；未使用该参数时，原有交互和令牌选择行为保留。

```bash
chatgh set-token --from-config --dry-run --json-output
chatgh set-token --from-config --json-output
```

令牌及编码授权头不会进入 Git 子进程参数或结果输出。POSIX 上仓库配置文件在写入秘密前收紧为用户私有权限；其它 Git 配置值保留。

## JSON/YAML 仓库维护文件

文件只保存目标，不保存 token。相对路径以文件所在目录为基准；`repo` 可选，用于确认该目录的 remote 仍指向预期仓库。请替换为真实仓库路径。

```json
{
  "version": 1,
  "repositories": [
    {"path": "./first-repo", "repo": "example/first-repo"},
    {"path": "./second-repo"}
  ]
}
```

等价的 YAML：

```yaml
version: 1
repositories:
  - path: ./first-repo
    repo: example/first-repo
  - path: ./second-repo
```

先预览，再执行：

```bash
chatgh set-token --from-config --file repositories.json --dry-run --json-output
chatgh set-token --from-config --file repositories.json --json-output
chatgh set-token --from-config --file repositories.yaml --json-output
```

批量模式必须明确使用 `--from-config` 或 `--token`，不能与 `--save-env` 混用。所有目标会在读取令牌和写入前完成预检；无效路径、预期仓库不匹配或不支持的字段会令整次预检失败。共享同一 Git config 和配置键的 worktree/重复路径只更新一次。

写入阶段逐项执行并回读。结果包含 `requested`、`total`、`duplicates_skipped`、`configured`、`failed` 和逐项状态；任何写入失败都会返回非零退出状态，不会把部分成功宣称为全部成功。预览模式不写入配置。

## Python 接口

```python
from chatgh.github.commands import set_token
from chatgh.github.transport import unset_token

plan = set_token(None, False, from_config=True,
                 repo_file="repositories.json", dry_run=True)
result = set_token(None, False, from_config=True,
                   repo_file="repositories.json")
removed = unset_token(cwd="./first-repo")
```

维护文件应留在操作者的私有配置目录；不要把实际机器路径或凭据提交到公共仓库。unset 没有广泛清理模式，其他已发布命令的功能不变。
