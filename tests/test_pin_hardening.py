"""PIN deneme siniri, PIN kaydi bellekte tutma, zayif PIN ve olay toplama."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sentinelguard.app import SentinelGuardApp
from sentinelguard.core.event_store import EventStore
from sentinelguard.core.pin_manager import (
    PinManager,
    PinStorageError,
    check_pin_strength,
)
from sentinelguard.core.security_manager import SecurityManager
from sentinelguard.ui.pin_window import PinWindow


class FakeAlarm:
    def start_alarm(self):
        pass

    def stop_alarm(self):
        pass


def make_security(correct="864201"):
    now = [100.0]
    security = SecurityManager(
        FakeAlarm(),
        pin_verifier=lambda pin: pin == correct,
        clock=lambda: now[0],
    )
    security.arm()
    return security, now


# --- #4: PIN deneme siniri ---------------------------------------------


def test_first_three_wrong_attempts_have_no_lockout():
    security, _ = make_security()
    for _ in range(3):
        assert security.submit_pin("000001") is False
        assert security.lockout_remaining() == 0


def test_fourth_wrong_attempt_starts_lockout_and_blocks_correct_pin():
    security, now = make_security()
    for _ in range(4):
        security.submit_pin("000001")

    assert security.lockout_remaining() == pytest.approx(5.0)
    # Bekleme suresinde dogru PIN bile kabul edilmez.
    assert security.submit_pin("864201") is False
    assert security.is_armed is True

    now[0] += 5.1
    assert security.lockout_remaining() == 0
    assert security.submit_pin("864201") is True


def test_lockout_grows_and_is_capped_at_sixty_seconds():
    security, now = make_security()
    waits = []
    for _ in range(12):
        security.submit_pin("000001")
        waits.append(round(security.lockout_remaining()))
        now[0] += 100  # beklemeyi bitir
    assert waits[3:8] == [5, 10, 20, 40, 60]
    assert max(waits) == 60


def test_locked_attempts_do_not_call_verifier():
    verifier = Mock(return_value=False)
    now = [0.0]
    security = SecurityManager(
        FakeAlarm(), pin_verifier=verifier, clock=lambda: now[0]
    )
    security.arm()
    for _ in range(4):
        security.submit_pin("000001")
    calls = verifier.call_count
    security.submit_pin("000001")
    assert verifier.call_count == calls


def test_rearm_resets_attempts():
    security, _ = make_security()
    for _ in range(5):
        security.submit_pin("000001")
    assert security.lockout_remaining() > 0
    security.disarm()
    security.arm()
    assert security.lockout_remaining() == 0
    assert security.failed_pin_attempts == 0


def test_pin_window_shows_lockout_message():
    window = PinWindow.__new__(PinWindow)
    window.pin_entry = Mock()
    window.pin_entry.get.return_value = "000001"
    window.feedback_var = Mock()
    window.hide = Mock()
    window.on_disarmed = None
    window.security_manager = Mock()
    window.security_manager.submit_pin.return_value = False
    window.security_manager.lockout_remaining.return_value = 4.2

    window._submit_pin()
    text = window.feedback_var.set.call_args[0][0]
    assert "5 saniye" in text

    window.security_manager.lockout_remaining.return_value = 0
    window._submit_pin()
    assert window.feedback_var.set.call_args[0][0] == "Yanlış PIN."


# --- #5: PIN kaydi bellekte --------------------------------------------


def test_locked_record_ignores_tampered_pin_file(tmp_path):
    manager = PinManager(tmp_path / "pin.json", iterations=1)
    manager.set_pin("864201")
    manager.lock_record()

    # Saldirgan dosyayi kendi bildigi PIN ile degistirir.
    attacker = PinManager(tmp_path / "pin.json", iterations=1)
    (tmp_path / "pin.json").unlink()
    attacker.set_pin("135790")

    assert manager.verify_pin("135790") is False
    assert manager.verify_pin("864201") is True

    manager.unlock_record()
    assert manager.verify_pin("135790") is True


def test_locked_record_survives_deleted_pin_file(tmp_path):
    manager = PinManager(tmp_path / "pin.json", iterations=1)
    manager.set_pin("864201")
    manager.lock_record()
    (tmp_path / "pin.json").unlink()
    assert manager.verify_pin("864201") is True
    assert manager.verify_pin("000001") is False


def test_lock_record_fails_on_corrupt_file(tmp_path):
    path = tmp_path / "pin.json"
    path.write_text("bozuk")
    with pytest.raises(PinStorageError):
        PinManager(path, iterations=1).lock_record()


def test_change_pin_clears_cached_record(tmp_path):
    manager = PinManager(tmp_path / "pin.json", iterations=1)
    manager.set_pin("864201")
    manager.lock_record()
    assert manager.change_pin("864201", "975310") is True
    assert manager.verify_pin("975310") is True
    assert manager.verify_pin("864201") is False


def test_app_locks_on_arm_and_unlocks_on_disarm(tmp_path):
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.pin_manager = Mock()
    app.event_store = EventStore(tmp_path / "events.db")
    app.stop_monitors = Mock()
    app.root = Mock()
    app.status_var = Mock()
    app.arm_button = Mock()
    app.security_manager = Mock()
    for name in ("power_monitor", "usb_monitor", "input_monitor"):
        setattr(app, name, Mock())

    app.activate_protection()
    app.pin_manager.lock_record.assert_called_once_with()

    app.on_disarmed()
    app.pin_manager.unlock_record.assert_called_once_with()


def test_arm_failure_when_pin_record_unreadable(tmp_path):
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.pin_manager = Mock()
    app.pin_manager.lock_record.side_effect = PinStorageError("bozuk")
    app.event_store = EventStore(tmp_path / "events.db")
    app.stop_monitors = Mock()
    app.status_var = Mock()
    app.arm_button = Mock()
    app.security_manager = Mock()

    app.activate_protection()
    app.security_manager.arm.assert_not_called()
    assert [e.code for e in app.get_recent_events()] == ["ARM_FAILED"]


# --- #6: Zayif PIN -------------------------------------------------------


@pytest.mark.parametrize("pin", [
    "123456", "654321", "111111", "000000", "121212", "123123",
    "234567", "567890", "901234", "987654", "112233", "159753",
    "12345678", "00000000", "12121212",
])
def test_weak_pins_are_rejected(pin):
    with pytest.raises(ValueError, match="tahmin"):
        check_pin_strength(pin)


@pytest.mark.parametrize("pin", [
    "864201", "135790", "482915", "908172", "13579024", "271828",
])
def test_reasonable_pins_are_accepted(pin):
    check_pin_strength(pin)


def test_existing_weak_pin_can_still_unlock(tmp_path):
    # Eski kullanicilarin PIN'i dogrulamada reddedilmemeli.
    manager = PinManager(tmp_path / "pin.json", iterations=1)
    manager.set_pin("123456")
    assert manager.verify_pin("123456") is True


def test_app_change_pin_rejects_weak_new_pin():
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.closed = False
    app.arming_after_id = None
    app.security_manager = SimpleNamespace(is_armed=False)
    app.pin_manager = Mock()
    with pytest.raises(ValueError):
        app.change_pin("864201", "111111")
    app.pin_manager.change_pin.assert_not_called()


def test_setup_window_rejects_weak_pin():
    from sentinelguard.ui.pin_setup_window import PinSetupWindow

    window = PinSetupWindow.__new__(PinSetupWindow)
    window.pin_entry = Mock()
    window.pin_entry.get.return_value = "123456"
    window.confirm_entry = Mock()
    window.confirm_entry.get.return_value = "123456"
    window.feedback = Mock()
    window.pin_manager = Mock()

    window.submit()
    window.pin_manager.set_pin.assert_not_called()
    assert "tahmin" in window.feedback.configure.call_args.kwargs["text"]


# --- #3: Olay geçmişini yanlis PIN'lerle doldurma -----------------------


def test_repeated_rejected_pins_collapse_into_one_row(tmp_path):
    store = EventStore(tmp_path / "events.db")
    store.add("ALARM_STARTED", "alarm", "Siren başlatıldı")
    store.add("PHOTO_CAPTURED", "alarm", "Kamera fotoğrafı kaydedildi")
    for _ in range(25):
        store.add_repeating("PIN_REJECTED", "auth", "Yanlış PIN denemesi")

    events = store.recent(limit=10)
    assert [e.code for e in events] == [
        "PIN_REJECTED", "PHOTO_CAPTURED", "ALARM_STARTED"
    ]
    assert events[0].message == "Yanlış PIN denemesi (×25)"


def test_repeating_starts_new_row_after_other_event(tmp_path):
    store = EventStore(tmp_path / "events.db")
    store.add_repeating("PIN_REJECTED", "auth", "Yanlış PIN denemesi")
    store.add("PIN_ACCEPTED", "auth", "Doğru PIN girildi")
    store.add_repeating("PIN_REJECTED", "auth", "Yanlış PIN denemesi")

    messages = [e.message for e in store.recent()]
    assert messages == [
        "Yanlış PIN denemesi", "Doğru PIN girildi", "Yanlış PIN denemesi"
    ]


def test_app_verify_pin_collapses_rejections(tmp_path):
    app = SentinelGuardApp.__new__(SentinelGuardApp)
    app.event_store = EventStore(tmp_path / "events.db")
    app.pin_manager = SimpleNamespace(verify_pin=lambda pin: False)
    for _ in range(12):
        app._verify_pin("000001")
    events = app.get_recent_events()
    assert len(events) == 1
    assert events[0].message.endswith("(×12)")
    assert "000001" not in events[0].message
