from __future__ import annotations

import asyncio

from astrbot.api.star import Context, Star

from .client import JsonApiClient
from .commands import DevCommands, PaperCommands, WorkspaceCommands
from .config import API_BASE, PAPER_API_BASE


class AIWorkspacePlugin(PaperCommands, DevCommands, WorkspaceCommands, Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.workspace_client = JsonApiClient(API_BASE, default_timeout=60)
        self.paper_client = JsonApiClient(PAPER_API_BASE, default_timeout=60)
        self.paper_scheduler_task: asyncio.Task | None = asyncio.create_task(self._paper_scheduler())

    async def terminate(self):
        if self.paper_scheduler_task and not self.paper_scheduler_task.done():
            self.paper_scheduler_task.cancel()
            try:
                await self.paper_scheduler_task
            except asyncio.CancelledError:
                pass
