import time
from unittest.mock import patch

from threads.cli import cmd_export


@patch('threads.cli.get_thread_by_id')
@patch('threads.cli.get_resources_for_thread')
@patch('threads.cli.get_tags_for_thread')
@patch('threads.cli.pyperclip.copy')
@patch('threads.cli.console')
def test_cmd_export(
    mock_console,
    mock_pyperclip_copy,
    mock_get_tags,
    mock_get_resources,
    mock_get_thread,
):
    """Test the export command functionality."""
    # Mock data
    thread_id = 42
    timestamp = time.time()
    mock_get_thread.return_value = (
        thread_id,
        'Test Question',
        timestamp,
        timestamp,
        False,
    )
    mock_get_tags.return_value = ['important', 'research']
    mock_get_resources.return_value = [
        (1, 'url', 'https://example.com', timestamp),
        (2, 'text', 'Some notes', timestamp),
    ]

    # Call function
    cmd_export(thread_id)

    # Verify thread was fetched
    mock_get_thread.assert_called_once_with(thread_id)

    # Verify tags were fetched
    mock_get_tags.assert_called_once_with(thread_id)

    # Verify resources were fetched
    mock_get_resources.assert_called_once_with(thread_id)

    # Verify clipboard was used
    mock_pyperclip_copy.assert_called_once()

    # Verify content format
    clipboard_content = mock_pyperclip_copy.call_args[0][0]
    assert f'Thread #{thread_id}' in clipboard_content
    assert 'Test Question' in clipboard_content
    assert 'Status: ACTIVE' in clipboard_content
    assert 'important' in clipboard_content
    assert 'research' in clipboard_content
    assert 'URL' in clipboard_content
    assert 'TEXT' in clipboard_content
    assert 'https://example.com' in clipboard_content
    assert 'Some notes' in clipboard_content

    # Verify console output
    assert mock_console.print.call_count >= 2


@patch('threads.cli.get_thread_by_id')
@patch('threads.cli.console')
def test_cmd_export_thread_not_found(mock_console, mock_get_thread):
    """Test the export command when thread is not found."""
    # Mock data
    thread_id = 999
    mock_get_thread.return_value = None

    # Call function
    cmd_export(thread_id)

    # Verify thread was fetched
    mock_get_thread.assert_called_once_with(thread_id)

    # Verify error message
    mock_console.print.assert_called_once()
    error_msg = mock_console.print.call_args[0][0]
    assert 'Error' in error_msg
    assert f'Thread #{thread_id} not found' in error_msg
