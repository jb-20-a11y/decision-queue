#!/usr/bin/env python3
"""
timesheet.py - A simple CLI time-tracking tool that logs work sessions to a
CSV file and, when run inside a git repository, commits (and pushes, if a
remote is configured) each edit so the timesheet has an independently
verifiable, timestamped history.

Usage:
    python timesheet.py [start|stop|log|status|total] ["message"]

Commands:
    start   Record a START entry with the current timestamp.
    stop    Record a STOP entry with the current timestamp, then rewrite
            any configured files' total-time lines and commit everything
            together in one commit.
    log     Record a LOG entry with a custom message (message is required).
    status  Show whether a session is currently open and how much time
            remains against the configured limit. This is the default
            command if none is given.
    total   Show the total elapsed time across all sessions.

Configuration (edit the constants below):
    CSV_PATH            Path to the timesheet CSV file (relative to the
                         current directory).
    TIME_LIMIT_SECONDS  The time budget, in seconds.
    FILES_TO_UPDATE     Mapping of {file path: line-prefix}. On "stop",
                         the first line in each file that starts with
                         exactly that prefix is rewritten to
                         "<prefix><formatted total time>"; everything
                         else in the file is left untouched.
    TIME_FORMAT         Format string used for the total-time text
                         inserted into FILES_TO_UPDATE files. Supports
                         {h} and {m} placeholders (rounded to the
                         nearest whole minute).
    COMMIT_MESSAGE      Git commit message used for every timesheet
                         commit.
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

CSV_PATH = "timesheet.csv"

TIME_LIMIT_SECONDS = 60 * 60 * 6  # 6 hours

# {file_path: line_prefix}. On "stop", the first line in each file that
# begins with exactly `line_prefix` (ignoring \n vs \r\n) is replaced with
# `line_prefix + <formatted total>`. Everything else in the file, and the
# prefix text itself, is left untouched.
FILES_TO_UPDATE = {
    "README.md": "**Total Time:** ",
}

# {h} and {m} are replaced with rounded whole hours and minutes.
TIME_FORMAT = "{h} hours, {m} minutes"

COMMIT_MESSAGE = "Timesheet update"

CSV_HEADERS = ["Timestamp", "Command", "Comment"]

# --------------------------------------------------------------------------
# git support (optional; only used if the current directory is inside a
# git repository)
# --------------------------------------------------------------------------

try:
    from git import Repo
    from git.exc import InvalidGitRepositoryError, NoSuchPathError, GitCommandError
    _GIT_AVAILABLE = True
except ImportError:
    _GIT_AVAILABLE = False


def get_repo():
    """Return a git.Repo for the current directory (searching parent
    directories, like git itself does), or None if not inside a repo."""
    if not _GIT_AVAILABLE:
        return None
    try:
        return Repo(os.getcwd(), search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None


def check_git_preconditions(repo):
    """
    Return None if it's safe to make a new timesheet commit, or a
    human-readable string explaining why it isn't.

    Blocks if:
      - there are staged changes not yet committed, or
      - there's a configured upstream and local commits not yet pushed to it.
    """
    if repo is None:
        return None

    # 1. Staged-but-not-committed changes.
    if repo.head.is_valid():
        staged = repo.index.diff("HEAD")
        if len(staged) > 0:
            files = ", ".join(sorted(set(d.a_path or d.b_path for d in staged)))
            return (
                f"there are staged changes not yet committed ({files}). "
                "Commit or unstage them first."
            )
    else:
        # Repository has no commits yet (unborn branch).
        if len(list(repo.index.entries)) > 0:
            return (
                "there are staged changes not yet committed (repository has "
                "no commits yet). Commit or unstage them first."
            )

    # 2. Committed-but-not-pushed changes. This queries the remote
    #    directly (via ls-remote) rather than relying on a locally
    #    configured tracking branch, because a tracking branch may not be
    #    set up yet (e.g. right after "git remote add") even though the
    #    remote already has, or is missing, real commits. Relying on
    #    tracking_branch() alone would silently miss that case.
    if len(repo.remotes) > 0 and repo.head.is_valid():
        try:
            branch = repo.active_branch
        except TypeError:
            return "the repository is in a detached HEAD state"

        remote_names = [r.name for r in repo.remotes]
        remote_name = "origin" if "origin" in remote_names else remote_names[0]

        try:
            ls_output = repo.git.ls_remote(remote_name, branch.name)
        except GitCommandError as e:
            return f"could not reach remote '{remote_name}' to check push status ({e})"

        local_sha = repo.head.commit.hexsha
        if not ls_output.strip():
            return (
                f"branch '{branch.name}' does not exist yet on remote "
                f"'{remote_name}'. Push your existing work first so it "
                "doesn't get bundled into the timesheet commit."
            )
        remote_sha = ls_output.split()[0]
        if remote_sha != local_sha:
            return (
                f"local '{branch.name}' is not fully pushed to "
                f"'{remote_name}' yet (local commit {local_sha[:8]} vs. "
                f"remote {remote_sha[:8]}). Push first."
            )

    return None


def commit_and_push(repo, filepaths, message):
    """Stage exactly `filepaths` (absolute paths), commit, and push if a
    remote is configured. Raises RuntimeError on failure after the commit
    has already been made locally, so the caller can report state clearly."""
    abs_paths = [os.path.abspath(p) for p in filepaths]
    repo.index.add(abs_paths)
    try:
        # repo.git.commit streams output to the console by default in recent
        # GitPython versions when you don't capture it; to print explicitly:
        output = repo.git.commit('-m', message)
        if output:
            print(output)
    except GitCommandError as e:
        # e.stdout / e.stderr hold the hook output
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        raise RuntimeError(f"git commit failed (exit {e.status})") from e

    if len(repo.remotes) == 0:
        return  # nothing to push to

    try:
        branch = repo.active_branch
    except TypeError:
        raise RuntimeError(
            "committed locally, but cannot push from a detached HEAD"
        )

    remote_names = [r.name for r in repo.remotes]
    remote_name = "origin" if "origin" in remote_names else remote_names[0]
    tracking = branch.tracking_branch()

    try:
        if tracking is None:
            repo.git.push("--set-upstream", remote_name, branch.name)
        else:
            repo.git.push(remote_name, branch.name)
    except GitCommandError as e:
        raise RuntimeError(
            f"committed locally (commit {repo.head.commit.hexsha[:8]}), but "
            f"push to '{remote_name}' failed: {e}"
        )


# --------------------------------------------------------------------------
# CSV helpers
# --------------------------------------------------------------------------

def ensure_csv(path):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADERS)


def append_row(path, timestamp, command, comment=""):
    ensure_csv(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([timestamp, command, comment])


def read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# Time accounting
# --------------------------------------------------------------------------

def compute_elapsed(rows, as_of=None):
    """Walk rows in order; return (total_elapsed_timedelta,
    open_session_start_or_None). LOG rows and unmatched STOPs are ignored."""
    if as_of is None:
        as_of = datetime.now()
    total = timedelta()
    open_start = None
    for row in rows:
        cmd = (row.get("Command") or "").strip().upper()
        ts_raw = row.get("Timestamp")
        if not ts_raw:
            continue
        try:
            ts = datetime.fromisoformat(ts_raw)
        except ValueError:
            continue
        if cmd == "START":
            open_start = ts
        elif cmd == "STOP" and open_start is not None:
            total += ts - open_start
            open_start = None
    if open_start is not None:
        total += as_of - open_start
    return total, open_start


def format_duration_precise(td):
    """H:MM:SS, with a leading '-' if td is negative."""
    total_seconds = int(td.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{sign}{hours}:{minutes:02d}:{seconds:02d}"


def format_duration(td, fmt=None):
    """Round to the nearest whole minute and apply `fmt` (default
    TIME_FORMAT), which may use {h} and {m}."""
    if fmt is None:
        fmt = TIME_FORMAT
    total_minutes = round(td.total_seconds() / 60)
    sign = "-" if total_minutes < 0 else ""
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return sign + fmt.format(h=hours, m=minutes)


# --------------------------------------------------------------------------
# File rewriting (used on "stop")
# --------------------------------------------------------------------------

def update_file_with_time(filepath, prefix, time_str):
    """
    Find the first line in `filepath` that starts with exactly `prefix`
    (ignoring that line's ending) and replace it with `prefix + time_str`,
    preserving that line's original ending (\\n or \\r\\n) and leaving
    every other line untouched. Returns True if a line was rewritten.
    """
    if not os.path.exists(filepath):
        print(f"  (skipped {filepath}: file not found)")
        return False

    with open(filepath, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.endswith("\r\n"):
            content, ending = line[:-2], "\r\n"
        elif line.endswith("\n") or line.endswith("\r"):
            content, ending = line[:-1], line[-1]
        else:
            content, ending = line, ""
        if content.startswith(prefix):
            lines[i] = prefix + time_str + ending
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                f.write("".join(lines))
            return True

    print(f"  (skipped {filepath}: no line starting with {prefix!r} found)")
    return False


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def _run_csv_edit(repo, edit_fn):
    """Shared flow for start/log/stop: check preconditions, run edit_fn
    (performs the writes and returns the list of changed paths), then
    commit+push if inside a repo."""
    reason = check_git_preconditions(repo)
    if reason is not None:
        print(f"Refusing to edit the timesheet: {reason}", file=sys.stderr)
        sys.exit(1)

    changed = edit_fn()

    if repo is not None:
        try:
            commit_and_push(repo, changed, COMMIT_MESSAGE)
        except RuntimeError as e:
            print(f"Warning: {e}", file=sys.stderr)
            sys.exit(1)


def cmd_start(args):
    _, open_start = compute_elapsed(read_rows(CSV_PATH))
    if open_start is not None:
        print(
            f"A session is already open (started "
            f"{open_start.isoformat(timespec='seconds')}). Run 'stop' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    def edit():
        now = datetime.now()
        append_row(CSV_PATH, now.isoformat(timespec="microseconds"), "START", "")
        return [CSV_PATH]

    _run_csv_edit(get_repo(), edit)
    print("Started.")


def cmd_stop(args):
    _, open_start = compute_elapsed(read_rows(CSV_PATH))
    if open_start is None:
        print("No open session to stop.", file=sys.stderr)
        sys.exit(1)

    def edit():
        now = datetime.now()
        append_row(CSV_PATH, now.isoformat(timespec="microseconds"), "STOP", "")
        changed = [CSV_PATH]
        total, _ = compute_elapsed(read_rows(CSV_PATH), as_of=now)
        time_str = format_duration(total)
        for filepath, prefix in FILES_TO_UPDATE.items():
            if update_file_with_time(filepath, prefix, time_str):
                changed.append(filepath)
        return changed

    _run_csv_edit(get_repo(), edit)
    total, _ = compute_elapsed(read_rows(CSV_PATH))
    print(
        f"Stopped. Total elapsed: {format_duration_precise(total)} "
        f"({format_duration(total)})."
    )


def cmd_log(args):
    if not args.message:
        print("The 'log' command requires a message.", file=sys.stderr)
        sys.exit(1)

    def edit():
        now = datetime.now()
        append_row(
            CSV_PATH, now.isoformat(timespec="microseconds"), "LOG", args.message
        )
        return [CSV_PATH]

    _run_csv_edit(get_repo(), edit)
    print(f"Logged: {args.message}")


def cmd_status(args):
    now = datetime.now()
    elapsed, open_start = compute_elapsed(read_rows(CSV_PATH), as_of=now)
    remaining = timedelta(seconds=TIME_LIMIT_SECONDS) - elapsed

    if open_start is not None:
        print(f"Session ACTIVE (started {open_start.isoformat(timespec='seconds')}).")
    else:
        print("No active session.")
    print(f"Elapsed:   {format_duration_precise(elapsed)}")
    if remaining.total_seconds() >= 0:
        print(f"Remaining: {format_duration_precise(remaining)}")
    else:
        print(f"OVER LIMIT by {format_duration_precise(-remaining)}")


def cmd_total(args):
    elapsed, _ = compute_elapsed(read_rows(CSV_PATH))
    print(f"Total elapsed: {format_duration_precise(elapsed)}")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Simple git-backed work timesheet.")
    parser.add_argument(
        "command",
        nargs="?",
        default="status",
        choices=["start", "stop", "log", "status", "total"],
    )
    parser.add_argument("message", nargs="?", default=None)
    args = parser.parse_args()

    if not _GIT_AVAILABLE and args.command in ("start", "stop", "log"):
        print(
            "Note: GitPython is not installed, so timesheet edits will not be "
            "committed even if this is a git repository. "
            "Install with 'pip install GitPython' to enable that.",
            file=sys.stderr,
        )

    {
        "start": cmd_start,
        "stop": cmd_stop,
        "log": cmd_log,
        "status": cmd_status,
        "total": cmd_total,
    }[args.command](args)


if __name__ == "__main__":
    main()
