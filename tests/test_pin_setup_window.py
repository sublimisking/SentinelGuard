from unittest.mock import Mock

from sentinelguard.ui.pin_setup_window import PinSetupWindow


def test_pin_show_and_hide():

    window = PinSetupWindow.__new__(PinSetupWindow)

    window.pin_visible = False
    window.pin_entry = Mock()
    window.pin_show_button = Mock()

    window.toggle_pin_visibility()

    assert window.pin_visible is True
    window.pin_entry.configure.assert_called_with(show="")
    window.pin_show_button.configure.assert_called_with(
        text="Gizle"
    )

    window.toggle_pin_visibility()

    assert window.pin_visible is False
    window.pin_entry.configure.assert_called_with(show="*")
    window.pin_show_button.configure.assert_called_with(
        text="Göster"
    )


def test_confirmation_show_and_hide():

    window = PinSetupWindow.__new__(PinSetupWindow)

    window.confirm_visible = False
    window.confirm_entry = Mock()
    window.confirm_show_button = Mock()

    window.toggle_confirm_visibility()

    assert window.confirm_visible is True
    window.confirm_entry.configure.assert_called_with(show="")

    window.toggle_confirm_visibility()

    assert window.confirm_visible is False
    window.confirm_entry.configure.assert_called_with(show="*")
