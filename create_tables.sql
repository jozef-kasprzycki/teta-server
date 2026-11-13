CREATE TABLE IF NOT EXISTS users (
    id           VARCHAR(255) NOT NULL,
    username     VARCHAR(255) NOT NULL,
    pub_key      TEXT         NOT NULL,
    passwd_hash  TEXT         NOT NULL,
    created_at   TEXT,
    ips          TEXT,
    last_login   TEXT,
    last_fetch   TEXT,
    PRIMARY KEY (id),
    UNIQUE (username)
);

CREATE TABLE IF NOT EXISTS chats (
    id          VARCHAR(255) NOT NULL,
    name        TEXT         NOT NULL,
    created_by  TEXT         NOT NULL,
    created_at  TEXT         NOT NULL,
    members     TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS messages (
    id                VARCHAR(255) NOT NULL,
    chat_id           TEXT         NOT NULL,
    sender_id         TEXT         NOT NULL,
    date_sender_sent  TEXT,
    content           TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tokens (
    id           VARCHAR(255) NOT NULL,
    token        TEXT         NOT NULL,
    user_id      TEXT         NOT NULL,
    expiry_date  TEXT         NOT NULL,
    PRIMARY KEY (id)
);
