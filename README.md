# Threads v0.1

A minimal CLI tool to create and manage "research threads" — each thread is a question or topic you explore, to which you can attach text or URLs. This helps you keep track of your context and reduce tab overload.

## Installation

```bash
# Using pip
pip install .
# or if published to PyPI eventually
pip install threads
```

## Commands

- **thread new "question"**
  Creates a new thread with the provided question or title.

- **thread attach "content"**
  Attaches the given text or URL to an existing thread via an interactive picker (shows last 5 threads).
  If you omit `"content"`, it will read from your clipboard (if it only contains text).

- **thread ls**
  Lists threads, showing ID, title, resource count, and last active time.

- **thread view [id]**
  Displays a single thread’s details: question, timestamps, and a list of resources.

- **thread current**
  Shows the single most recently active thread in the same format as `thread view`.

## Database

Threads stores data in SQLite under `~/.config/threadz/threads.db` by default.

## Future Plans

- Browser extension to attach current tab directly.
- Potential AI features (e.g., summarizing threads, auto-categorization).
- Daemon-based approach or advanced “restore/focus” flows.

Enjoy using Threads!