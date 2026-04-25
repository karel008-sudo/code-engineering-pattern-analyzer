"""
analyzers/git_signals.py — Git metadata pattern analysis.

Analyzes commit history for patterns associated with AI-assisted development:
  - Burst commits (large LOC added in short time)
  - Low author diversity (single session)
  - Generic commit message style
  - Unusual time-of-day distribution

⚠ These are probabilistic signals, not proof of authorship.
"""
from __future__ import annotations
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..scanners.git import CommitRecord


# ── Burst detection ───────────────────────────────────────────────────────────

def git_burst_score(commits: List[CommitRecord]) -> float:
    """
    Detect large LOC additions in short time windows (AI generation bursts).
    Returns [0.0, 1.0] where 1.0 = strong burst pattern.

    v5.0: Improved to reduce false positives for:
    - Initial repository imports
    - CVS/SVN migrations
    - Large refactoring commits
    - Generated code updates
    - Vendor syncs
    If commit messages indicate these patterns, burst score is reduced.
    """
    if len(commits) < 3:
        return 0.30

    # v5.0: Detect import/migration/refactor commits and exclude them from burst analysis
    filtered_commits = []
    migration_detected = False
    for c in commits:
        if _IMPORT_MIGRATION_KEYWORDS.search(c.subject or ""):
            migration_detected = True
            continue  # skip non-AI burst commits
        filtered_commits.append(c)

    # If most commits are migration-like, return very low burst score
    if len(filtered_commits) < len(commits) * 0.5:
        return 0.15  # mostly migration/import commits — not AI burst

    # Use filtered commits for burst detection
    analysis_commits = filtered_commits if filtered_commits else commits

    # Group commits by day
    by_day: Dict[int, int] = defaultdict(int)
    for c in analysis_commits:
        day = c.timestamp // 86400
        by_day[day] += c.insertions

    daily_locs = list(by_day.values())
    if not daily_locs:
        return 0.30

    max_day_loc = max(daily_locs)
    mean_loc    = statistics.mean(daily_locs)

    # If any single day has 10× the average AND > 500 LOC → burst signal
    if mean_loc > 0 and max_day_loc > mean_loc * 8 and max_day_loc > 300:
        ratio = min(max_day_loc / max(mean_loc * 10, 300), 3.0)
        return round(min(0.40 + ratio * 0.15, 0.88), 4)

    # Check for consecutive high-activity days
    sorted_days = sorted(by_day.keys())
    consecutive_high = 0
    for i in range(1, len(sorted_days)):
        if (sorted_days[i] - sorted_days[i-1] == 1
                and by_day[sorted_days[i]] > mean_loc * 3):
            consecutive_high += 1
    if consecutive_high >= 2:
        return round(min(0.50 + consecutive_high * 0.08, 0.80), 4)

    return 0.28


# ── Author diversity ──────────────────────────────────────────────────────────

def git_author_diversity(commits: List[CommitRecord]) -> float:
    """
    AI signal: low author diversity (single author, single session).
    Human signal: multiple authors over time.
    Returns [0.0, 1.0] where 1.0 = AI-like (few authors).
    """
    if not commits:
        return 0.40

    emails = [c.author_email.lower() for c in commits]
    unique_authors = len(set(emails))
    total = len(emails)

    if unique_authors == 1:
        # Single author — could be normal. Check session concentration.
        return 0.55

    # Shannon entropy of author distribution
    freq = Counter(emails)
    entropy = -sum((c/total) * math.log2(c/total) for c in freq.values())
    max_entropy = math.log2(unique_authors)
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0

    # Low entropy (concentrated) = AI-like
    ai_signal = max(0.0, min(1.0, 1.0 - normalized))
    return round(ai_signal, 4)


# ── Commit message style ──────────────────────────────────────────────────────

# AI-generated commit messages tend to be formulaic
_AI_MSG_PATTERNS = re.compile(
    r"^(?:Add|Implement|Create|Update|Fix|Refactor|Remove|Delete|"
    r"Initial commit|Add implementation|Implement \w+|"
    r"Add \w+ service|Add \w+ handler|Add \w+ util|"
    r"Update \w+ to|Fix \w+ issue)\b",
    re.I,
)

