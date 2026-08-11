from pathlib import Path


def test_ci_workflow_runs_matrix_and_installed_cli_smoke() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'python-version: ["3.10", "3.11", "3.12"]' in workflow
    assert "python -m pip install -e .[dev,docs]" in workflow
    assert "python -m pytest -q" in workflow
    assert "chatgh --version" in workflow
    assert "chatgh --tree" in workflow
    assert "mkdocs build --strict" in workflow


def test_publish_workflow_uses_oidc_with_tag_and_main_guards() -> None:
    workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "Check tag matches package version" in workflow
    assert "Check release commit is on default branch" in workflow
    assert "git fetch --no-tags origin master:refs/remotes/origin/master" in workflow
    assert 'git merge-base --is-ancestor "${GITHUB_SHA}" "origin/master"' in workflow
    assert "git fetch origin master --tags" not in workflow
    assert "git fetch origin main --tags" not in workflow
    assert "TWINE_PASSWORD" not in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "secrets.PYPI" not in workflow
    assert "environment: pypi" not in workflow


def test_preview_and_deploy_workflows_use_chatarch_docs_domain() -> None:
    preview = Path(".github/workflows/preview.yaml").read_text(encoding="utf-8")
    deploy = Path(".github/workflows/deploy.yaml").read_text(encoding="utf-8")

    assert "CHATARCH_PREVIEW_URL: https://arch.gh.wzhecnu.cn/ChatGH/dev/" in preview
    assert "mike deploy dev --push --update-aliases" in preview
    assert "mkdocs gh-deploy --force" in deploy
    assert "chatarch.github.io" not in preview
    assert "chatarch.github.io" not in deploy
