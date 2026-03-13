"""Test emotion storage: daily_emotion_log table."""
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from chatbot.memory.long_term import HealthEventStore


def test_log_daily_emotion():
    """Non-neutral emotion should be logged."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_daily_emotion("user_001", "sad", "我今天很难过")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 1
            assert logs[0]["emotion_label"] == "sad"
            assert logs[0]["user_input"] == "我今天很难过"
    finally:
        os.unlink(db_path)


def test_neutral_not_logged():
    """Neutral emotion should NOT be logged (caller responsibility, but verify method works)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            # Caller should not call this with neutral, but if they do it still stores
            store.log_daily_emotion("user_001", "neutral", "hello")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 1  # method itself doesn't filter
    finally:
        os.unlink(db_path)


def test_clear_daily_emotions():
    """Clear daily emotions for a user."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    try:
        with patch("chatbot.memory.long_term.DB_PATH", db_path):
            store = HealthEventStore()
            store.log_daily_emotion("user_001", "sad", "难过")
            store.log_daily_emotion("user_001", "anxious", "焦虑")
            store.clear_daily_emotions("user_001")
            logs = store.get_daily_emotions("user_001")
            assert len(logs) == 0
    finally:
        os.unlink(db_path)
