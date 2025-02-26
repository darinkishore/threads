import time
from unittest.mock import patch, MagicMock

import pytest
from rich.console import Console

from threads.cli import (
    cmd_new,
    cmd_view,
    cmd_current,
    cmd_ls,
    guess_resource_type,
    time_since,
    parse_args,
)


def test_parse_args():
    """Test the command line argument parser."""
    # Test basic command
    command, known_flags, unknown_flags = parse_args(["thread", "new"])
    assert command == "new"
    assert known_flags == []
    assert unknown_flags == []
    
    # Test with flags
    command, known_flags, unknown_flags = parse_args(
        ["thread", "new", "My Question", "--deep", "--tag1", "--tag2"]
    )
    assert command == "new"
    assert known_flags == ["--deep"]
    assert unknown_flags == ["tag1", "tag2"]


def test_guess_resource_type():
    """Test resource type detection."""
    # URL detection
    assert guess_resource_type("https://example.com") == "url"
    assert guess_resource_type("http://test.org/page") == "url"
    
    # Text detection
    assert guess_resource_type("This is just plain text") == "text"
    assert guess_resource_type("Notes about the topic") == "text"


def test_time_since():
    """Test the time formatter."""
    now = time.time()
    
    # Test seconds
    assert time_since(now - 30) == "30s"
    
    # Test minutes
    assert time_since(now - 120) == "2m"
    
    # Test hours
    assert time_since(now - 7200) == "2h"
    
    # Test days
    assert time_since(now - 172800) == "2d"


@patch("threads.cli.create_thread")
@patch("threads.cli.console")
def test_cmd_new(mock_console, mock_create_thread):
    """Test the new thread command."""
    mock_create_thread.return_value = 42
    
    result = cmd_new("Test Question")
    
    # Verify create_thread was called
    mock_create_thread.assert_called_once_with("Test Question")
    
    # Verify output
    mock_console.print.assert_called_once()
    assert "42" in mock_console.print.call_args[0][0]
    
    # Verify return value
    assert result == 42


@patch("threads.cli.get_thread_by_id")
@patch("threads.cli.get_resources_for_thread")
@patch("threads.cli.get_tags_for_thread")
@patch("threads.cli.update_thread_last_active")
@patch("threads.cli.console")
def test_cmd_view(
    mock_console, 
    mock_update_last_active,
    mock_get_tags,
    mock_get_resources,
    mock_get_thread
):
    """Test the view thread command."""
    # Mock data
    thread_id = 42
    mock_get_thread.return_value = (thread_id, "Test Question", time.time(), time.time(), False)
    mock_get_tags.return_value = ["important", "research"]
    mock_get_resources.return_value = [
        (1, "url", "https://example.com", time.time()),
        (2, "text", "Some notes", time.time()),
    ]
    
    # Call function
    cmd_view(thread_id)
    
    # Verify thread was fetched
    mock_get_thread.assert_called_once_with(thread_id)
    
    # Verify last_active was updated
    mock_update_last_active.assert_called_once_with(thread_id)
    
    # Verify tags were fetched
    mock_get_tags.assert_called_once_with(thread_id)
    
    # Verify resources were fetched
    mock_get_resources.assert_called_once_with(thread_id)
    
    # Verify output
    assert mock_console.print.call_count >= 5  # Multiple print calls