# Human messages: more varied, include ticket refs, profanity, WIP markers
_HUMAN_MSG_PATTERNS = re.compile(
    r"(?:WIP|wip|todo|FIXME|fixme|hotfix|HOTFIX|oops|typo|"
    r"[A-Z]{2,}-\d+|#\d+|JIRA|ticket|revert|merge|Merge|bump)",
    re.I,
)

# v5.0: Non-AI burst keywords — large commits with these messages are NOT AI bursts
# They indicate: initial import, migration, refactoring, regeneration, etc.
_IMPORT_MIGRATION_KEYWORDS = re.compile(
    r"(?:initial\s+(?:import|commit|setup)|"
    r"cvs|svn|import\s+(?:source|from)|"
    r"(?:migrate|migration|move|rename|refactor|reformat|format)(?:d|ing)?\b|"
    r"cleanup|clean.?up|"
    r"regenerate|generated\s+(?:by|from)|"
    r"vendored?|vendor|third.?party|"
    r"sync(?:hronize)?|mirror|"
    r"cherry.pick|squash)",
    re.I,
)


def git_message_entropy(commits: List[CommitRecord]) -> float:
    """
    AI-generated commits have more formulaic, lower-entropy messages.
    Returns [0.0, 1.0] where 1.0 = AI-like (formulaic messages).
    """
    if len(commits) < 5:
        return 0.40

    subjects = [c.subject.strip() for c in commits if c.subject.strip()]
    if not subjects:
        return 0.40

    ai_matches  = sum(1 for s in subjects if _AI_MSG_PATTERNS.match(s))
    hum_matches = sum(1 for s in subjects if _HUMAN_MSG_PATTERNS.search(s))
    total = len(subjects)

    ai_ratio  = ai_matches  / total
    hum_ratio = hum_matches / total

    if hum_ratio > 0.3: return max(0.10, 0.35 - hum_ratio)
    if ai_ratio > 0.6:  return min(0.85, 0.50 + ai_ratio * 0.35)
    if ai_ratio > 0.4:  return 0.55

    # Message length entropy: AI tends toward medium-length consistent messages
    lengths = [len(s.split()) for s in subjects]
    if len(lengths) >= 3:
        try:
            cv = statistics.stdev(lengths) / max(statistics.mean(lengths), 1)
            if cv < 0.3: return 0.60  # very uniform = AI
        except statistics.StatisticsError:
            pass

    return 0.38


# ── Commit size distribution ──────────────────────────────────────────────────

def git_commit_size_score(commits: List[CommitRecord]) -> float:
    """
    AI sessions tend to produce large, uniform commits.
    Human commits have high variance in size.
    Returns [0.0, 1.0] where 1.0 = AI-like (large/uniform commits).
    """
    sizes = [c.insertions for c in commits if c.insertions > 0]
    if len(sizes) < 3:
        return 0.35

    avg_size = statistics.mean(sizes)
    try:
        cv = statistics.stdev(sizes) / max(avg_size, 1)
    except statistics.StatisticsError:
        cv = 1.0

    ai_signal = 0.0
    # Large average commit size
    if avg_size > 500: ai_signal += 0.30
    elif avg_size > 200: ai_signal += 0.15
    # Low coefficient of variation (uniform) — but don't penalize small commits
    if cv < 0.5 and avg_size > 100: ai_signal += 0.25
    elif cv < 1.0: ai_signal += 0.10

    return round(min(ai_signal, 0.80), 4)


# ── Main aggregator ───────────────────────────────────────────────────────────

def analyze_git(commits: List[CommitRecord]) -> Dict[str, float]:
    """
    Run all git signal analyzers and return a signal dict.
    All values in [0.0, 1.0]. Returns neutral values if no commits.
    """
    if not commits:
        return {
            "git_burst_score":       0.35,
            "git_author_diversity":  0.35,
            "git_message_entropy":   0.35,
            "git_commit_size_score": 0.35,
        }
    return {
        "git_burst_score":       git_burst_score(commits),
        "git_author_diversity":  git_author_diversity(commits),
        "git_message_entropy":   git_message_entropy(commits),
        "git_commit_size_score": git_commit_size_score(commits),
    }
