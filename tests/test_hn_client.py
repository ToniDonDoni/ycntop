from datetime import datetime, timezone

from src.hn_client import filter_recent_items


def test_filter_recent_items_filters_old_entries():
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    items = [
        {"id": 1, "time": int(now.timestamp())},
        {"id": 2, "time": int((now.timestamp() - 25 * 3600))},
    ]
    recent = filter_recent_items(items, hours=24, now=now)
    assert len(recent) == 1
    assert recent[0]["id"] == 1
