from __future__ import annotations

from .utils import command_args, initial_last_sent

__all__ = ["AIWorkspacePlugin", "command_args", "initial_last_sent"]


def __getattr__(name: str):
    if name == "AIWorkspacePlugin":
        from .plugin import AIWorkspacePlugin

        return AIWorkspacePlugin
    raise AttributeError(name)
