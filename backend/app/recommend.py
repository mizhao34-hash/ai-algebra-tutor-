"""Recommendation rule: the lowest-mastery skill whose prerequisites are all mastered."""

from .skills import MASTERY_THRESHOLD, SKILLS, topological_order


def is_unlocked(skill: str, mastery: dict[str, float]) -> bool:
    return all(mastery[p] >= MASTERY_THRESHOLD for p in SKILLS[skill].prerequisites)


def recommend(mastery: dict[str, float]) -> str:
    # Candidates are listed in topological order, and min() returns the FIRST
    # of several equal values, so ties go to the more basic skill.
    candidates = [s for s in topological_order() if is_unlocked(s, mastery)]
    return min(candidates, key=lambda s: mastery[s])
