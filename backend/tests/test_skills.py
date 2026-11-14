import pytest

from app import skills
from app.skills import SKILLS, Skill, topological_order


def test_nine_skills_in_scope():
    assert 8 <= len(SKILLS) <= 10


def test_prerequisites_come_first():
    order = topological_order()
    assert sorted(order) == sorted(SKILLS)
    pos = {s: i for i, s in enumerate(order)}
    for s in SKILLS.values():
        for pre in s.prerequisites:
            assert pos[pre] < pos[s.id]


def test_every_skill_maps_to_assistments():
    for s in SKILLS.values():
        assert s.assistments_skill_ids


def test_cycle_is_detected(monkeypatch):
    bad = dict(SKILLS)
    bad["integer_ops"] = Skill("integer_ops", "x", ("multi_step",), (277,))
    monkeypatch.setattr(skills, "SKILLS", bad)
    with pytest.raises(ValueError, match="cycle"):
        skills.topological_order()
