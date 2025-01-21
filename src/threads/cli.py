import sys
import time
import pyperclip
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from .db import (
    create_thread,
    attach_resource,
    list_threads,
    get_thread_by_id,
    get_resources_for_thread,
    get_last_n_threads,
    get_most_recent_thread,
    update_thread_last_active,
)

console = Console()


def main():
    # Simple argument parser approach
    # Usage:
    #   thread new "question"
    #   thread attach "thing"
    #   thread ls
    #   thread view [thread_id]
    #   thread current

    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "new":
        if len(sys.argv) < 3:
            console.print("[red]Error:[/red] No question specified.")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        cmd_new(question)

    elif command == "attach":
        # e.g. thread attach "something"
        # if none provided, read from clipboard
        content = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not content.strip():
            # try reading from clipboard
            clip = pyperclip.paste()
            if clip and isinstance(clip, str):
                content = clip.strip()
            else:
                console.print(
                    "[red]Error:[/red] No content passed and clipboard empty."
                )
                sys.exit(1)
        cmd_attach(content)

    elif command == "ls":
        cmd_ls()

    elif command == "view":
        # thread view [id]
        if len(sys.argv) < 3:
            console.print("[red]Error:[/red] No thread ID specified.")
            sys.exit(1)
        thread_id_str = sys.argv[2]
        if not thread_id_str.isdigit():
            console.print("[red]Error:[/red] Thread ID must be an integer.")
            sys.exit(1)
        cmd_view(int(thread_id_str))

    elif command == "current":
        cmd_current()

    else:
        print_help()


def print_help():
    console.print("[bold cyan]Threads v0.1 commands:[/bold cyan]")
    console.print('  thread new "question text"')
    console.print('  thread attach "content"  (uses interactive picker)')
    console.print("  thread ls   (list threads)")
    console.print("  thread view [id]  (view a thread's details)")
    console.print("  thread current     (view the most recently active thread)")
    console.print("")


def cmd_new(question: str):
    thread_id = create_thread(question)
    console.print(f'[green]Created new thread (#{thread_id}):[/green] "{question}"')


def cmd_attach(content: str):
    # Show an interactive picker with the last 5 threads
    recent = get_last_n_threads(n=5)
    console.print("[bold cyan]Recent Threads[/bold cyan]")
    for i, row in enumerate(recent, start=1):
        # row = (id, question, last_active)
        t_id, t_question, t_last_active = row
        ago = time_since(t_last_active)
        console.print(
            f'  [bold]{i}.[/bold] (#{t_id}) "{t_question}" [dim]{ago} ago[/dim]'
        )
    console.print("  [bold]n.[/bold] New thread")
    console.print("")

    choice = Prompt.ask(
        "[bold white]Select a thread or 'n' to create new[/bold white]", default="1"
    )

    if choice.lower() == "n":
        # Make a new thread with the content as the question, or ask user for question?
        # The spec: "n" means "create a new thread with this resource"? The conversation varied,
        # but let's ask for a thread name for clarity:
        new_question = Prompt.ask("[bold]Enter a new thread question/title[/bold]")
        new_thread_id = create_thread(new_question)
        # Attach this resource to new thread
        rtype = guess_resource_type(content)
        attach_resource(new_thread_id, content, rtype)
        console.print(
            f'[green]Attached resource to new thread (#{new_thread_id}):[/green] "{new_question}"'
        )
    else:
        # Try parse as integer index
        try:
            idx = int(choice)
            if idx < 1 or idx > len(recent):
                console.print("[red]Invalid choice.[/red]")
                return
            selected = recent[idx - 1]
            selected_id = selected[0]
            rtype = guess_resource_type(content)
            attach_resource(selected_id, content, rtype)
            console.print(f"[green]Attached resource to thread #{selected_id}[/green]")
        except ValueError:
            console.print("[red]Invalid input.[/red]")


def cmd_ls():
    threads = list_threads(limit=50)  # default 50, can be changed
    if not threads:
        console.print("[dim]No threads found.[/dim]")
        return

    table = Table(title="Threads (by last active)", show_lines=False)
    table.add_column("ID", style="bold")
    table.add_column("Question/Title", style="cyan")
    table.add_column("Resources", style="magenta")
    table.add_column("Last Active", style="dim")

    for t_id, question, resource_count, last_active in threads:
        ago = time_since(last_active)
        table.add_row(str(t_id), question, str(resource_count), f"{ago} ago")
    console.print(table)


def cmd_view(thread_id: int):
    thread_data = get_thread_by_id(thread_id)
    if not thread_data:
        console.print(f"[red]Error:[/red] Thread #{thread_id} not found.")
        return

    t_id, t_question, t_created, t_last_active = thread_data
    # Mark thread as viewed -> update last_active
    update_thread_last_active(t_id)

    resources = get_resources_for_thread(t_id)
    console.print(f'[blue bold]Thread #{t_id}[/blue bold]: "{t_question}"')
    console.print(f"Created: [dim]{time.ctime(t_created)}[/dim]")
    console.print(f"Last Active: [dim]{time.ctime(time.time())} (just updated)[/dim]\n")

    if not resources:
        console.print("[dim]No resources found for this thread.[/dim]")
        return

    console.print("[dim]Resources:[/dim]")
    for idx, (r_id, r_type, r_content, r_added) in enumerate(resources, start=1):
        console.print(f"  {idx}) [{r_type}] {r_content}")


def cmd_current():
    row = get_most_recent_thread()
    if not row:
        console.print("[dim]No threads yet.[/dim]")
        return

    t_id, t_question, t_created, t_last_active = row
    # mark it viewed -> update last_active
    update_thread_last_active(t_id)
    resources = get_resources_for_thread(t_id)
    console.print(f'[blue bold]Thread #{t_id}[/blue bold]: "{t_question}"')
    console.print(f"Created: [dim]{time.ctime(t_created)}[/dim]")
    console.print(f"Last Active: [dim]{time.ctime(time.time())} (just updated)[/dim]\n")

    if not resources:
        console.print("[dim]No resources found for this thread.[/dim]")
        return

    console.print("[dim]Resources:[/dim]")
    for idx, (r_id, r_type, r_content, r_added) in enumerate(resources, start=1):
        console.print(f"  {idx}) [{r_type}] {r_content}")


def guess_resource_type(content: str) -> str:
    # Very minimal check for URL or text
    # In v0.1: "url" if starts with http/https, else "text"
    if content.strip().lower().startswith("http"):
        return "url"
    return "text"


def time_since(timestamp: float) -> str:
    """Return a short string like '2m', '3h' or '1d' representing time since `timestamp`."""
    diff = time.time() - timestamp
    if diff < 60:
        return f"{int(diff)}s"
    elif diff < 3600:
        return f"{int(diff // 60)}m"
    elif diff < 86400:
        return f"{int(diff // 3600)}h"
    else:
        return f"{int(diff // 86400)}d"
