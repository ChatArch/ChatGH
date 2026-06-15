from pathlib import Path

from chatgh.config import GitHubConfig


def test_chatenv_entrypoint_registers_chatgh_config():
    pyproject_text = (
        Path(__file__).resolve().parents[1] / "pyproject.toml"
    ).read_text(encoding="utf-8")

    assert '[project.entry-points."chatenv.configs"]' in pyproject_text
    assert 'chatgh = "chatgh.config"' in pyproject_text
    assert "gh" in GitHubConfig._aliases
    assert GitHubConfig.GITHUB_ACCESS_TOKEN.is_sensitive
