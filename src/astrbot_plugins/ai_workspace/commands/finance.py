from __future__ import annotations

import asyncio

from astrbot.api.event import AstrMessageEvent, filter

from ..utils import command_args


class FinanceCommands:
    @filter.command("finance")
    async def finance(self, event: AstrMessageEvent):
        query = " ".join(command_args(event.message_str, "finance"))
        if not query:
            yield event.plain_result("用法：/finance 查询今日黄金行情或分析问题")
            return
        data = await asyncio.to_thread(self.finance_client.post, "/api/finance/analyze", {"query": query, "user_id": "default"}, 180)
        yield event.plain_result(str(data.get("answer", data)))

    @filter.command("portfolio")
    async def portfolio(self, event: AstrMessageEvent):
        data = await asyncio.to_thread(self.finance_client.get, "/api/finance/portfolio", 30)
        yield event.plain_result(str(data.get("portfolio", data)))
