import json
import pytest

from sentinelguard.core.pin_manager import (
    PinManager,
    PinStorageError
)


@pytest.fixture
def manager(tmp_path):
    return PinManager(
        tmp_path / "pin.json",
        iterations=2000
    )


def test_new_install_has_no_pin(manager):

    assert manager.has_pin() is False
    assert manager.verify_pin("123456") is False


def test_set_and_verify_pin(manager):

    manager.set_pin("12345678")

    assert manager.has_pin() is True
    assert manager.verify_pin("12345678") is True
    assert manager.verify_pin("87654321") is False

    saved_text = manager.path.read_text(
        encoding="utf-8"
    )

    assert "12345678" not in saved_text

    saved_data = json.loads(saved_text)

    assert saved_data["algorithm"] == "pbkdf2_sha256"

    # Yeni nesne ayni kayitli PIN'i okuyabilmeli.
    restarted_manager = PinManager(manager.path)

    assert restarted_manager.verify_pin("12345678") is True


@pytest.mark.parametrize(
    "pin",
    [
        "12345",
        "1234567890123",
        "abc123",
        "12 3456",
        "１２３４５６"
    ]
)
def test_invalid_pin_rejected(manager, pin):

    with pytest.raises(ValueError):
        manager.set_pin(pin)


def test_cannot_replace_existing_pin_directly(manager):

    manager.set_pin("123456")

    with pytest.raises(RuntimeError):
        manager.set_pin("654321")

    assert manager.verify_pin("123456") is True


def test_change_pin_requires_old_pin(manager):

    manager.set_pin("123456")

    assert manager.change_pin("000000", "654321") is False
    assert manager.verify_pin("123456") is True

    assert manager.change_pin("123456", "654321") is True

    assert manager.verify_pin("123456") is False
    assert manager.verify_pin("654321") is True


def test_corrupt_file_cannot_be_reset(manager):

    manager.path.write_text(
        "{broken",
        encoding="utf-8"
    )

    assert manager.has_pin() is True

    with pytest.raises(PinStorageError):
        manager.verify_pin("123456")

    with pytest.raises(RuntimeError):
        manager.set_pin("123456")


def test_does_not_modify_audio_settings(tmp_path):

    settings_path = tmp_path / "settings.json"

    settings_path.write_text(
        '{"audio": {"speaker_device_id": "x"}}',
        encoding="utf-8"
    )

    manager = PinManager(
        tmp_path / "pin.json",
        iterations=2000
    )

    manager.set_pin("123456")

    settings = json.loads(
        settings_path.read_text(encoding="utf-8")
    )

    assert settings["audio"]["speaker_device_id"] == "x"
