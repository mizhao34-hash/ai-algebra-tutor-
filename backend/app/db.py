"""SQLite storage for attempts (plain sqlite3, no ORM).

Every submission is stored. For knowledge tracing we use only the FIRST graded
(non-invalid) attempt per problem, matching ASSISTments, where "correct" means
correct on the first attempt. Retries after a wrong answer still get feedback
but don't change mastery.
"""

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
"""

# The first graded attempt of each problem, per user.
_FIRST_ATTEMPTS = """
SELECT skill, status FROM attempts
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
    return [(r["skill"], r["status"] == "correct") for r in rows]
