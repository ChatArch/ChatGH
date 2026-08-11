from pathlib import Path

PUBLIC_DOCS = (
    "README.md",
    "docs/index.md",
    "docs/index.en.md",
    "docs/interface-tree.md",
    "docs/interface-tree.en.md",
    "docs/gh-interface-alignment.md",
    "docs/gh-interface-alignment.en.md",
    "docs/agent-definition.md",
    "docs/agent-definition.en.md",
    "docs/agent-task-bot-alignment.md",
    "docs/agent-task-bot-alignment.en.md",
)


def test_mkdocs_material_renderer_and_package_metadata_contract() -> None:
    mkdocs = Path("mkdocs.yml").read_text(encoding="utf-8")
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "site_url: https://arch.gh.wzhecnu.cn/ChatGH/" in mkdocs
    assert "mkdocs-static-i18n" in pyproject
    assert "mkdocs-material>=9.5,<10.0" in pyproject
    assert "emoji_index: !!python/name:material.extensions.emoji.twemoji" in mkdocs
    assert "emoji_generator: !!python/name:material.extensions.emoji.to_svg" in mkdocs
    assert 'Homepage = "https://arch.gh.wzhecnu.cn/ChatGH/"' in pyproject
    assert 'Documentation = "https://arch.gh.wzhecnu.cn/ChatGH/"' in pyproject


def test_public_docs_do_not_point_to_stale_domains_or_scaffold_commands() -> None:
    for rel in PUBLIC_DOCS:
        text = Path(rel).read_text(encoding="utf-8")
        assert "github.io" not in text.lower(), rel
        assert "OWNER/REPO" not in text, rel
        assert "latest/" not in text, rel
        assert "template `hello`" not in text.lower(), rel
