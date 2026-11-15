"""Recommendation rule: the lowest-mastery skill whose prerequisites are all mastered.

With `within` (a course's skills), only prerequisites inside that course count
and only that course's skills are candidates. Otherwise a student who starts
Algebra 1 directly would find every skill locked behind Pre-Algebra skills.
"""

from .skills import MASTERY_THRESHOLD, SKILLS, topological_order


def is_unlocked(skill: str, mastery: dict[str, float], within: list[str] | None = None) -> bool:
    prereqs = [p for p in SKILLS[skill].prerequisites if within is None or p in within]
    return all(mastery[p] >= MASTERY_THRESHOLD for p in prereqs)


def recommend(mastery: dict[str, float], within: list[str] | None = None) -> str:
    # Candidates are listed in topological order, and min() returns the FIRST
    # of several equal values, so ties go to the more basic skill.
    candidates = [
        s for s in topological_order()
        if (within is None or s in within) and is_unlocked(s, mastery, within)
    ]
    return min(candidates, key=lambda s: mastery[s])
