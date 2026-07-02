from __future__ import annotations

from astrbot.api.star import register
from astrbot.core.star.star_handler import star_handlers_registry

from .plugin import AIWorkspacePlugin as _BaseAIWorkspacePlugin


@register(
    "ai_workspace",
    "dzx0902",
    "Low-permission bridge to the local AI Workspace FastAPI service.",
    "0.2.7",
)
class AIWorkspacePlugin(_BaseAIWorkspacePlugin):
    pass


# Handlers are declared in the package module. Attribute them to this entrypoint
# so AstrBot binds them to the plugin instance loaded from main.py.
for handler in star_handlers_registry:
    if handler.handler_module_path.startswith(__package__ or ""):
        handler.handler_module_path = __name__


__all__ = ["AIWorkspacePlugin"]
