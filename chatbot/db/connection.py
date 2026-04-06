from __future__ import annotations
"""
chatbot/db/connection.py
PostgreSQL 连接池（psycopg2 SimpleConnectionPool）

用法：
    from chatbot.db.connection import get_conn, release_conn

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT ...")
            rows = cur.fetchall()
        conn.commit()
    finally:
        release_conn(conn)

或用上下文管理器：
    with db_cursor() as cur:
        cur.execute("SELECT ...")
"""
import os
import contextlib
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor

# 连接池单例
_pool: pg_pool.SimpleConnectionPool | None = None


def _build_pool() -> pg_pool.SimpleConnectionPool:
    return pg_pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.environ["PG_HOST"],
        port=int(os.environ.get("PG_PORT", 5432)),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        dbname=os.environ["PG_DB"],
        connect_timeout=10,
    )


def get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = _build_pool()
    return _pool


def get_conn():
    """从连接池获取一个连接。使用完后必须调用 release_conn()。"""
    return get_pool().getconn()


def release_conn(conn) -> None:
    """归还连接到池。"""
    if conn:
        get_pool().putconn(conn)


@contextlib.contextmanager
def db_cursor(commit: bool = False):
    """
    上下文管理器，自动获取/归还连接，返回 RealDictCursor（结果为 dict）。

    with db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
        row = cur.fetchone()   # → {"user_id": "...", "name": "..."}
    """
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
        else:
            conn.rollback()   # 只读查询，不提交
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)
