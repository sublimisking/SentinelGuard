"""SentinelGuard olay geçmişi: küçük, yerel SQLite veri tabanı.

Olaylar yalnızca kod, açıklama, kategori ve zaman içerir.
PIN, şifre, klavye içeriği veya USB cihaz kimliği kaydedilmez.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import sqlite3


@dataclass(frozen=True)
class EventRecord:
    id: int
    occurred_at: str
    code: str
    category: str
    message: str
    photo_path: str | None = None


class EventStore:
    """Uygulama ana thread'inde kısa SQLite işlemleri yapar."""

    MAX_RECORDS = 2000

    def __init__(self, path: str | Path | None = None):
        if path is None:
            base = os.environ.get("LOCALAPPDATA")
            if base is None:
                base_path = Path.home() / "AppData" / "Local"
            else:
                base_path = Path(base)
            path = base_path / "SentinelGuard" / "events.db"

        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=3)
        connection.execute("PRAGMA busy_timeout=3000")
        return connection

    def _initialize(self):
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        occurred_at TEXT NOT NULL,
                        code TEXT NOT NULL,
                        category TEXT NOT NULL,
                        message TEXT NOT NULL,
                        photo_path TEXT
                    )
                    """
                )
                # Eski veritabanlarina fotograf sutununu ekle.
                columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(security_events)"
                    )
                }
                if "photo_path" not in columns:
                    connection.execute(
                        "ALTER TABLE security_events ADD COLUMN photo_path TEXT"
                    )

    def add(
        self,
        code: str,
        category: str,
        message: str,
        photo_path: str | Path | None = None,
    ) -> EventRecord:
        if not code or not category or not message:
            raise ValueError("Olay alanları boş bırakılamaz.")

        occurred_at = datetime.now().astimezone().isoformat(timespec="seconds")
        photo_path = str(photo_path) if photo_path else None

        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO security_events
                        (occurred_at, code, category, message, photo_path)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (occurred_at, code, category, message, photo_path),
                )
                event_id = cursor.lastrowid

                # Veritabanının süresiz büyümesini engelle.
                connection.execute(
                    """
                    DELETE FROM security_events
                    WHERE id NOT IN (
                        SELECT id FROM security_events
                        ORDER BY id DESC LIMIT ?
                    )
                    """,
                    (self.MAX_RECORDS,),
                )

        return EventRecord(
            event_id, occurred_at, code, category, message, photo_path
        )

    _REPEAT_SUFFIX = re.compile(r"^(.*) \(×(\d+)\)$")

    def add_repeating(
        self, code: str, category: str, message: str
    ) -> EventRecord:
        """Ayni kod art arda gelirse yeni satir acmak yerine sayar.

        Ornek: "Yanlış PIN denemesi (×7)". Boylece tekrarlayan olaylar
        gecmisteki diger kayitlari listeden itmez.
        """
        if not code or not category or not message:
            raise ValueError("Olay alanları boş bırakılamaz.")

        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, code, message FROM security_events
                ORDER BY id DESC LIMIT 1
                """
            ).fetchone()

            if row is None or row[1] != code:
                row = None
            else:
                match = self._REPEAT_SUFFIX.match(row[2])
                count = int(match.group(2)) if match else 1
                occurred_at = datetime.now().astimezone().isoformat(
                    timespec="seconds"
                )
                new_message = f"{message} (×{count + 1})"
                with connection:
                    connection.execute(
                        """
                        UPDATE security_events
                        SET occurred_at = ?, message = ?
                        WHERE id = ?
                        """,
                        (occurred_at, new_message, row[0]),
                    )
                return EventRecord(
                    row[0], occurred_at, code, category, new_message
                )

        return self.add(code, category, message)

    def recent(self, limit: int = 100) -> list[EventRecord]:
        if not 1 <= limit <= 500:
            raise ValueError("Limit 1 ile 500 arasında olmalıdır.")

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, occurred_at, code, category, message, photo_path
                FROM security_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [EventRecord(*row) for row in rows]
