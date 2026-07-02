from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shlex
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star

API_BASE = os.getenv("AI_WORKSPACE_API_BASE", "http://host.docker.internal:8001").rstrip("/")
PAPER_API_BASE = os.getenv("PAPER_RADAR_API_BASE", API_BASE).rstrip("/")
SUBSCRIPTIONS_FILE = Path(
    os.getenv("PAPER_RADAR_SUBSCRIPTIONS", "/AstrBot/data/paper_radar_subscriptions.json")
)
PAPER_TIMEZONE = ZoneInfo(os.getenv("PAPER_RADAR_TIMEZONE", "Asia/Shanghai"))


def post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(body or str(exc)) from exc


def get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{API_BASE}{path}", timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json_params(path: str, params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    return get_json(f"{path}?{query}")


def paper_post_json(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{PAPER_API_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paper_get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{PAPER_API_BASE}{path}", timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def paper_get_json_params(path: str, params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    return paper_get_json(f"{path}?{query}")


def command_args(message: str, command: str) -> list[str]:
    """Parse args whether AstrBot keeps or strips the leading slash."""
    tokens = shlex.split(message.strip())
    if tokens and tokens[0].lstrip("/").casefold() == command.casefold():
        tokens = tokens[1:]
    return tokens


def initial_last_sent(scheduled_time: str, now: datetime) -> str:
    """Avoid an immediate catch-up push when subscribing after today's time."""
    if now.strftime("%H:%M") >= scheduled_time:
        return now.date().isoformat()
    return ""


def text_result(data: dict) -> str:
    if "answer" in data:
        return data["answer"]
    result = data.get("result", data)
    if isinstance(result, dict):
        for key in ("plan", "patch", "note", "markdown", "dir"):
            if key in result:
                return str(result[key])
    return json.dumps(data, ensure_ascii=False, indent=2)


def file_result(data: dict) -> str:
    result = data.get("result", data)
    if not isinstance(result, dict):
        return text_result(data)
    lines = ["Processed."]
    if result.get("markdown"):
        lines.append(f"Markdown: {result['markdown']}")
    if result.get("note"):
        lines.append(f"Note: {result['note']}")
    ingest = result.get("ingest")
    if isinstance(ingest, dict):
        lines.append(f"Chunks: {ingest.get('chunks', 0)}")
    return "\n".join(lines)


def parse_out(args: list[str]) -> tuple[list[str], str | None]:
    if "--out" not in args:
        return args, None
    idx = args.index("--out")
    if idx == len(args) - 1:
        raise ValueError("--out requires a value")
    output_dir = args[idx + 1]
    return args[:idx] + args[idx + 2 :], output_dir


def split_message(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        lines = paragraph.splitlines()
        current = ""
        for line in lines:
            candidate = line if not current else f"{current}\n{line}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = line[:max_chars]
    if current:
        chunks.append(current)
    return chunks


class AIWorkspacePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.paper_scheduler_task: asyncio.Task | None = asyncio.create_task(self._paper_scheduler())

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
                        data = await asyncio.to_thread(paper_post_json, "/papers/run", payload)
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

    @filter.command("ask")
    async def ask(self, event: AstrMessageEvent):
        args = command_args(event.message_str, "ask")
        if len(args) >= 3:
            source_type, category = args[0], args[1]
            question = " ".join(args[2:])
        else:
            source_type = None
            category = None
            question = " ".join(args)
        data = post_json("/ask", {"question": question, "source_type": source_type, "category": category})
        yield event.plain_result(text_result(data))

    @filter.command("file")
    async def file(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "file"))
        if len(args) < 3:
            yield event.plain_result("Usage: /file <source_type> <category> <filename> [--out output_dir]")
            return
        source_type, category, filename = args[0], args[1], args[2]
        data = post_json("/file", {"source_type": source_type, "category": category, "filename": filename, "output_dir": output_dir})
        yield event.plain_result(file_result(data))

    @filter.command("analyze_file")
    async def analyze_file(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "analyze_file"))
        if len(args) < 3:
            yield event.plain_result("Usage: /analyze_file <source_type> <category> <filename> [--out output_dir]")
            return
        source_type, category, filename = args[0], args[1], args[2]
        data = post_json("/file", {"source_type": source_type, "category": category, "filename": filename, "output_dir": output_dir})
        yield event.plain_result(file_result(data))

    @filter.command("analyze_pdf")
    async def analyze_pdf(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "analyze_pdf"))
        if len(args) < 2:
            yield event.plain_result("Usage: /analyze_pdf <category> <filename> [--out output_dir]")
            return
        category, filename = args[0], args[1]
        data = post_json("/file", {"source_type": "pdf", "category": category, "filename": filename, "output_dir": output_dir})
        yield event.plain_result(file_result(data))

    @filter.command("web")
    async def web(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "web"))
        if len(args) < 2:
            yield event.plain_result("Usage: /web <category> <url> [--out output_dir]")
            return
        data = post_json("/web", {"category": args[0], "url": args[1], "output_dir": output_dir})
        yield event.plain_result(text_result(data))

    @filter.command("video")
    async def video(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "video"))
        if len(args) < 2:
            yield event.plain_result("Usage: /video <category> <url> [--out output_dir]")
            return
        data = post_json("/video", {"category": args[0], "url": args[1], "output_dir": output_dir})
        yield event.plain_result(text_result(data))

    @filter.command("transcribe")
    async def transcribe(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "transcribe"))
        if len(args) < 2:
            yield event.plain_result("Usage: /transcribe <category> <url_or_file> [--out output_dir]")
            return
        data = post_json("/transcribe", {"category": args[0], "url_or_file": args[1], "output_dir": output_dir})
        yield event.plain_result(text_result(data))

    @filter.command("repos")
    async def repos(self, event: AstrMessageEvent):
        data = get_json("/dev/repos")
        repos = data.get("repos", [])
        if not repos:
            yield event.plain_result("No allowed repos found.")
            return
        yield event.plain_result("\n".join(repo["name"] for repo in repos))

    @filter.command("dev")
    async def dev(self, event: AstrMessageEvent):
        args = command_args(event.message_str, "dev")
        if len(args) < 2:
            yield event.plain_result("Usage: /dev <plan|patch|review|test|diff|apply|task> <repo_name|task_id> ...")
            return
        action, repo_name = args[0], args[1]
        if action == "plan":
            data = post_json("/dev/plan", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "patch":
            data = post_json("/dev/patch", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "review":
            data = post_json("/dev/review", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "test":
            data = post_json("/dev/test", {"repo_name": repo_name, "command": " ".join(args[2:]), "allow_shell": True})
        elif action == "diff":
            data = post_json("/dev/diff", {"repo_name": repo_name})
        elif action == "apply":
            data = post_json("/dev/apply", {"task_id": repo_name, "confirm": True})
        elif action == "task" and len(args) >= 4:
            data = post_json("/dev/task", {"repo_name": repo_name, "task_type": args[2], "task_description": " ".join(args[3:])})
        else:
            yield event.plain_result("Unsupported /dev action.")
            return
        yield event.plain_result(text_result(data))

    @filter.command("papers")
    async def papers(self, event: AstrMessageEvent):
        """查看指定日期的论文雷达摘要。用法：/papers [YYYY-MM-DD] [数量]"""
        args = command_args(event.message_str, "papers")
        report_date = args[0] if args else datetime.now(PAPER_TIMEZONE).date().isoformat()
        limit = int(args[1]) if len(args) > 1 else 20
        data = await asyncio.to_thread(
            paper_get_json_params,
            "/papers/daily",
            {"date": report_date, "limit": max(1, min(limit, 30))},
        )
        for chunk in split_message(data["message"]):
            yield event.plain_result(chunk)

    @filter.command("paper")
    async def paper(self, event: AstrMessageEvent):
        """查看单篇论文详情。用法：/paper <arXiv ID>"""
        args = command_args(event.message_str, "paper")
        if not args:
            yield event.plain_result("Usage: /paper <arXiv ID>")
            return
        paper_id = urllib.parse.quote(args[0], safe="")
        data = await asyncio.to_thread(paper_get_json, f"/papers/detail/{paper_id}")
        yield event.plain_result(data["message"])

    @filter.command("paper_run")
    async def paper_run(self, event: AstrMessageEvent):
        """立即更新论文雷达。默认不调用 LLM；添加 --llm 可启用。"""
        args = command_args(event.message_str, "paper_run")
        use_llm = "--llm" in args
        report_date = datetime.now(PAPER_TIMEZONE).date().isoformat()
        limit_llm = 20
        if "--date" in args and args.index("--date") + 1 < len(args):
            report_date = args[args.index("--date") + 1]
        if "--limit" in args and args.index("--limit") + 1 < len(args):
            limit_llm = int(args[args.index("--limit") + 1])
        data = await asyncio.to_thread(
            paper_post_json,
            "/papers/run",
            {
                "date": report_date,
                "limit_llm": max(1, limit_llm),
                "no_llm": not use_llm,
                "report_limit": 20,
            },
        )
        for chunk in split_message(data["message"]):
            yield event.plain_result(chunk)

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

    async def terminate(self):
        if self.paper_scheduler_task and not self.paper_scheduler_task.done():
            self.paper_scheduler_task.cancel()
            try:
                await self.paper_scheduler_task
            except asyncio.CancelledError:
                pass
