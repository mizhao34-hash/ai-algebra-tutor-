"""SQLite storage for attempts (plain sqlite3, no ORM).

Every submission is stored. For knowledge tracing we use only the FIRST graded
(non-invalid) attempt per problem, matching ASSISTments, where "correct" means
correct on the first attempt. Retries after a wrong answer still get feedback
but don't change mastery.
"""

import json
import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- increasing id = time order
    user_id    TEXT NOT NULL,
    problem_id TEXT NOT NULL,
    skill      TEXT NOT NULL,
    answer     TEXT NOT NULL,
    status     TEXT NOT NULL,  -- correct | not_simplified | incorrect | invalid
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts (user_id, id);

CREATE TABLE IF NOT EXISTS hints (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       TEXT NOT NULL,
    problem_id    TEXT NOT NULL,
    current       TEXT NOT NULL,
    hint          TEXT NOT NULL,
    next_step     TEXT NOT NULL,
    verified      INTEGER NOT NULL,
    source        TEXT NOT NULL,     -- llm | fallback
    attempts      INTEGER NOT NULL,  -- LLM calls used
    rejections    TEXT NOT NULL,     -- JSON list; server-side only (may quote the answer)
    before_answer INTEGER NOT NULL,  -- 1 if requested before the first graded attempt
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_hints_user ON hints (user_id, problem_id);
"""

# The first graded attempt of each problem, per user. As in ASSISTments, asking
# for a hint before answering means the problem counts as not solved
# independently, so `helped` turns a correct first attempt into incorrect.
_FIRST_ATTEMPTS = """
SELECT skill, status,
       EXISTS (SELECT 1 FROM hints h
               WHERE h.user_id = a.user_id AND h.problem_id = a.problem_id AND h.before_answer = 1) AS helped
FROM attempts a
WHERE id IN (
    SELECT MIN(id) FROM attempts
    WHERE user_id = ? AND status != 'invalid'
    GROUP BY problem_id
)
ORDER BY id
"""


@contextmanager
def connect(path: str):
    """Open a connection, commit on success (rollback on error), always close.
    (sqlite3's own `with conn:` commits but does NOT close.)"""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init(path: str) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def add_attempt(path: str, user_id: str, problem_id: str, skill: str, answer: str, status: str) -> bool:
    """Store an attempt. Returns True if it is the first graded attempt on this problem."""
    with connect(path) as conn:
        earlier = conn.execute(
            "SELECT 1 FROM attempts WHERE user_id = ? AND problem_id = ? AND status != 'invalid' LIMIT 1",
            (user_id, problem_id),
        ).fetchone()
        conn.execute(
            "INSERT INTO attempts (user_id, problem_id, skill, answer, status) VALUES (?, ?, ?, ?, ?)",
            (user_id, problem_id, skill, answer, status),
        )
    return status != "invalid" and earlier is None


def kt_history(path: str, user_id: str) -> list[tuple[str, bool]]:
    """(skill, correct) for each problem's first graded attempt, in time order."""
    with connect(path) as conn:
        rows = conn.execute(_FIRST_ATTEMPTS, (user_id,)).fetchall()
    return [(r["skill"], r["status"] == "correct" and not r["helped"]) for r in rows]


def add_hint(path: str, user_id: str, problem_id: str, current: str, result) -> None:
    """Store a HintResult (see hints.py)."""
    with connect(path) as conn:
        answered = conn.execute(
            "SELECT 1 FROM attempts WHERE user_id = ? AND problem_id = ? AND status != 'invalid' LIMIT 1",
            (user_id, problem_id),
        ).fetchone()
        conn.execute(
            "INSERT INTO hints (user_id, problem_id, current, hint, next_step, verified, source, attempts,"
            " rejections, before_answer) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, problem_id, current, result.hint, result.next_step, int(result.verified), result.source,
             result.attempts, json.dumps(result.rejections), int(answered is None)),
        )
