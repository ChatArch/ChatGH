import importlib


def __getattr__(name: str):
    if name != "GitHubClient":
        raise AttributeError(name)
    value = getattr(importlib.import_module("chatgh.github.client"), name)
    globals()[name] = value
    return value

__all__ = ["GitHubClient"]
