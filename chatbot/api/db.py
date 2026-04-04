"""Shared PostgreSQL connection helper."""
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        dbname=os.getenv("PG_DB"),
        connect_timeout=10,
    )
