import os
import shutil
import sqlite3
import time
from datetime import datetime


DEFAULT_DB_PATH = os.path.expanduser('~/.config/threads/threads.db')
DEFAULT_BACKUP_DIR = os.path.expanduser('~/.config/threads/backups')


def _get_db_version(cursor: sqlite3.Cursor) -> int:
    """Get the current database version."""
    try:
        cursor.execute('SELECT version FROM schema_version')
        return cursor.fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def _set_db_version(cursor: sqlite3.Cursor, version: int) -> None:
    """Set the database version."""
    cursor.execute(
        'INSERT OR REPLACE INTO schema_version (id, version) VALUES (1, ?)', (version,)
    )


def _run_migration_1(cursor: sqlite3.Cursor) -> None:
    """Add tags support"""
    # Create schema_version table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_version (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        version INTEGER NOT NULL
    )
    """)

    # Create tags table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at REAL NOT NULL,
        FOREIGN KEY(thread_id) REFERENCES threads(id),
        UNIQUE(thread_id, name)
    )
    """)

    _set_db_version(cursor, 1)


def _run_migration_2(cursor: sqlite3.Cursor) -> None:
    """Add archive support for threads"""
    # Add is_archived column to threads table
    cursor.execute(
        'ALTER TABLE threads ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0'
    )
    _set_db_version(cursor, 2)


def backup_database(
    db_path: str = DEFAULT_DB_PATH, backup_dir: str = DEFAULT_BACKUP_DIR
) -> str:
    """
    Create a backup of the database.
    Returns the path to the backup file or empty string if backup failed.
    """
    try:
        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_filename = os.path.basename(db_path)
        backup_filename = f'{os.path.splitext(db_filename)[0]}_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)

        # Copy database file to backup location
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            return backup_path
    except (PermissionError, OSError):
        # Log error or simply continue without backup on permission issues
        pass
    return ''


def ensure_db_exists(
    db_path: str = DEFAULT_DB_PATH, create_backup: bool = False
) -> None:
    """
    Ensure the SQLite database and tables exist, creating if necessary.
    Only create backup when create_backup=True (for write operations).
    """
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Create a backup if the database already exists and backup was requested
    if create_backup and os.path.exists(db_path):
        backup_database(db_path)

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

    # Run migrations if needed
    version = _get_db_version(cursor)
    if version < 1:
        _run_migration_1(cursor)
    if version < 2:
        _run_migration_2(cursor)

    conn.commit()
    conn.close()


