from datetime import datetime

from sentinelguard.core.event_store import EventStore


def test_event_persists_across_instances(tmp_path):
    path = tmp_path / "events.db"
    EventStore(path).add("USB_DISCONNECTED", "security", "USB çıkarıldı")

    records = EventStore(path).recent()
    assert len(records) == 1
    assert records[0].code == "USB_DISCONNECTED"
    assert records[0].message == "USB çıkarıldı"
    datetime.fromisoformat(records[0].occurred_at)


def test_recent_events_newest_first(tmp_path):
    store = EventStore(tmp_path / "events.db")
    store.add("ARMED", "system", "Koruma açıldı")
    store.add("DISARMED", "system", "Koruma kapandı")
    assert [e.code for e in store.recent()] == ["DISARMED", "ARMED"]
    assert [e.code for e in store.recent(limit=1)] == ["DISARMED"]


def test_event_store_limits_retention(tmp_path):
    store = EventStore(tmp_path / "events.db")
    store.MAX_RECORDS = 3
    for i in range(5):
        store.add("EVENT", "system", str(i))
    assert [e.message for e in store.recent()] == ["4", "3", "2"]


def test_event_store_rejects_invalid_limit(tmp_path):
    store = EventStore(tmp_path / "events.db")
    for limit in (0, -1, 501):
        try:
            store.recent(limit)
        except ValueError:
            pass
        else:
            raise AssertionError("Geçersiz limit kabul edildi")


def test_empty_store(tmp_path):
    assert EventStore(tmp_path / "events.db").recent() == []
