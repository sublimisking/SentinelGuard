import hashlib
import hmac
import json
import os
import secrets
import tempfile

from pathlib import Path


class PinStorageError(RuntimeError):
    """PIN kaydi bozuk veya okunamiyor."""


class PinManager:

    DEFAULT_ITERATIONS = 600_000
    MIN_PIN_LENGTH = 6
    MAX_PIN_LENGTH = 12

    def __init__(self, path=None, *, iterations=DEFAULT_ITERATIONS):

        if path is None:
            local_appdata = os.environ.get("LOCALAPPDATA")

            if not local_appdata:
                raise RuntimeError("LOCALAPPDATA bulunamadi.")

            path = (
                Path(local_appdata)
                / "SentinelGuard"
                / "pin.json"
            )

        if type(iterations) is not int or iterations < 1:
            raise ValueError("Gecersiz yineleme sayisi.")

        self.path = Path(path)
        self.iterations = iterations

    def has_pin(self):
        return self.path.exists()

    @classmethod
    def _validate_pin(cls, pin):

        if (
            not isinstance(pin, str)
            or not pin.isascii()
            or not pin.isdigit()
            or not cls.MIN_PIN_LENGTH <= len(pin) <= cls.MAX_PIN_LENGTH
        ):
            raise ValueError(
                "PIN 6-12 haneli ve yalnizca rakamlardan olusmali."
            )

    def _create_record(self, pin):

        salt = secrets.token_bytes(16)

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            self.iterations
        )

        return {
            "version": 1,
            "algorithm": "pbkdf2_sha256",
            "iterations": self.iterations,
            "salt": salt.hex(),
            "hash": digest.hex()
        }

    def _write_record(self, record):

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        fd, temp_path = tempfile.mkstemp(
            prefix=".pin-",
            suffix=".tmp",
            dir=self.path.parent
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(record, file, indent=2)

            os.replace(temp_path, self.path)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _read_record(self):

        try:
            with self.path.open("r", encoding="utf-8") as file:
                record = json.load(file)

            if not isinstance(record, dict):
                raise ValueError("Gecersiz kayit.")

            if (
                record.get("version") != 1
                or record.get("algorithm") != "pbkdf2_sha256"
            ):
                raise ValueError("Bilinmeyen PIN formati.")

            iterations = record["iterations"]

            if (
                type(iterations) is not int
                or not 1 <= iterations <= 10_000_000
            ):
                raise ValueError("Gecersiz yineleme sayisi.")

            salt = bytes.fromhex(record["salt"])
            digest = bytes.fromhex(record["hash"])

            if len(salt) != 16 or len(digest) != 32:
                raise ValueError("Gecersiz PIN verisi.")

            return iterations, salt, digest

        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            UnicodeError
        ) as error:
            raise PinStorageError(
                "PIN kaydi okunamadi veya bozuk."
            ) from error

    def set_pin(self, pin):

        self._validate_pin(pin)

        if self.has_pin():
            raise RuntimeError(
                "PIN zaten ayarlanmis. change_pin() kullan."
            )

        record = self._create_record(pin)
        self._write_record(record)

    def verify_pin(self, pin):

        if not self.has_pin():
            return False

        try:
            self._validate_pin(pin)
        except ValueError:
            return False

        iterations, salt, stored_digest = (
            self._read_record()
        )

        entered_digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            iterations
        )

        return hmac.compare_digest(
            entered_digest,
            stored_digest
        )

    def change_pin(self, old_pin, new_pin):

        self._validate_pin(new_pin)

        if not self.verify_pin(old_pin):
            return False

        record = self._create_record(new_pin)
        self._write_record(record)

        return True
