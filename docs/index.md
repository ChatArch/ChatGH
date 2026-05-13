# chatgh 文档

`chatgh` 是 ChatArch 的 GitHub CLI 与 Python API 承载项目，包含从 `chattool gh` 迁移而来的 PR、CI、Actions run/job logs、repo permissions 和 token 配置能力。

## 命令入口

```bash
chatgh --help
chatgh pr --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

## 常用流程

```bash
chatgh pr create --repo OWNER/REPO --base main --head feature --title "Title" --body "Body"
chatgh pr view --repo OWNER/REPO --number 123
chatgh pr checks --repo OWNER/REPO --number 123 --wait --interval 15 --timeout 600
chatgh run view --repo OWNER/REPO --run-id 123456789
chatgh run logs --repo OWNER/REPO --job-id 987654321 --tail 200
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

`chattool gh` 如仍存在，应视为 ChatTool 侧兼容入口；推荐新脚本和文档迁移到 `chatgh`。

## 本地预览

```bash
pip install -e ".[docs]"
mkdocs serve
```

英文版见：[index.en.md](index.en.md)。
