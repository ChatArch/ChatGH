# Changelog

All notable changes to this project will be documented in this file.

本项目按日期记录更新；正式发版信息也维护在本文件。

## 2026-06-15
- 补充 `chatenv.configs` entry point，让 `gh`/`github` typed env schema 随独立 `chatgh` 注册；这是 ChatTool 移除内置 GitHubConfig 后的归属调整，当前仅准备分支，不发版。
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
