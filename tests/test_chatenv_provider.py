from pathlib import Path
import importlib
import sys

_toml_module = "tomllib" if sys.version_info >= (3, 11) else "tomli"
tomllib = importlib.import_module(_toml_module)


ROOT = Path(__file__).resolve().parents[1]


def test_package_registers_github_config_as_chatenv_provider():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["entry-points"]["chatenv.configs"] == {
        "github": "chatgh.config"
    }
