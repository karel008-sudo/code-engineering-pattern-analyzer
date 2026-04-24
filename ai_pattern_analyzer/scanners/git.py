"""
scanners/git.py — Raw git log extraction.

Runs git commands and returns structured commit data.
Returns empty results gracefully if git is unavailable or repo has no history.
"""
from __future__ import annotations
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CommitRecord:
    sha: str
    author_name: str
    author_email: str
    timestamp: int          # Unix epoch
    subject: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


def get_commits(repo_path: Path, max_commits: int = 500) -> List[CommitRecord]:
    """
    Return recent commits from a git repo.
    Returns [] if not a git repo or git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "log",
             f"--max-count={max_commits}",
             "--format=%H\x1f%an\x1f%ae\x1f%at\x1f%s",
             "--shortstat"],
            cwd=str(repo_path),
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    return _parse_log(result.stdout)


def _parse_log(raw: str) -> List[CommitRecord]:
    commits: List[CommitRecord] = []
    # Each commit block: header line + optional blank + optional shortstat line
    header_re = re.compile(
        r"^([0-9a-f]{40})\x1f(.*?)\x1f(.*?)\x1f(\d+)\x1f(.*)$"
    )
    stat_re = re.compile(
        r"(\d+)\s+files?\s+changed"
        r"(?:,\s*(\d+)\s+insertions?\(\+\))?"
        r"(?:,\s*(\d+)\s+deletions?\(-\))?",
    )

    current: Optional[CommitRecord] = None
    for line in raw.splitlines():
        m = header_re.match(line)
        if m:
            current = CommitRecord(
                sha=m.group(1), author_name=m.group(2),
                author_email=m.group(3), timestamp=int(m.group(4)),
                subject=m.group(5),
            )
            commits.append(current)
            continue
        if current:
            s = stat_re.search(line)
            if s:
                current.files_changed = int(s.group(1) or 0)
                current.insertions    = int(s.group(2) or 0)
                current.deletions     = int(s.group(3) or 0)

    return commits


def get_file_authors(repo_path: Path, rel_path: str) -> List[str]:
    """Return list of unique author emails for a specific file."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%ae", "--", rel_path],
            cwd=str(repo_path), capture_output=True, text=True, timeout=10,
        )
        return list(set(result.stdout.splitlines()))
    except Exception:
        return []
