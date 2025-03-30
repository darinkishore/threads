import time

import pytest

from threads.db import (
    add_tag,
    archive_thread,
    attach_resource,
    create_thread,
    get_last_n_threads,
    get_most_recent_thread,
    get_resources_for_thread,
    get_tags_for_thread,
    get_thread_by_id,
    list_threads,
    unarchive_thread,
    update_thread_last_active,
)


@pytest.fixture
def test_db(tmp_path):
    """Create a test database file."""
    db_path = tmp_path / 'test_threads.db'
    return str(db_path)


def test_create_thread(test_db):
    """Test creating a new thread."""
    thread_id = create_thread('Test Question', db_path=test_db)
    assert thread_id == 1

    # Create another thread
    thread_id = create_thread('Another Question', db_path=test_db)
    assert thread_id == 2


def test_get_thread_by_id(test_db):
    """Test retrieving a thread by ID."""
    thread_id = create_thread('Test Question', db_path=test_db)
    thread = get_thread_by_id(thread_id, db_path=test_db)

    assert thread is not None
    assert thread[0] == thread_id
    assert thread[1] == 'Test Question'
    assert isinstance(thread[2], float)  # created_at
    assert isinstance(thread[3], float)  # last_active


def test_list_threads(test_db):
    """Test listing threads."""
    # Create threads
    thread_id1 = create_thread('Question 1', db_path=test_db)
    thread_id2 = create_thread('Question 2', db_path=test_db)

    threads = list_threads(db_path=test_db)
    assert len(threads) == 2

    # Most recent should be listed first
    assert threads[0][0] == thread_id2
    assert threads[1][0] == thread_id1


def test_attach_resource(test_db):
    """Test attaching resources to a thread."""
    thread_id = create_thread('Test Question', db_path=test_db)

    # Attach a URL
    attach_resource(thread_id, 'https://example.com', 'url', db_path=test_db)

    # Attach text
    attach_resource(thread_id, 'Some notes about this topic', 'text', db_path=test_db)

    resources = get_resources_for_thread(thread_id, db_path=test_db)
    assert len(resources) == 2

    # Check resource types
    assert resources[0][1] == 'url'
    assert resources[1][1] == 'text'

    # Check content
    assert resources[0][2] == 'https://example.com'
    assert resources[1][2] == 'Some notes about this topic'


def test_get_most_recent_thread(test_db):
    """Test getting the most recent thread."""
    thread_id1 = create_thread('Question 1', db_path=test_db)
    time.sleep(0.1)  # Ensure timestamps are different
    thread_id2 = create_thread('Question 2', db_path=test_db)

    recent = get_most_recent_thread(db_path=test_db)
    assert recent is not None
    assert recent[0] == thread_id2

    # Update first thread
    update_thread_last_active(thread_id1, db_path=test_db)
    recent = get_most_recent_thread(db_path=test_db)
    assert recent[0] == thread_id1


def test_get_last_n_threads(test_db):
    """Test getting the last N threads."""
    for i in range(10):
        create_thread(f'Question {i + 1}', db_path=test_db)

    # Get last 5 threads
    threads = get_last_n_threads(db_path=test_db, n=5)
    assert len(threads) == 5

    # They should be in reverse order (newest first)
    assert threads[0][0] == 10  # Most recent thread ID
    assert threads[4][0] == 6  # Oldest of the 5


def test_tags(test_db):
    """Test tag functionality."""
    thread_id = create_thread('Test Question', db_path=test_db)

    # Add tags
    add_tag(thread_id, 'important', db_path=test_db)
    add_tag(thread_id, 'research', db_path=test_db)

    # Get tags
    tags = get_tags_for_thread(thread_id, db_path=test_db)
    assert len(tags) == 2
    assert 'important' in tags
    assert 'research' in tags

    # Test adding duplicate tag (should not raise an error)
    add_tag(thread_id, 'important', db_path=test_db)
    tags = get_tags_for_thread(thread_id, db_path=test_db)
    assert len(tags) == 2  # Still just 2 tags


def test_archive_unarchive(test_db):
    """Test archiving and unarchiving threads."""
    # Create two threads
    thread_id1 = create_thread('Question 1', db_path=test_db)
    thread_id2 = create_thread('Question 2', db_path=test_db)

    # Verify both are active (not archived)
    thread1 = get_thread_by_id(thread_id1, db_path=test_db)
    thread2 = get_thread_by_id(thread_id2, db_path=test_db)
    assert not thread1[4]  # is_archived is False
    assert not thread2[4]  # is_archived is False

    # Archive thread 1
    success = archive_thread(thread_id1, db_path=test_db)
    assert success

    # Verify thread 1 is now archived
    thread1 = get_thread_by_id(thread_id1, db_path=test_db)
    assert thread1[4]  # is_archived is True

    # Verify listing only shows thread 2 by default
    threads = list_threads(db_path=test_db, include_archived=False)
    assert len(threads) == 1
    assert threads[0][0] == thread_id2

    # Verify listing with include_archived shows both threads
    threads = list_threads(db_path=test_db, include_archived=True)
    assert len(threads) == 2

    # Unarchive thread 1
    success = unarchive_thread(thread_id1, db_path=test_db)
    assert success

    # Verify thread 1 is active again
    thread1 = get_thread_by_id(thread_id1, db_path=test_db)
    assert not thread1[4]  # is_archived is False

    # Verify listing shows both threads
    threads = list_threads(db_path=test_db)
    assert len(threads) == 2
