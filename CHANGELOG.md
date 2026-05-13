# Changelog

All notable changes to this project will be documented in this file.

本项目按日期记录更新；正式发版信息另见 `release.log`。

## 2026-05-14
- Migrated GitHub PR, CI checks, Actions run/job logs, repository permission, and token configuration helpers into `chatgh`.
- Added `chatgh pr`, `chatgh run`, `chatgh repo-perms`, and `chatgh set-token` CLI entry points.
- Added `chatgh.github` Python API modules and `GitHubClient` wrapper.
- Added mock CLI and code tests for command registration, interactive missing-parameter handling, JSON/output rendering, token/credential parsing, PR checks polling, merge blockers, and client wrapper behavior.
- Replaced the template `hello` command as the primary CLI surface with GitHub commands.
- Documented `chatgh` as the recommended entry point; `chattool gh` compatibility is handled in ChatTool as a thin wrapper.
- Initial ChatArch package scaffold.
