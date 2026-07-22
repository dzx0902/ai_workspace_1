from __future__ import annotations

import asyncio

from astrbot.api.event import AstrMessageEvent, filter

from ..utils import command_args, format_planner_result, format_today_tasks


class PlannerCommands:
    @filter.command("plan")
    async def plan(self, event: AstrMessageEvent):
        text = " ".join(command_args(event.message_str, "plan"))
        if not text:
            yield event.plain_result("用法：/plan 今天完成什么任务")
            return
        data = await asyncio.to_thread(self.planner_client.post, "/api/v1/plans", {"input": text, "user_id": "default"}, 60)
        yield event.plain_result(format_planner_result(data))

    @filter.command("today")
    async def today(self, event: AstrMessageEvent):
        data = await asyncio.to_thread(self.planner_client.get, "/api/v1/tasks/today", 30)
        tasks = data.get("data", [])
        yield event.plain_result(format_today_tasks(tasks if isinstance(tasks, list) else []))
