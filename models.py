from dataclasses import dataclass
from datetime import datetime

@dataclass
class Request:
    action: str
    token: str | None = None
    body: str | None = None


@dataclass
class User:
    id: str
    username: str
    pub_key: str
    passwd_hash: str
    created_at: datetime | None = None
    ips: list[str] | None = None
    last_login: datetime | None = None
    last_fetch: datetime | None = None


@dataclass
class Chat:
    id: str
    name: str
    created_by: str
    created_at: datetime
    members: list[str] | None = None


@dataclass
class Message:
    id: str
    chat_id: str
    sender_id: str.encode('utf-8')
    date_sender_sent: datetime | None = None
    content: str | None = None


@dataclass
class Token:
    id: str
    token: str
    user_id: str
    expiry_date: datetime

