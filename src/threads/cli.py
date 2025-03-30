import sys
import time

import pyperclip
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .db import (
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


console = Console()


def parse_args(args: list[str]) -> tuple[str, list[str], list[str]]:
    """Parse command and extract flags.
    Returns (command, known_flags, unknown_flags)
    Known flags are --deep, --all
    """
    command = args[1].lower() if len(args) > 1 else ''
    known_flags = []
    unknown_flags = []

    for arg in args[2:]:
        if arg.startswith('--'):
            if arg in ['--deep', '--all']:
                known_flags.append(arg)
            else:
                # Strip -- prefix for tag name
                unknown_flags.append(arg[2:])

    return command, known_flags, unknown_flags


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command, known_flags, unknown_flags = parse_args(sys.argv)

    if command == 'new':
        if len(sys.argv) < 3:
            console.print('[red]Error:[/red] No question specified.')
            sys.exit(1)
        # Get the question by joining all non-flag arguments after "new"
        question_parts = []
        for arg in sys.argv[2:]:
            if not arg.startswith('--'):
                question_parts.append(arg)
        question = ' '.join(question_parts)
        thread_id = cmd_new(question)

        # Add any unknown flags as tags
        for tag in unknown_flags:
            add_tag(thread_id, tag)
        if '--deep' in known_flags:
            add_tag(thread_id, 'deep')

    elif command == 'attach':
        # e.g. thread attach "something"
        # if none provided, read from clipboard
        content_parts = []
        for arg in sys.argv[2:]:
            if not arg.startswith('--'):
                content_parts.append(arg)
        content = ' '.join(content_parts) if content_parts else ''

        if not content.strip():
            # try reading from clipboard
            clip = pyperclip.paste()
            if clip and isinstance(clip, str):
                content = clip.strip()
            else:
                console.print(
                    '[red]Error:[/red] No content passed and clipboard empty.'
                )
                sys.exit(1)
        thread_id = cmd_attach(content)

        # Add any unknown flags as tags
        if thread_id:
            for tag in unknown_flags:
                add_tag(thread_id, tag)
            if '--deep' in known_flags:
                add_tag(thread_id, 'deep')

    elif command == 'ls':
        # Check for --all flag to show archived threads
        include_archived = '--all' in known_flags
        cmd_ls(include_archived)

    elif command == 'archive':
        # thread archive [id]
        thread_id = get_thread_id_from_args()
        cmd_archive(thread_id)

    elif command == 'unarchive':
        # thread unarchive [id]
        thread_id = get_thread_id_from_args()
        cmd_unarchive(thread_id)

    elif command == 'view':
        # thread view [id]
        thread_id = get_thread_id_from_args()
        cmd_view(thread_id)

    elif command == 'current':
        # Check for --all flag to potentially include archived threads
        include_archived = '--all' in known_flags
        cmd_current(include_archived)

    elif command == 'export':
        # thread export [id]
        thread_id = get_thread_id_from_args()
        cmd_export(thread_id)

    else:
        print_help()


def get_thread_id_from_args() -> int:
    """Parse thread ID from command line arguments."""
    thread_id = None
    for arg in sys.argv[2:]:
        if not arg.startswith('--'):
            if not arg.isdigit():
                console.print('[red]Error:[/red] Thread ID must be an integer.')
                sys.exit(1)
            thread_id = int(arg)
            break

    if thread_id is None:
        console.print('[red]Error:[/red] No thread ID specified.')
        sys.exit(1)

    return thread_id


def print_help():
    console.print('[bold cyan]Threads v0.1 commands:[/bold cyan]')
    console.print('  thread new "question text" [--deep] [--tag1] [--tag2] ...')
    console.print(
        '  thread attach "content" [--deep] [--tag1] [--tag2] ...  (uses interactive picker)'
    )
    console.print('  thread ls [--all]   (list threads, --all to include archived)')
    console.print("  thread view [id]  (view a thread's details)")
    console.print('  thread current [--all]  (view the most recently active thread)')
    console.print('  thread archive [id]  (archive a thread)')
    console.print('  thread unarchive [id]  (unarchive a thread)')
    console.print('  thread export [id]  (export a thread to clipboard)')
    console.print('')
    console.print('[dim]Flags:[/dim]')
    console.print('  --deep            Mark thread as requiring deep analysis')
    console.print('  --all             Include archived threads in listing/current')
    console.print('  --tag1, --tag2    Any flag starting with -- becomes a tag')


def cmd_new(question: str) -> int:
    thread_id = create_thread(question)
    console.print(f'[green]Created new thread (#{thread_id}):[/green] "{question}"')
    return thread_id


def cmd_attach(content: str) -> int | None:
    # Show an interactive picker with the last 5 active threads
    recent = get_last_n_threads(n=5, include_archived=False)
    console.print('[bold cyan]Recent Threads[/bold cyan]')
    for i, row in enumerate(recent, start=1):
        # row = (id, question, last_active, is_archived)
        t_id, t_question, t_last_active, is_archived = row
        ago = time_since(t_last_active)
        # Get tags
        tags = get_tags_for_thread(t_id)
        tags_str = f' [{", ".join(tags)}]' if tags else ''
        status = ' [yellow]ARCHIVED[/yellow]' if is_archived else ''
        console.print(
            f'  [bold]{i}.[/bold] (#{t_id}) "{t_question}"{tags_str}{status} [dim]{ago} ago[/dim]'
        )
    console.print('  [bold]n.[/bold] New thread')
    console.print('')

    choice = Prompt.ask(
        "[bold white]Select a thread or 'n' to create new[/bold white]", default='1'
    )

    if choice.lower() == 'n':
        new_question = Prompt.ask('[bold]Enter a new thread question/title[/bold]')
        new_thread_id = create_thread(new_question)
        # Attach this resource to new thread
        rtype = guess_resource_type(content)
        attach_resource(new_thread_id, content, rtype)
        console.print(
            f'[green]Attached resource to new thread (#{new_thread_id}):[/green] "{new_question}"'
        )
        return new_thread_id
    else:
        # Try parse as integer index
        try:
            idx = int(choice)
            if idx < 1 or idx > len(recent):
                console.print('[red]Invalid choice.[/red]')
                return None
            selected = recent[idx - 1]
            selected_id = selected[0]

            # Check if thread is archived
            if selected[3]:  # is_archived
                console.print(
                    f'[yellow]Warning: Thread #{selected_id} is archived.[/yellow]'
                )
                if (
                    not Prompt.ask(
                        '[bold]Attach to archived thread anyway? (y/n)[/bold]',
                        choices=['y', 'n'],
                        default='n',
                    )
                    == 'y'
                ):
                    return None

            rtype = guess_resource_type(content)
            attach_resource(selected_id, content, rtype)
            console.print(f'[green]Attached resource to thread #{selected_id}[/green]')
            return selected_id
        except ValueError:
            console.print('[red]Invalid input.[/red]')
            return None


def cmd_ls(include_archived: bool = False):
    threads = list_threads(
        limit=50, include_archived=include_archived
    )  # default 50, can be changed
    if not threads:
        console.print('[dim]No threads found.[/dim]')
        return

    table = Table(title='Threads (by last active)', show_lines=False)
    table.add_column('ID', style='bold')
    table.add_column('Question/Title', style='cyan')
    table.add_column('Tags', style='yellow')
    table.add_column('Resources', style='magenta')
    table.add_column('Last Active', style='dim')
    table.add_column('Status', style='yellow')

    for t_id, question, resource_count, last_active, is_archived in threads:
        ago = time_since(last_active)
        tags = get_tags_for_thread(t_id)
        tags_str = ', '.join(tags) if tags else ''
        status = '[yellow]Archived[/yellow]' if is_archived else 'Active'
        table.add_row(
            str(t_id), question, tags_str, str(resource_count), f'{ago} ago', status
        )
    console.print(table)


def cmd_archive(thread_id: int):
    """Archive a thread."""
    thread = get_thread_by_id(thread_id)
    if not thread:
        console.print(f'[red]Error:[/red] Thread #{thread_id} not found.')
        return

    # Check if already archived
    if thread[4]:  # is_archived field
        console.print(f'[yellow]Thread #{thread_id} is already archived.[/yellow]')
        return

    success = archive_thread(thread_id)
    if success:
        console.print(f'[green]Thread #{thread_id} has been archived.[/green]')
    else:
        console.print(f'[red]Error:[/red] Could not archive thread #{thread_id}.')


def cmd_unarchive(thread_id: int):
    """Unarchive a thread."""
    thread = get_thread_by_id(thread_id)
    if not thread:
        console.print(f'[red]Error:[/red] Thread #{thread_id} not found.')
        return

    # Check if already active
    if not thread[4]:  # is_archived field
        console.print(
            f'[yellow]Thread #{thread_id} is already active (not archived).[/yellow]'
        )
        return

    success = unarchive_thread(thread_id)
    if success:
        console.print(f'[green]Thread #{thread_id} has been unarchived.[/green]')
    else:
        console.print(f'[red]Error:[/red] Could not unarchive thread #{thread_id}.')


def cmd_view(thread_id: int):
    thread_data = get_thread_by_id(thread_id)
    if not thread_data:
        console.print(f'[red]Error:[/red] Thread #{thread_id} not found.')
        return

    t_id, t_question, t_created, t_last_active, t_is_archived = thread_data
    # Mark thread as viewed -> update last_active
    update_thread_last_active(t_id)

    resources = get_resources_for_thread(t_id)
    tags = get_tags_for_thread(t_id)

    status = '[yellow]ARCHIVED[/yellow]' if t_is_archived else ''
    console.print(f'[blue bold]Thread #{t_id}[/blue bold]: "{t_question}" {status}')
    if tags:
        console.print(f'[yellow]Tags:[/yellow] {", ".join(tags)}')
    console.print(f'Created: [dim]{time.ctime(t_created)}[/dim]')
    console.print(f'Last Active: [dim]{time.ctime(time.time())} (just updated)[/dim]\n')

    if not resources:
        console.print('[dim]No resources found for this thread.[/dim]')
        return

    console.print('[dim]Resources:[/dim]')
    for idx, (r_id, r_type, r_content, r_added) in enumerate(resources, start=1):
        console.print(f'  {idx}) [{r_type}] {r_content}')


def cmd_current(include_archived: bool = False):
    row = get_most_recent_thread(include_archived=include_archived)
    if not row:
        msg = (
            'No threads yet.'
            if include_archived
            else 'No active threads. Try --all to include archived threads.'
        )
        console.print(f'[dim]{msg}[/dim]')
        return

    t_id, t_question, t_created, t_last_active, t_is_archived = row
    # mark it viewed -> update last_active
    update_thread_last_active(t_id)
    resources = get_resources_for_thread(t_id)
    tags = get_tags_for_thread(t_id)

    status = '[yellow]ARCHIVED[/yellow]' if t_is_archived else ''
    console.print(f'[blue bold]Thread #{t_id}[/blue bold]: "{t_question}" {status}')
    if tags:
        console.print(f'[yellow]Tags:[/yellow] {", ".join(tags)}')
    console.print(f'Created: [dim]{time.ctime(t_created)}[/dim]')
    console.print(f'Last Active: [dim]{time.ctime(time.time())} (just updated)[/dim]\n')

    if not resources:
        console.print('[dim]No resources found for this thread.[/dim]')
        return

    console.print('[dim]Resources:[/dim]')
    for idx, (r_id, r_type, r_content, r_added) in enumerate(resources, start=1):
        console.print(f'  {idx}) [{r_type}] {r_content}')


def cmd_export(thread_id: int) -> None:
    """Export a thread to clipboard in a formatted way."""
    thread_data = get_thread_by_id(thread_id)
    if not thread_data:
        console.print(f'[red]Error:[/red] Thread #{thread_id} not found.')
        return

    t_id, t_question, t_created, t_last_active, t_is_archived = thread_data
    resources = get_resources_for_thread(t_id)
    tags = get_tags_for_thread(t_id)

    # Format the thread data into a pretty string
    status = 'ARCHIVED' if t_is_archived else 'ACTIVE'
    timestamp = time.ctime(t_created)

    # Build the export string
    export_lines = [
        f'# Thread #{t_id}: {t_question}',
        f'Status: {status}',
        f'Created: {timestamp}',
    ]

    if tags:
        export_lines.append(f'Tags: {", ".join(tags)}')

    if resources:
        export_lines.append('\n## Resources:')
        for idx, (r_id, r_type, r_content, r_added) in enumerate(resources, start=1):
            r_time = time.ctime(r_added)
            export_lines.append(f'### {idx}. [{r_type.upper()}] - {r_time}')
            export_lines.append(f'{r_content}\n')

    # Join all lines with newlines
    export_content = '\n'.join(export_lines)

    # Copy to clipboard
    pyperclip.copy(export_content)

    # Inform the user
    console.print(f'[green]Thread #{t_id} has been exported to clipboard.[/green]')
    console.print('[dim]Preview:[/dim]')
    console.print(export_content)


def guess_resource_type(content: str) -> str:
    # Very minimal check for URL or text
    # In v0.1: "url" if starts with http/https, else "text"
    if content.strip().lower().startswith('http'):
        return 'url'
    return 'text'


def time_since(timestamp: float) -> str:
    """Return a short string like '2m', '3h' or '1d' representing time since `timestamp`."""
    diff = time.time() - timestamp
    if diff < 60:
        return f'{int(diff)}s'
    elif diff < 3600:
        return f'{int(diff // 60)}m'
    elif diff < 86400:
        return f'{int(diff // 3600)}h'
    else:
        return f'{int(diff // 86400)}d'
