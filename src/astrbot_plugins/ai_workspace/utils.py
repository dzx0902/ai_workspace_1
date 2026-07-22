from __future__ import annotations

from datetime import datetime
import json
import shlex
from typing import Any
from zoneinfo import ZoneInfo


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


def format_planner_result(data: dict[str, Any]) -> str:
    """Render planner API data as a compact chat response."""
    result = data.get("data", data)
    if not isinstance(result, dict):
        return "计划创建完成。"
    if data.get("success") is False or result.get("success") is False:
        return str(data.get("error") or result.get("message") or "创建计划失败。")

    scheduled = result.get("scheduled_tasks", [])
    unscheduled = result.get("unscheduled_tasks", [])
    lines = [f"已安排 {len(scheduled)} 项任务"]
    lines.extend(_format_planner_task(task) for task in scheduled if isinstance(task, dict))
    if unscheduled:
        lines.append(f"暂未安排 {len(unscheduled)} 项：")
        lines.extend(f"- {task.get('title', '未命名任务')}" for task in unscheduled if isinstance(task, dict))
    return "\n".join(lines)


def format_today_tasks(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "今天暂无任务。"
    lines = [f"今日计划（{len(tasks)} 项）"]
    lines.extend(_format_planner_task(task, include_status=True) for task in tasks)
    return "\n".join(lines)


def _format_planner_task(task: dict[str, Any], include_status: bool = False) -> str:
    start = _format_planner_time(task.get("start"))
    end = _format_planner_time(task.get("end"))
    schedule = f"{start}-{end}" if start and end else "待安排"
    priority = task.get("priority") or "P1"
    title = task.get("title") or "未命名任务"
    must_today = " 必做" if task.get("must_today") else ""
    status = _planner_status_label(task.get("status")) if include_status else ""
    return f"- {schedule} [{priority}] {title}{must_today}{status}"


def _format_planner_time(value: Any) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(ZoneInfo("Asia/Shanghai"))
        return parsed.strftime("%H:%M")
    except ValueError:
        return str(value)


def _planner_status_label(value: Any) -> str:
    labels = {"Planned": "（待办）", "Done": "（已完成）", "Canceled": "（已取消）"}
    return labels.get(str(value), "")
