from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import urllib.parse

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter

from ..config import PAPER_TIMEZONE, SUBSCRIPTIONS_FILE
from ..utils import command_args, initial_last_sent, positive_option, split_message


class PaperCommands:
    def _format_platform_paper_schedule(self, data: dict) -> str:
        enabled = "开启" if data.get("enabled", True) else "关闭"
        time = data.get("time") or data.get("cron") or "未知"
        body = data.get("body") if isinstance(data.get("body"), dict) else {}
        mode = "关键词筛选" if body.get("no_llm", False) else "LLM 评分"
        limit = body.get("report_limit") or body.get("limit_llm") or 20
        last_run = data.get("last_run") or "暂无"
        return (
            f"论文定时推送：{enabled}\n"
            f"时间：每天 {time}（{PAPER_TIMEZONE.key}）\n"
            f"模式：{mode}，Top {limit}\n"
            f"上次触发：{last_run}"
        )

    def _platform_schedule_body_patch(self, args: list[str], current_body: dict) -> dict | None:
        body = dict(current_body)
        changed = False
        if "--llm" in args:
            body["no_llm"] = False
            changed = True
        if "--no-llm" in args:
            body["no_llm"] = True
            changed = True
        if "--limit" in args:
            report_limit = positive_option(args, "--limit", default=5, maximum=30)
            body["report_limit"] = report_limit
            body["limit_llm"] = report_limit
            changed = True
        return body if changed else None

    def _load_subscriptions(self) -> dict:
        if not SUBSCRIPTIONS_FILE.exists():
            return {}
        try:
            value = json.loads(SUBSCRIPTIONS_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except Exception as exc:
            logger.error(f"Failed to load Paper Radar subscriptions: {exc}")
            return {}

    def _save_subscriptions(self, subscriptions: dict) -> None:
        SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = SUBSCRIPTIONS_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(subscriptions, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(SUBSCRIPTIONS_FILE)

    async def _paper_scheduler(self) -> None:
        while True:
            try:
                now = datetime.now(PAPER_TIMEZONE)
                subscriptions = self._load_subscriptions()
                changed = False
                for umo, config in subscriptions.items():
                    scheduled_time = str(config.get("time", "08:30"))
                    if now.strftime("%H:%M") < scheduled_time:
                        continue
                    if config.get("last_sent") == now.date().isoformat():
                        continue
                    last_attempt = config.get("last_attempt")
                    if last_attempt:
                        try:
                            attempted_at = datetime.fromisoformat(last_attempt)
                            if now - attempted_at < timedelta(hours=1):
                                continue
                        except ValueError:
                            pass
                    config["last_attempt"] = now.isoformat(timespec="seconds")
                    changed = True
                    payload = {
                        "date": now.date().isoformat(),
                        "limit_llm": int(config.get("limit_llm", 20)),
                        "no_llm": bool(config.get("no_llm", True)),
                        "report_limit": int(config.get("report_limit", 20)),
                    }
                    try:
                        data = await asyncio.to_thread(
                            self.paper_client.post,
                            "/papers/run",
                            payload,
                            300,
                        )
                        chunks = split_message(data["message"])
                        for index, chunk in enumerate(chunks, 1):
                            prefix = f"论文日报 {index}/{len(chunks)}\n" if len(chunks) > 1 else ""
                            await self.context.send_message(
                                umo,
                                MessageChain().message(prefix + chunk),
                            )
                            await asyncio.sleep(1)
                        config["last_sent"] = now.date().isoformat()
                    except Exception as exc:
                        logger.error(f"Paper Radar scheduled push failed for {umo}: {exc}")
                if changed:
                    self._save_subscriptions(subscriptions)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(f"Paper Radar scheduler error: {exc}")
            await asyncio.sleep(30)

    @filter.command("papers")
    async def papers(self, event: AstrMessageEvent):
        """查看指定日期的论文雷达摘要。用法：/papers [YYYY-MM-DD] [数量]"""
        args = command_args(event.message_str, "papers")
        report_date = args[0] if args else datetime.now(PAPER_TIMEZONE).date().isoformat()
        try:
            limit = max(1, min(int(args[1]), 10)) if len(args) > 1 else 5
        except ValueError:
            yield event.plain_result("数量需要是 1 到 10 之间的整数，例如 /papers 2026-07-23 5")
            return
        data = await asyncio.to_thread(
            self.paper_client.get_params,
            "/papers/daily",
            {"date": report_date, "limit": limit},
        )
        yield event.plain_result(data["message"])

    @filter.command("paper")
    async def paper(self, event: AstrMessageEvent):
        """查看单篇论文详情。用法：/paper <arXiv ID>"""
        args = command_args(event.message_str, "paper")
        if not args:
            yield event.plain_result("Usage: /paper <arXiv ID>")
            return
        paper_id = urllib.parse.quote(args[0], safe="")
        data = await asyncio.to_thread(self.paper_client.get, f"/papers/detail/{paper_id}")
        yield event.plain_result(data["message"])

    @filter.command("paper_run")
    async def paper_run(self, event: AstrMessageEvent):
        """立即更新论文雷达。--limit 同时限制评分和聊天展示数量。"""
        args = command_args(event.message_str, "paper_run")
        use_llm = "--llm" in args
        report_date = datetime.now(PAPER_TIMEZONE).date().isoformat()
        if "--date" in args and args.index("--date") + 1 < len(args):
            report_date = args[args.index("--date") + 1]
        try:
            report_limit = positive_option(args, "--limit", default=5, maximum=10)
        except ValueError:
            yield event.plain_result("--limit 需要 1 到 10 之间的整数，例如 /paper_run --llm --limit 5")
            return
        data = await asyncio.to_thread(
            self.paper_client.post,
            "/papers/run",
            {
                "date": report_date,
                "limit_llm": report_limit,
                "no_llm": not use_llm,
                "report_limit": report_limit,
            },
            300,
        )
        yield event.plain_result(data["message"])

    @filter.command("paper_schedule")
    async def paper_schedule(self, event: AstrMessageEvent):
        """管理平台级论文定时推送。用法：/paper_schedule [HH:MM|on|off|run] [--llm|--no-llm] [--limit N]"""
        args = command_args(event.message_str, "paper_schedule")
        try:
            if not args or args[0] in {"status", "show"}:
                data = await asyncio.to_thread(self.scheduler_client.get, "/v1/jobs/paper_daily")
                yield event.plain_result(self._format_platform_paper_schedule(data))
                return

            action = args[0].lower()
            if action in {"run", "now"}:
                await asyncio.to_thread(self.scheduler_client.post, "/v1/jobs/paper_daily/run", {}, 300)
                yield event.plain_result("已触发论文定时任务，结果会推送到论文机器人。")
                return

            if action in {"on", "off"}:
                data = await asyncio.to_thread(
                    self.scheduler_client.patch,
                    "/v1/jobs/paper_daily",
                    {"enabled": action == "on"},
                )
                yield event.plain_result(self._format_platform_paper_schedule(data))
                return

            datetime.strptime(args[0], "%H:%M")
            patch = {"time": args[0]}
            current = await asyncio.to_thread(self.scheduler_client.get, "/v1/jobs/paper_daily")
            body = self._platform_schedule_body_patch(args[1:], current.get("body", {}))
            if body is not None:
                patch["body"] = body
            data = await asyncio.to_thread(self.scheduler_client.patch, "/v1/jobs/paper_daily", patch)
            yield event.plain_result(self._format_platform_paper_schedule(data))
        except ValueError:
            yield event.plain_result("用法：/paper_schedule [HH:MM|on|off|run] [--llm|--no-llm] [--limit N]")
        except Exception as exc:
            yield event.plain_result(f"调度器暂时不可用：{exc}")

    @filter.command("paper_subscribe")
    async def paper_subscribe(self, event: AstrMessageEvent):
        """订阅每日论文推送。用法：/paper_subscribe HH:MM [--llm] [--top N]"""
        args = command_args(event.message_str, "paper_subscribe")
        if not args:
            yield event.plain_result("Usage: /paper_subscribe HH:MM [--llm] [--top N]")
            return
        try:
            datetime.strptime(args[0], "%H:%M")
            report_limit = 20
            if "--top" in args and args.index("--top") + 1 < len(args):
                report_limit = max(1, min(int(args[args.index("--top") + 1]), 30))
        except ValueError:
            yield event.plain_result("时间格式应为 HH:MM，例如 /paper_subscribe 08:30")
            return
        subscriptions = self._load_subscriptions()
        now = datetime.now(PAPER_TIMEZONE)
        use_llm = "--llm" in args
        subscriptions[event.unified_msg_origin] = {
            "time": args[0],
            "no_llm": not use_llm,
            "limit_llm": report_limit if use_llm else 20,
            "report_limit": report_limit,
            "last_sent": initial_last_sent(args[0], now),
        }
        self._save_subscriptions(subscriptions)
        mode = "LLM 评分" if use_llm else "关键词筛选"
        starts = (
            "明天开始推送"
            if subscriptions[event.unified_msg_origin]["last_sent"]
            else "今天开始推送"
        )
        yield event.plain_result(
            f"已订阅每天 {args[0]}（{PAPER_TIMEZONE.key}）的论文推送，"
            f"模式：{mode}，Top {report_limit}，{starts}。"
        )

    @filter.command("paper_unsubscribe")
    async def paper_unsubscribe(self, event: AstrMessageEvent):
        """取消当前会话的每日论文推送。"""
        subscriptions = self._load_subscriptions()
        removed = subscriptions.pop(event.unified_msg_origin, None)
        self._save_subscriptions(subscriptions)
        yield event.plain_result("已取消论文推送。" if removed else "当前会话没有论文推送订阅。")

    @filter.command("paper_subscription")
    async def paper_subscription(self, event: AstrMessageEvent):
        """查看当前会话的论文推送设置。"""
        config = self._load_subscriptions().get(event.unified_msg_origin)
        if not config:
            yield event.plain_result("当前会话没有论文推送订阅。")
            return
        mode = "关键词筛选" if config.get("no_llm", True) else "LLM 评分"
        yield event.plain_result(
            f"每日 {config['time']}（{PAPER_TIMEZONE.key}），{mode}，Top {config.get('report_limit', 20)}。"
        )
