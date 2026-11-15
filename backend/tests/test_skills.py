import pytest

from app import skills
from app.skills import SKILLS, Skill, topological_order


def test_skill_count():
    assert len(SKILLS) == 12  # 9 linear (DKT) + 3 quadratic (BKT)


def test_prerequisites_come_first():
    order = topological_order()
    assert sorted(order) == sorted(SKILLS)
    pos = {s: i for i, s in enumerate(order)}
    for s in SKILLS.values():
        for pre in s.prerequisites:
            assert pos[pre] < pos[s.id]


def test_only_algebra_2_skills_lack_a_dkt_mapping():
    from app.courses import COURSES

    unmapped = {sid for sid, s in SKILLS.items() if not s.assistments_skill_ids}
    assert unmapped == set(COURSES["algebra_2"].skills)


def test_cycle_is_detected(monkeypatch):
    bad = dict(SKILLS)
    bad["integer_ops"] = Skill("integer_ops", "x", ("multi_step",), (277,))
    monkeypatch.setattr(skills, "SKILLS", bad)
    with pytest.raises(ValueError, match="cycle"):
        skills.topological_order()


MIN_TRAIN_ROWS = 1000


def test_mapped_assistments_skills_are_well_trained():
    """DKT is unreliable on skills it barely saw in training (see skills.py)."""
    import csv
    from collections import Counter

    from app.mastery import DEFAULT_SKILL_MAP

    train = DEFAULT_SKILL_MAP.parent / "train.csv"
    if not train.exists():
        pytest.skip("processed data not found")
    with open(DEFAULT_SKILL_MAP) as f:
        idx = {int(r["skill_id"]): r["skill_idx"] for r in csv.DictReader(f)}
    with open(train) as f:
        rows = Counter(r["skill_idx"] for r in csv.DictReader(f))
    for s in SKILLS.values():
        for a in s.assistments_skill_ids:
            assert rows[idx[a]] >= MIN_TRAIN_ROWS, (s.id, a, rows[idx[a]])
