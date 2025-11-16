import os
import sqlite3
from contextlib import contextmanager

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db.sqlite3")

def ensure_db_path():
    data_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

@contextmanager
def get_conn(path=None):
    ensure_db_path()
    conn = sqlite3.connect(path or DB_FILE, timeout=30)
    try:
        yield conn
    finally:
        conn.close()

def init_db(path=None):
    """
    Create required tables if they do not exist.
    """
    with get_conn(path) as conn:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_uuid TEXT,
            question_index INTEGER,
            selected_answer INTEGER,
            correct_answer INTEGER,
            time_spent_sec INTEGER,
            hint_count INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def log_attempt(attempt_uuid, question_index, selected_answer, correct_answer,
                time_spent_sec, hint_count=0, path=None):
    """
    Insert a row recording a question attempt.
    selected_answer/correct_answer: 0..3 for A..D, or None.
    """
    with get_conn(path) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO attempts (attempt_uuid, question_index, selected_answer, correct_answer, time_spent_sec, hint_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (attempt_uuid, question_index, selected_answer, correct_answer, time_spent_sec, hint_count))
        conn.commit()
        return cur.lastrowid

def get_attempts_for_attempt_id(attempt_uuid, path=None):
    """
    Return list of dict rows for a given attempt_uuid ordered by question_index.
    """
    with get_conn(path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT question_index, selected_answer, correct_answer, time_spent_sec, hint_count, timestamp
            FROM attempts
            WHERE attempt_uuid = ?
            ORDER BY question_index
        """, (attempt_uuid,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

def clear_attempts_for_attempt_id(attempt_uuid, path=None):
    with get_conn(path) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM attempts WHERE attempt_uuid = ?", (attempt_uuid,))
        conn.commit()