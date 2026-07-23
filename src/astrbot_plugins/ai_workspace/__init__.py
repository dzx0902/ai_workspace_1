from __future__ import annotations

from .utils import command_args, format_planner_result, format_today_tasks, initial_last_sent, positive_option

__all__ = ["AIWorkspacePlugin", "command_args", "format_planner_result", "format_today_tasks", "initial_last_sent", "positive_option"]


def __getattr__(name: str):
    if name == "AIWorkspacePlugin":
        from .plugin import AIWorkspacePlugin

        return AIWorkspacePlugin
    raise AttributeError(name)
