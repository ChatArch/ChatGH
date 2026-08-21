# Development Guide

## CLI Rules

- Use `chatstyle>=0.2.0,<0.3.0` and `chatenv>=0.2.9,<0.3.0` as the canonical CLI interaction runtime.
- Prefer `CommandSchema`, `CommandField`, `add_interactive_option()`, and `resolve_command_inputs()` for new commands.
- Use `add_tree_option()` for the registered Click tree; keep `--tree` signatures verbose and provide `--tree-brief` without parameter signatures.
- Missing required args should auto-enter interactive mode when recoverable and `CHATARCH_AUTO_PROMPT` is not false.
- `CHATARCH_AUTO_PROMPT=0/false/no/off` disables default auto-prompting for machine/CI callers.
- `-i` forces interactive mode; `-I` disables prompting and must fail fast.
- Prompt defaults must match actual execution defaults.
- Sensitive values must stay masked in prompts and summaries.
- Prefer lazy imports in CLI wiring and keep implementation imports local when possible.

## Docs and Tests

- Use doc-first CLI testing.
- Put real CLI coverage under `tests/cli-tests/`.
- Put mock/fake CLI coverage under `tests/mock-cli-tests/`.
- Keep `README.md`, `docs/`, and `CHANGELOG.md` in sync with user-facing changes.

## Automation

- Keep automation small and reviewable.
- Prefer commands that can run in CI without interactive prompts.
- Ensure generated defaults are safe for local development.
