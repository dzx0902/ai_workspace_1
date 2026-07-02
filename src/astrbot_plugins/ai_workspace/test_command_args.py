from datetime import datetime
from zoneinfo import ZoneInfo

from . import command_args, initial_last_sent


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
