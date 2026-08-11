# 更新日志

本项目按日期记录更新；正式发版信息也维护在本文件。

## 2026-08-12
- 准备 `0.2.11` 补丁版本：补齐 MkDocs Material emoji renderer baseline、当前 docs dependency window、CI Python 3.10/3.11/3.12 matrix + installed `chatgh --version` / `chatgh --tree` smoke，以及 PyPI Trusted Publishing default-branch ancestry guard。
- 将 package Homepage 对齐到 ChatArch docs custom domain，并清理公开文档中的泛用仓库占位符与 scaffold wording。

## 2026-08-11
- 准备 `0.2.10` 补丁版本：新增顶层 `chatgh --tree`，从 Click 注册命令树生成当前命令面，包含 `--help`、`--version`、`--tree`、顶层资源组、嵌套子命令、参数/选项签名与一行用途说明。
- 为 `--tree` 增加 CLI 合约测试，锁住代表性命令面（`pr checks`、`repo transfer`、`project item edit`、`project field list`、`run logs`、`invitation accept`）并确保没有脚手架示例命令泄漏。
- 将发布 workflow 从 Twine secret 上传迁移为 PyPI Trusted Publisher / GitHub OIDC，并收紧 MkDocs docs extras 上界，保持严格构建稳定。

## 2026-07-19
- 新增 `chatgh repo transfer`：封装 GitHub Repository Transfer API，把仓库所有权迁移到目标 user/org；支持 `--dry-run` 先检查 source 权限与目标同名仓库，真正执行必须显式传 `--accept-transfer-consequences`，并支持转移到组织时重复传 `--team-id`；同步校对 CLI 树和官方 `gh` 对齐文档，并记录 GitHub Pages source 配置仍是未来 `repo pages` 能力缺口。
- 补充 ChatGH 文档规范：新增 `docs/interface-tree.md`，按 ChatTea 风格记录当前 CLI 树、目标方向、职责、CLI -> Python API 映射和测试契约；同步 `mkdocs.yml` 与 package metadata 到共享文档域名 `https://arch.gh.wzhecnu.cn/ChatGH/`，启用 `mkdocs-static-i18n` suffix 模式生成语言切换，并让 Preview Docs workflow 对齐 ChatTea 的 `https://arch.gh.wzhecnu.cn/<Repo>/dev/` 预览链接。
- 新增 `docs/agent-definition.md` / `docs/agent-definition.en.md`，定义 ChatGH 机器人的身份、manifest、触发流程、权限、工具、运行时、记忆、审批和审计模型。
- 新增 `docs/agent-task-bot-alignment.md`，调研官方 `gh agent-task`、`gh skill`、GitHub Apps、webhook 和机器人相关接口，并明确 ChatGH 后续代理任务和机器人命令面需要区分 GitHub 托管 Copilot / CAPI 与自托管事件到运行器桥接；补充官方 `gh` 可完成的常见机器人创建、评论、PR、status 和 webhook 操作清单，以及 Julia Registrator / TagBot 作为仓库原生机器人的实证案例。

## 2026-07-16
- 准备 `0.2.9` 补丁版本：为常用命令新增官方 `gh --json FIELDS` 风格的字段投影 JSON 输出，同时保留 ChatGH 既有 `--json-output` 完整 payload 输出。
- `--json` 支持常见官方字段别名映射，例如 `headRefName` / `baseRefName` / `mergeStateStatus`，便于复用官方 `gh` 命令片段；同时传 `--json` 与 `--json-output` 会明确报错。

## 2026-07-09
- 准备 `0.2.8` 补丁版本：新增 `chatgh invitation list/accept/decline`，用于查看并处理当前 authenticated user 的 GitHub repository invitations。
- `invitation` 命令对齐 GitHub REST API 的 `/user/repository_invitations` 能力，继续复用 ChatGH token resolution、JSON 输出和不打印 token 的安全边界；`accept` / `decline` 只按显式 invitation id 执行。

## 2026-07-03
- 开始 `chatgh project` GitHub Projects v2 命令面：按 ChatGH 自有结构设计 project command group：Project 本体命令保持顶层，item/field 作为 `project item ...` / `project field ...` 子树打开；不保留官方 `gh project` 的 item/field 扁平兼容入口。新增 Projects Python API、字段值编辑展开参数、JSON 输出和安全门测试。
- `chatgh project` 继续使用 ChatGH 自有 token resolution / ChatEnv / repo-local credential 规范，不依赖官方 `gh auth`。
- `chatgh project` 全命令接入 ChatStyle 缺参补问：默认终端可交互时自动补问，`CHATARCH_AUTO_PROMPT=0/false/no/off` 让机器/CI 缺参时报错，`-i` 强制交互，`-I` 禁用交互；危险确认仍必须显式 `--confirm`，不会由交互补问绕过。

## 2026-07-01
- 准备 `0.2.8` 补丁版本：发布 `chatgh repo clone`，用于首次 clone 时复用已解析 token 并写入 repo-local HTTPS auth header。
- 新增 `chatgh repo clone`：首次 clone 私有仓库时可直接复用已解析到的 token，在 `git clone` 阶段注入一次性 HTTPS auth header，并在 clone 完成后把 repo-local token 写入目标仓库 `.git/config`，避免“先 clone 再 set-token”的死锁。
- 为 `repo clone` 补充 CLI / command tests，并同步 README 与 docs/index 文档。

