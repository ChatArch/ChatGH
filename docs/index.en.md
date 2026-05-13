# chatgh Docs

`chatgh` is the ChatArch GitHub CLI and Python API package. It contains PR, CI, Actions run/job log, repository permission, and token configuration helpers migrated from `chattool gh`.

## CLI Entry Points

```bash
chatgh --help
chatgh pr --help
chatgh run --help
chatgh repo-perms --help
chatgh set-token --help
```

## Common Workflows

```bash
chatgh pr create --repo OWNER/REPO --base main --head feature --title "Title" --body "Body"
chatgh pr view --repo OWNER/REPO --number 123
chatgh pr checks --repo OWNER/REPO --number 123 --wait --interval 15 --timeout 600
chatgh run view --repo OWNER/REPO --run-id 123456789
chatgh run logs --repo OWNER/REPO --job-id 987654321 --tail 200
chatgh set-token --token "$GITHUB_ACCESS_TOKEN" --save-env
```

If `chattool gh` still exists, treat it as a ChatTool compatibility entry point. New scripts and docs should use `chatgh`.
