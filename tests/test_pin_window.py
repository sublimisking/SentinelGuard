
from types import SimpleNamespace
from unittest.mock import Mock

import tkinter as tk

from sentinelguard.core.pin_manager import PinStorageError
from sentinelguard.ui.pin_window import (
    PinWindow,
    get_pin_status_text
)


# TEST 1 - PIN sayaci 10 saniyeden baslar.
def test_pin_countdown_displays_ten_seconds():

    security = SimpleNamespace(
        pin_deadline=110.0,
        pin_timeout_triggered=False,
        clock=lambda: 100.0
    )

    assert get_pin_status_text(security) == "00:10"


# TEST 2 - PIN sayaci azalir.
def test_pin_countdown_decreases():

    security = SimpleNamespace(
        pin_deadline=110.0,
        pin_timeout_triggered=False,
        clock=lambda: 105.0
    )

    assert get_pin_status_text(security) == "00:05"


# TEST 3 - Sure doldugunda alarm yazisi gorunur.
def test_expired_countdown_displays_alarm():

    security = SimpleNamespace(
        pin_deadline=110.0,
        pin_timeout_triggered=True,
        clock=lambda: 110.0
    )

    assert get_pin_status_text(security) == "SIREN AKTIF"


# TEST 4 - Aninda alarm olayinda alarm yazisi gorunur.
def test_immediate_alarm_displays_alarm():

    security = SimpleNamespace(
        pin_deadline=None,
        pin_timeout_triggered=False,
        clock=lambda: 100.0
    )

    assert get_pin_status_text(security) == "SIREN AKTIF"


# SAHTE PIN PENCERESI
def make_fake_window(pin, accepted):

    # Gercek Tk penceresi olusturmadan metodu test et.
    window = PinWindow.__new__(PinWindow)

    window.security_manager = Mock()
    window.security_manager.submit_pin.return_value = accepted

    window.pin_entry = Mock()
    window.pin_entry.get.return_value = pin

    window.feedback_var = Mock()
    window.hide = Mock()
    window.on_disarmed = Mock()

    return window


# TEST 5 - Dogru PIN pencereyi kapatir.
def test_correct_pin_closes_window():

    window = make_fake_window("864201", True)

    window._submit_pin()

    window.security_manager.submit_pin.assert_called_once_with(
        "864201"
    )

    window.pin_entry.delete.assert_called_once_with(
        0, tk.END
    )

    window.hide.assert_called_once()
    window.on_disarmed.assert_called_once()


# TEST 6 - Yanlis PIN pencereyi kapatmaz.
def test_wrong_pin_keeps_window_open():

    window = make_fake_window("111111", False)

    window._submit_pin()

    window.hide.assert_not_called()
    window.on_disarmed.assert_not_called()

    window.feedback_var.set.assert_called_once_with(
        "Yanlış PIN."
    )


# TEST 7 - Bozuk PIN kaydinda koruma devam eder.
def test_corrupt_pin_storage_keeps_window_open():

    window = make_fake_window("864201", False)

    window.security_manager.submit_pin.side_effect = (
        PinStorageError("Bozuk kayit.")
    )

    window._submit_pin()

    window.hide.assert_not_called()
    window.on_disarmed.assert_not_called()

    window.feedback_var.set.assert_called_once_with(
        "PIN kaydı okunamadı. Koruma devam ediyor."
    )
