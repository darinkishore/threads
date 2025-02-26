# Threads v0.1

A minimal CLI tool to create and manage "research threads" — each thread is a question or topic you explore, to which you can attach text or URLs. This helps you keep track of your context and reduce tab overload.

## Installation

```bash
git clone https://github.com/darinkishore/threads.git
cd threads
uv install --tool -e .
# or
pip install -e . 
```

## Commands

- **`thread new "question"`**
  Creates a new thread with the provided question or title.

- **`thread attach "content"`**
  Attaches the given text or URL to an existing thread via an interactive picker (shows last 5 threads).
  If you omit `"content"`, it will read from your clipboard (if it only contains text).

- **`thread ls [--all]`**
  Lists threads, showing ID, title, resource count, and last active time.
  Use `--all` to include archived threads.

- **`thread view [id]`**
  Displays a single thread's details: question, timestamps, and a list of resources.

- **`thread current [--all]`**
  Shows the single most recently active thread in the same format as `thread view`.
  Use `--all` to consider archived threads.

- **`thread archive [id]`**
  Archives a thread to hide it from the default listing.

- **`thread unarchive [id]`**
  Unarchives a thread to make it active again.

## Database

Threads stores data in SQLite under `~/.config/threads/threads.db` by default.
Automatic backups are created in `~/.config/threads/backups/` when the database is accessed.

## Future Plans

- Browser extension to attach current tab directly.
- Potential AI features (e.g., summarizing threads, auto-categorization).
- Daemon-based approach or advanced "restore/focus" flows.

Enjoy using Threads!