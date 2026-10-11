# Token updates, cleanup, and batch maintenance

| Goal | Command | Scope |
|---|---|---|
| Refresh the repository value from current configuration | `chatgh set-token --from-config` | One repository Git token item |
| Remove the previously configured value | `chatgh unset-token` | The same target and key as set |
| Update repositories from a maintenance file | `chatgh set-token --from-config --file repositories.json` | Validated targets in that file |

## Set and unset operate on the same configuration item

`set-token` writes or updates the repository HTTPS token configuration. `unset-token` uses the same origin-first GitHub remote selection and deletes that exact item. Tracking a different upstream does not make unset remove another remote's value.

Unset does not decode, inspect, or validate a token. Expired, malformed, or empty values are removed as the same configuration item. It does not resolve a default credential, scan other keys, or operate on other repositories. An absent item succeeds with `removed_count=0`.

```bash
chatgh set-token --from-config
chatgh unset-token
```

These commands modify repository Git configuration, not GitHub token revocation. Existing API and transport precedence remains explicit value, matching repository configuration, then current typed configuration.

## Refresh from configuration

`--from-config` reads the current typed GitHub configuration rather than reusing an old repository token. It is mutually exclusive with `--token`. Without the flag, the existing interactive and selection behavior remains available.

```bash
chatgh set-token --from-config --dry-run --json-output
chatgh set-token --from-config --json-output
```

Neither a token nor its encoded authorization header enters Git child-process arguments or result output. On POSIX, the repository configuration is made user-private before secret writes, while unrelated Git values remain unchanged.

## JSON/YAML repository maintenance file

The file contains targets, never credentials. Relative paths are resolved from the manifest directory. Optional `repo` asserts that the checkout still points to the expected repository. Replace these paths with real checkouts.

```json
{
  "version": 1,
  "repositories": [
    {"path": "./first-repo", "repo": "example/first-repo"},
    {"path": "./second-repo"}
  ]
}
```

Equivalent YAML:

```yaml
version: 1
repositories:
  - path: ./first-repo
    repo: example/first-repo
  - path: ./second-repo
```

Preview, then apply:

```bash
chatgh set-token --from-config --file repositories.json --dry-run --json-output
chatgh set-token --from-config --file repositories.json --json-output
chatgh set-token --from-config --file repositories.yaml --json-output
```

Batch mode requires `--from-config` or an explicit `--token`, and cannot use `--save-env`. Every target is preflighted before token resolution or writes; invalid paths, mismatched repository assertions, and unsupported fields fail the whole preflight. Duplicate paths or worktrees sharing the same Git config and key are updated once.

Apply processes targets individually and reads their values back. Results include `requested`, `total`, `duplicates_skipped`, `configured`, `failed`, and per-target status. Any write failure gives a nonzero exit status; partial success is never reported as complete success. Dry runs do not write configuration.

## Python API

```python
from chatgh.github.commands import set_token
from chatgh.github.transport import unset_token

plan = set_token(None, False, from_config=True,
                 repo_file="repositories.json", dry_run=True)
result = set_token(None, False, from_config=True,
                   repo_file="repositories.json")
removed = unset_token(cwd="./first-repo")
```

Keep maintenance files in the operator's private configuration directory; do not commit real machine paths or credentials to public repositories. Unset has no broad cleanup mode. Other released commands retain their behavior.
