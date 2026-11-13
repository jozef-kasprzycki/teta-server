import json
from datetime import datetime
from pathlib import Path

import mysql.connector
from mysql.connector import Error

import models
from utils import get_env

TABLES = ("users", "chats", "messages", "tokens")
SCHEMA_PATH = Path(__file__).with_name("create_tables.sql")


class Database:
    """Dostęp do MySQL. Metody publiczne zwracają obiekty z models."""

    def __init__(self) -> None:
        self.connection = mysql.connector.connect(
            host=get_env("DB_HOST"),
            database=get_env("DB_NAME"),
            user=get_env("DB_USER"),
            password=get_env("DB_PASSWORD"),
        )
        self.create_tables()

    def close(self) -> None:
        if self.connection is not None and self.connection.is_connected():
            self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _execute(self, query: str, params: tuple | None = None, *, fetch: str | None = None):
        if not self.connection.is_connected():
            self.connection.reconnect()

        cursor = self.connection.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(query, params or ())
            if fetch == "one":
                result = cursor.fetchone()
            elif fetch == "all":
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
            self.connection.commit()
            return result
        except Error:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _existing_tables(self) -> set[str]:
        placeholders = ", ".join(["%s"] * len(TABLES))
        rows = self._execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name IN ({placeholders})
            """,
            TABLES,
            fetch="all",
        )
        existing = set()
        for row in rows:
            name = next(value for key, value in row.items() if key.lower() == "table_name")
            existing.add(name)
        return existing

    def create_tables(self) -> None:
        """Tworzy brakujące tabele opisane w create_tables.sql."""
        if set(TABLES) <= self._existing_tables():
            return

        script = SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in (part.strip() for part in script.split(";")):
            if statement:
                self._execute(statement)

    @staticmethod
    def _to_db_datetime(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat(sep=" ")

    @staticmethod
    def _from_db_datetime(value: str | datetime | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    @staticmethod
    def _to_db_ips(ips: list[str] | None) -> str | None:
        if ips is None:
            return None
        return json.dumps(ips)

    @staticmethod
    def _from_db_ips(value: str | None) -> list[str] | None:
        if value is None:
            return None
        parsed = json.loads(value)
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("Kolumna ips musi zawierać tablicę JSON napisów")
        return parsed

    def _user_from_row(self, row: dict) -> models.User:
        return models.User(
            id=row["id"],
            username=row["username"],
            pub_key=row["pub_key"],
            passwd_hash=row["passwd_hash"],
            created_at=self._from_db_datetime(row["created_at"]),
            ips=self._from_db_ips(row["ips"]),
            last_login=self._from_db_datetime(row["last_login"]),
            last_fetch=self._from_db_datetime(row["last_fetch"]),
        )

    def _message_from_row(self, row: dict) -> models.Message:
        return models.Message(
            id=row["id"],
            chat_id=row["chat_id"],
            sender_id=row["sender_id"],
            date_sender_sent=self._from_db_datetime(row["date_sender_sent"]),
            content=row["content"],
        )

    def _token_from_row(self, row: dict) -> models.Token:
        expiry = self._from_db_datetime(row["expiry_date"])
        if expiry is None:
            raise ValueError("Token nie ma daty wygaśnięcia")
        return models.Token(
            id=row["id"],
            token=row["token"],
            user_id=row["user_id"],
            expiry_date=expiry,
        )

    def get_user(self, user_id: str) -> models.User | None:
        row = self._execute(
            """
            SELECT id, username, pub_key, passwd_hash, created_at, ips, last_login, last_fetch
            FROM users
            WHERE id = %s
            """,
            (user_id,),
            fetch="one",
        )
        if row is None:
            return None
        return self._user_from_row(row)

    def create_user(self, user: models.User) -> models.User:
        self._execute(
            """
            INSERT INTO users (
                id, username, pub_key, passwd_hash, created_at, ips, last_login, last_fetch
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user.id,
                user.username,
                user.pub_key,
                user.passwd_hash,
                self._to_db_datetime(user.created_at),
                self._to_db_ips(user.ips),
                self._to_db_datetime(user.last_login),
                self._to_db_datetime(user.last_fetch),
            ),
        )
        stored = self.get_user(user.id)
        if stored is None:
            raise RuntimeError(f"Użytkownik {user.id} nie został zapisany")
        return stored

    def get_message(self, message_id: str) -> models.Message | None:
        row = self._execute(
            """
            SELECT id, chat_id, sender_id, date_sender_sent, content
            FROM messages
            WHERE id = %s
            """,
            (message_id,),
            fetch="one",
        )
        if row is None:
            return None
        return self._message_from_row(row)

    def create_message(self, message: models.Message) -> models.Message:
        self._execute(
            """
            INSERT INTO messages (
                id, chat_id, sender_id, date_sender_sent, content
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                message.id,
                message.chat_id,
                message.sender_id,
                self._to_db_datetime(message.date_sender_sent),
                message.content,
            ),
        )
        stored = self.get_message(message.id)
        if stored is None:
            raise RuntimeError(f"Wiadomość {message.id} nie została zapisana")
        return stored

    def delete_message(self, message_id: str) -> models.Message | None:
        message = self.get_message(message_id)
        if message is None:
            return None
        self._execute("DELETE FROM messages WHERE id = %s", (message_id,))
        return message

    def get_token(self, token: str) -> models.Token | None:
        row = self._execute(
            """
            SELECT id, token, user_id, expiry_date
            FROM tokens
            WHERE token = %s
            """,
            (token,),
            fetch="one",
        )
        if row is None:
            return None
        return self._token_from_row(row)

    def create_token(self, token: models.Token) -> models.Token:
        self._execute(
            """
            INSERT INTO tokens (id, token, user_id, expiry_date)
            VALUES (%s, %s, %s, %s)
            """,
            (
                token.id,
                token.token,
                token.user_id,
                self._to_db_datetime(token.expiry_date),
            ),
        )
        stored = self.get_token(token.id)
        if stored is None:
            raise RuntimeError(f"Token {token.id} nie został zapisany")
        return stored