def create_thread(question: str, db_path: str = DEFAULT_DB_PATH) -> int:
    """Create a new thread with a given question. Returns the new thread's ID."""
    ensure_db_exists(db_path, create_backup=True)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
    INSERT INTO threads (question, created_at, last_active)
    VALUES (?, ?, ?)
    """,
        (question, timestamp, timestamp),
    )
    thread_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return thread_id


def list_threads(
    db_path: str = DEFAULT_DB_PATH, limit: int = 10, include_archived: bool = False
) -> list[tuple[int, str, int, float, bool]]:
    """
    Returns a list of threads, each entry is (thread_id, question, resource_count, last_active, is_archived).
    Limited by `limit`, sorted by last_active desc.
    By default, only non-archived threads are included unless include_archived is True.
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Only include active threads unless include_archived is True
    where_clause = '' if include_archived else 'WHERE t.is_archived = 0'

    cursor.execute(
        f"""
    SELECT t.id, t.question,
           (SELECT COUNT(*) FROM resources r WHERE r.thread_id = t.id) as resource_count,
           t.last_active, t.is_archived
    FROM threads t
    {where_clause}
    ORDER BY t.last_active DESC
    LIMIT ?
    """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_thread_by_id(
    thread_id: int, db_path: str = DEFAULT_DB_PATH
) -> tuple[int, str, float, float, bool] | None:
    """
    Returns (id, question, created_at, last_active, is_archived) for a thread, or None if not found.
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT id, question, created_at, last_active, is_archived
    FROM threads
    WHERE id = ?
    """,
        (thread_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_most_recent_thread(
    db_path: str = DEFAULT_DB_PATH,
    include_archived: bool = False,
) -> tuple[int, str, float, float, bool] | None:
    """
    Return the single most recently active thread (or None if no threads).
    By default, only considers non-archived threads unless include_archived is True.
    """
    threads = list_threads(db_path=db_path, limit=1, include_archived=include_archived)
    if not threads:
        return None
    # threads[i] is (thread_id, question, resource_count, last_active, is_archived)
    # We want (id, question, created_at, last_active, is_archived) from get_thread_by_id,
    # so let's do extra query:
    t_id = threads[0][0]
    return get_thread_by_id(t_id, db_path)


def get_last_n_threads(
    db_path: str = DEFAULT_DB_PATH, n: int = 5, include_archived: bool = False
) -> list[tuple[int, str, float, bool]]:
    """
    Returns last n active threads for picking.
    Each entry is (id, question, last_active, is_archived).
    By default, only returns non-archived threads unless include_archived is True.
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Only include active threads unless include_archived is True
    where_clause = '' if include_archived else 'WHERE t.is_archived = 0'

    cursor.execute(
        f"""
    SELECT t.id, t.question, t.last_active, t.is_archived
    FROM threads t
    {where_clause}
    ORDER BY t.last_active DESC
    LIMIT ?
    """,
        (n,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def attach_resource(
    thread_id: int, content: str, resource_type: str, db_path: str = DEFAULT_DB_PATH
) -> None:
    """
    Attaches a resource to a thread and updates the thread's last_active.
    """
    ensure_db_exists(db_path, create_backup=True)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Insert resource
    cursor.execute(
        """
    INSERT INTO resources (thread_id, type, content, added_at)
    VALUES (?, ?, ?, ?)
    """,
        (thread_id, resource_type, content, timestamp),
    )
    # Update last_active
    cursor.execute(
        """
    UPDATE threads SET last_active = ? WHERE id = ?
    """,
        (timestamp, thread_id),
    )
    conn.commit()
    conn.close()


def get_resources_for_thread(
    thread_id: int, db_path: str = DEFAULT_DB_PATH
) -> list[tuple[int, str, str, float]]:
    """
    Returns a list of resources for the given thread, sorted by added_at ascending.
    Each row is (resource_id, type, content, added_at).
    """
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT id, type, content, added_at
    FROM resources
    WHERE thread_id = ?
    ORDER BY added_at ASC
    """,
        (thread_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def update_thread_last_active(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Updates the thread's last_active time (used e.g. when viewing).
    """
    ensure_db_exists(db_path, create_backup=True)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
    UPDATE threads SET last_active = ? WHERE id = ?
    """,
        (timestamp, thread_id),
    )
    conn.commit()
    conn.close()


def add_tag(thread_id: int, tag_name: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Add a tag to a thread."""
    ensure_db_exists(db_path, create_backup=True)
    timestamp = time.time()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
        INSERT INTO tags (thread_id, name, created_at)
        VALUES (?, ?, ?)
        """,
            (thread_id, tag_name, timestamp),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        # Tag already exists for this thread, ignore
        pass
    finally:
        conn.close()


def get_tags_for_thread(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> list[str]:
    """Get all tags for a thread."""
    ensure_db_exists(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
    SELECT name FROM tags
    WHERE thread_id = ?
    ORDER BY name ASC
    """,
        (thread_id,),
    )
    tags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tags


def archive_thread(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Mark a thread as archived.
    Returns True if thread was found and archived, False otherwise.
    """
    ensure_db_exists(db_path, create_backup=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Mark thread as archived
    cursor.execute(
        """
    UPDATE threads SET is_archived = 1 WHERE id = ?
    """,
        (thread_id,),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def unarchive_thread(thread_id: int, db_path: str = DEFAULT_DB_PATH) -> bool:
    """
    Mark a thread as not archived.
    Returns True if thread was found and unarchived, False otherwise.
    """
    ensure_db_exists(db_path, create_backup=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Mark thread as not archived
    cursor.execute(
        """
    UPDATE threads SET is_archived = 0 WHERE id = ?
    """,
        (thread_id,),
    )

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success
