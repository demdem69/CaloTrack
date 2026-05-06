import os
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection as Connection


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None or val == "":
        raise RuntimeError(f"Missing environment variable: {name}")
    return val


def get_dsn() -> str:
    host = _env("DB_HOST")
    port = _env("DB_PORT", "14530")
    db = _env("DB_NAME", "defaultdb")
    user = _env("DB_USER")
    password = _env("DB_PASSWORD")
    sslmode = _env("DB_SSLMODE", "require")
    return f"host={host} port={port} dbname={db} user={user} password={password} sslmode={sslmode}"


def connect() -> Connection:
    return psycopg2.connect(get_dsn())


def session() -> Iterator[Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()

