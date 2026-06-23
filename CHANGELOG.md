# Changelog

All notable changes to this project will be documented in this file.

本项目按日期记录更新；正式发版信息也维护在本文件。

## 2026-06-24
- 恢复 `chatgh pr create/comment/edit/merge` 公开 CLI surface，复用已存在的 GitHub helper 层；`merge` 默认 `--method squash` 与 `--check`，写操作支持 `--json-output` 和 body/message file。
- 为 ChatArch 内部依赖补版本窗口：`chatstyle>=0.1.0,<0.2.0`、`chatenv>=0.1.1,<0.2.0`，避免旧包自动解析到未来不兼容 minor。
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
- Migrated GitHub PR, CI checks, Actions run/job logs, repository permission, and token configuration helpers into `chatgh`.
- Added `chatgh pr`, `chatgh run`, `chatgh repo-perms`, and `chatgh set-token` CLI entry points.
- Added `chatgh.github` Python API modules and `GitHubClient` wrapper.
- Added mock CLI and code tests for command registration, interactive missing-parameter handling, JSON/output rendering, token/credential parsing, PR checks polling, merge blockers, and client wrapper behavior.
- Replaced the template `hello` command as the primary CLI surface with GitHub commands.
- Documented `chatgh` as the recommended entry point; `chattool gh` compatibility is handled in ChatTool as a thin wrapper.
- Initial ChatArch package scaffold.
