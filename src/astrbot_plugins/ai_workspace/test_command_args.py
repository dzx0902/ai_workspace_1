from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from . import command_args, format_planner_result, format_today_tasks, initial_last_sent, positive_option


def test_command_args_handles_slash_and_normalized_messages():
    assert command_args("/papers", "papers") == []
    assert command_args("papers", "papers") == []
    assert command_args("/papers 2026-06-11 10", "papers") == [
        "2026-06-11",
        "10",
    ]
    assert command_args("papers 2026-06-11 10", "papers") == [
        "2026-06-11",
        "10",
    ]


def test_initial_last_sent_defers_subscriptions_created_after_scheduled_time():
    timezone = ZoneInfo("Asia/Shanghai")
    before = datetime(2026, 6, 11, 8, 29, tzinfo=timezone)
    after = datetime(2026, 6, 11, 8, 30, tzinfo=timezone)

    assert initial_last_sent("08:30", before) == ""
    assert initial_last_sent("08:30", after) == "2026-06-11"


def test_positive_option_bounds_and_validates_command_limit():
    assert positive_option(["--limit", "5"], "--limit", default=20, maximum=30) == 5
    assert positive_option(["--limit", "100"], "--limit", default=20, maximum=30) == 30
    assert positive_option([], "--limit", default=20, maximum=30) == 20
    with pytest.raises(ValueError):
        positive_option(["--limit"], "--limit", default=20, maximum=30)


def test_planner_chat_formatting_is_compact_and_uses_local_time():
    task = {
        "title": "学习英语",
        "start": "2026-07-22T01:00:00Z",
        "end": "2026-07-22T01:30:00Z",
        "priority": "P1",
        "must_today": True,
        "status": "Planned",
    }

    assert format_planner_result({"success": True, "data": {"scheduled_tasks": [task], "unscheduled_tasks": []}}) == (
        "已安排 1 项任务\n- 09:00-09:30 [P1] 学习英语 必做"
    )
    assert format_today_tasks([task]) == "今日计划（1 项）\n- 09:00-09:30 [P1] 学习英语 必做（待办）"
