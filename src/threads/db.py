import os
import sqlite3
import time
from typing import List, Tuple, Optional

DEFAULT_DB_PATH = os.path.expanduser("~/.config/threads/threads.db")

def ensure_db_exists(db_path: str = DEFAULT_DB_PATH) -> None:
    """Ensure the SQLite database and tables exist, creating if necessary."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create threads table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT NOT NULL,
        created_at REAL NOT NULL,
        last_active REAL NOT NULL
    )
    """)

    # Create resources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER NOT NULL,
        type TEXT NOT NULL,     -- e.g. 'url' or 'text'
        content TEXT NOT NULL,
        added_at REAL NOT NULL,
        FOREIGN KEY(thread_id) REFERENCES threads(id)
    )
    """)

    conn.commit()
    conn.close()

def create_thread(question: str, db_path: str = DEFAULT_DB_PATH) -> int:
    """Create a new thread with a given question. Returns the new thread's ID."""
    ensure_db_exists(db_path)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO threads (question, created_at, last_active)
    VALUES (?, ?, ?)
    """, (question, timestamp, timestamp))
    thread_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thread_id

def list_threads(db_path: str = DEFAULT_DB_PATH, limit: int = 10) -> List[Tuple[int, str, int, float]]:
    """
    Returns a list of threads, each entry is (thread_id, question, resource_count, last_active).
    Limited by `limit`, sorted by last_active desc.
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.id, t.question,
           (SELECT COUNT(*) FROM resources r WHERE r.thread_id = t.id) as resource_count,
           t.last_active
    FROM threads t
    ORDER BY t.last_active DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_thread_by_id(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Tuple[int, str, float, float]]:
    """
    Returns (id, question, created_at, last_active) for a thread, or None if not found.
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, question, created_at, last_active
    FROM threads
    WHERE id = ?
    """, (thread_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_most_recent_thread(db_path: str = DEFAULT_DB_PATH) -> Optional[Tuple[int, str, float, float]]:
    """Return the single most recently active thread (or None if no threads)."""
    threads = list_threads(db_path=db_path, limit=1)
    if not threads:
        return None
    # threads[i] is (thread_id, question, resource_count, last_active)
    # We want (id, question, created_at, last_active) from get_thread_by_id, so let's do extra query:
    t_id = threads[0][0]
    return get_thread_by_id(t_id, db_path)

def get_last_n_threads(db_path: str = DEFAULT_DB_PATH, n: int = 5) -> List[Tuple[int, str, float]]:
    """
    Returns last n active threads for picking. Each entry is (id, question, last_active).
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT t.id, t.question, t.last_active
    FROM threads t
    ORDER BY t.last_active DESC
    LIMIT ?
    """, (n,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def attach_resource(thread_id: int, content: str, resource_type: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Attaches a resource to a thread and updates the thread's last_active.
    """
    ensure_db_exists(db_path)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Insert resource
    cursor.execute("""
    INSERT INTO resources (thread_id, type, content, added_at)
    VALUES (?, ?, ?, ?)
    """, (thread_id, resource_type, content, timestamp))
    # Update last_active
    cursor.execute("""
    UPDATE threads SET last_active = ? WHERE id = ?
    """, (timestamp, thread_id))
    conn.commit()
    conn.close()

def get_resources_for_thread(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> List[Tuple[int, str, str, float]]:
    """
    Returns a list of resources for the given thread, sorted by added_at ascending.
    Each row is (resource_id, type, content, added_at).
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, type, content, added_at
    FROM resources
    WHERE thread_id = ?
    ORDER BY added_at ASC
    """, (thread_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_thread_last_active(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Updates the thread's last_active time (used e.g. when viewing).
    """
    ensure_db_exists(db_path)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE threads SET last_active = ? WHERE id = ?
    """, (timestamp, thread_id))
    conn.commit()
    conn.close()