## 2026-06-24
- 准备 `0.2.7` 补丁版本：发布 `repo view/clone/sync/edit`、`pr status/diff/close/reopen/review/ready/update-branch`、`run list/watch/rerun/cancel/download`，并保持官方 `gh` 仅作接口参考、ChatGH 自有 CLI + Python API + JSON + safety gate 落地。
- 批量对齐官方 `gh` 常见接口：新增 `repo view/clone/sync/edit`、`pr status/diff/close/reopen/review/ready/update-branch`、`run list/watch/rerun/cancel/download`，并为这些命令补齐可 import 的 Python API、JSON 输出和 mock CLI 测试。
- 新增 `chatgh repo fork`：支持把 source 仓库 fork 到目标 user/org，可自定义目标仓库名、`--default-branch-only`、`--if-exists use` 与 JSON 输出；复用已有仓库时会校验 source，避免误认同名非匹配 fork。
- 准备 `0.2.6` 补丁版本：恢复 `chatgh pr create/comment/edit/merge` 公开 CLI surface，并把 ChatEnv 依赖窗口推进到 `chatenv>=0.2.0,<0.3.0` 以对齐已发布的 shared config runtime。
- 恢复 `chatgh pr create/comment/edit/merge` 公开 CLI surface，复用已存在的 GitHub helper 层；`merge` 默认 `--method squash` 与 `--check`，写操作支持 `--json-output` 和 body/message file。
- 为 ChatArch 内部依赖补版本窗口：`chatstyle>=0.1.0,<0.2.0`、`chatenv>=0.2.0,<0.3.0`，避免旧包自动解析到未来不兼容 minor。
- 文档同步移除“PR 写操作未公开”的过期说明。

## 2026-06-15
- 准备 `0.2.5` 补丁版本：为 ChatGH 注册 `chatenv.configs` provider，使安装后的 `chatenv list` / `chatenv cat -t gh` 能发现 GitHub typed env。
- 准备 `0.2.4` 补丁版本：发布 `chatgh repo protection` 默认分支保护 / rulesets 检查能力，并补充 owner inventory 的并发检查与表格/JSON 输出。
- 修复 `chatgh repo list/create` 缺少可恢复参数时被 Click required option 提前拦截、无法进入 chatstyle 交互补问的问题。
- 新增 `chatgh repo protection` 独立命令，用于查看单仓库或 owner inventory 的默认分支保护和 repository rulesets 状态；不把治理/规则字段塞进 `repo list` 默认表格。
- 准备 `0.2.3` 补丁版本：发布 repo-local `.git/config` HTTPS auth header 读写改造，确保 `chatgh set-token` 与 token resolution 不再依赖全局 git credential store。
- 改造 GitHub token 读写：`chatgh set-token` 不再写全局 `git credential` / `~/.git-credentials`，而是把 repo-local HTTPS `extraHeader` 写入当前仓库 `.git/config`；token 解析顺序同步改为显式 `--token`、repo-local `.git/config`、typed env `GITHUB_ACCESS_TOKEN`。
- 增强 `chatgh repo list`：默认输出仓库 table，支持 JSON 输出、limit、排序方向，以及按 updated/created/pushed/name/stars/open PR/open issue 排序；返回字段补充 visibility、stars、forks、open PRs、open issues、created/updated/pushed timestamps 等，便于查看 GitHub 用户或组织下的仓库概况。
- 新增 `chatgh repo list/create` 最小仓库管理入口；`repo create` 默认创建 private 仓库，并支持 `--if-exists use` 复用已有仓库。
- 准备 `0.2.2` 补丁版本：移除外露 `pr-legacy` 迁移入口，只保留 `chatgh pr` 与干净辅助命令作为公开 CLI surface。
- 移除外露 `pr-legacy` 迁移入口：`chatgh` 顶层只保留任务导向的 `pr`、`run`、`repo-perms`、`set-token`；旧 PR 兼容命令不再作为 CLI surface 维护，文档与测试同步收敛到 `chatgh pr ...`。
- 准备 `0.2.1` 补丁版本：`chatgh pr list/view/checks` 默认命令不再引用缺失的 generated API 模块，先复用已验证的 GitHub helper 层，保留 `chatgh pr view NUMBER` / `chatgh pr checks NUMBER` 命令面。
- 准备 `0.2.0` 版本：`chattool pypi probe chatgh` 确认 PyPI 最新 `chatgh` 为 `0.1.0` 后，按 minor bump 将包版本提升到 `0.2.0`。
- 为 `chatrest` generated API layer 补齐 `httpx` 运行依赖，修复 PR #2 CI 中 adapter/client 测试缺少 `httpx` 的失败。
- `chatgh pr view` 与 `chatgh pr checks` 的 generated-layer 用法改为 `chatgh pr view NUMBER` / `chatgh pr checks NUMBER`，贴近官方 `gh` 的位置参数习惯，不再暴露冗余 `--number`。
- 发版记录约定收口为只维护 `CHANGELOG.md`，不再要求额外发版记录文件。

## 2026-05-14
- 将 GitHub PR、CI 检查、Actions 运行和作业日志、仓库权限、令牌配置辅助能力迁移到 `chatgh`。
- 新增 `chatgh pr`、`chatgh run`、`chatgh repo-perms` 和 `chatgh set-token` CLI 入口。
- 新增 `chatgh.github` Python API 模块和 `GitHubClient` 封装。
- 新增 mock CLI 与代码测试，覆盖命令注册、交互式缺参补问、JSON / 人类可读输出、令牌和凭据解析、PR checks 轮询、合并阻断信息和 client wrapper 行为。
- 将模板示例命令替换为以 GitHub 命令为主的公开命令面。
- 文档明确推荐使用 `chatgh`；`chattool gh` 兼容由 ChatTool 侧薄封装处理。
- 初始化 ChatArch package scaffold。
