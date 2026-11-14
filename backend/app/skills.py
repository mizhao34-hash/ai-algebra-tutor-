"""Skill graph for the linear-equations unit.

Each skill has:
  - prerequisites: skills that must be mastered (>= MASTERY_THRESHOLD) before
    this skill is recommended (used by the recommendation rule in Week 4).
  - assistments_skill_ids: ASSISTments 2009 skill ids that best match this
    skill. DKT/BKT were trained on ASSISTments skills, so at inference time we
    read mastery for a tutor skill from these ids (averaged if several).
    The mapping is a hand-made approximation; see the report's limitations.
"""

from dataclasses import dataclass

MASTERY_THRESHOLD = 0.7


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    prerequisites: tuple[str, ...]
    assistments_skill_ids: tuple[int, ...]


# Order matters only for display; the graph is defined by `prerequisites`.
#
#   integer_ops ─┬─> combine_like_terms ──────────────┐
#                ├─> distributive ─────────────────┐  │
#                ├─> one_step_add ─┐               │  │
#                └─> one_step_mul ─┴─> two_step ─┬─┼──┴─> vars_both_sides ─┐
#                                                └─┴────> parentheses ─────┴─> multi_step
SKILLS: dict[str, Skill] = {
    s.id: s
    for s in [
        Skill("integer_ops", "Integer operations", (), (277, 279, 310)),
        Skill("combine_like_terms", "Combining like terms", ("integer_ops",), (165,)),
        Skill("distributive", "Distributive property", ("integer_ops",), (340,)),
        Skill("one_step_add", "One-step equations (add/subtract)", ("integer_ops",), (311,)),
        Skill("one_step_mul", "One-step equations (multiply/divide)", ("integer_ops",), (311,)),
        Skill("two_step", "Two-step equations", ("one_step_add", "one_step_mul"), (311,)),
        Skill("vars_both_sides", "Variables on both sides", ("two_step", "combine_like_terms"), (312,)),
        Skill("parentheses", "Equations with parentheses", ("two_step", "distributive"), (312, 340)),
        Skill("multi_step", "Multi-step equations", ("vars_both_sides", "parentheses"), (312, 166)),
    ]
}


def topological_order() -> list[str]:
    """Return skill ids so every skill comes after its prerequisites.

    Raises ValueError if the graph has a cycle or an unknown prerequisite,
    so a bad edit to SKILLS fails loudly (tested in tests/test_skills.py).
    """
    order: list[str] = []
    state: dict[str, str] = {}  # "visiting" while on the DFS stack, "done" after

    def visit(sid: str) -> None:
        if sid not in SKILLS:
            raise ValueError(f"unknown skill: {sid}")
        if state.get(sid) == "done":
            return
        if state.get(sid) == "visiting":
            raise ValueError(f"cycle in skill graph at: {sid}")
        state[sid] = "visiting"
        for pre in SKILLS[sid].prerequisites:
            visit(pre)
        state[sid] = "done"
        order.append(sid)

    for sid in SKILLS:
        visit(sid)
    return order
