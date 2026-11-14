"""API tests with a temporary database and a fake mastery model, so they test
the API logic without depending on what DKT happens to predict."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.problems import problem_from_id
from app.skills import SKILLS


class FakeMastery:
    """Mastery = fraction of first attempts correct on that skill."""

    def __init__(self):
        self.calls = []

    def mastery(self, history):
        self.calls.append(list(history))
        out = {}
        for s in SKILLS:
            results = [ok for skill, ok in history if skill == s]
            out[s] = sum(results) / len(results) if results else 0.0
        return out


@pytest.fixture
def fake():
    return FakeMastery()


@pytest.fixture
def client(tmp_path, fake):
    app = create_app(db_path=str(tmp_path / "test.db"), mastery_model=fake)
    with TestClient(app) as c:  # `with` runs the startup (lifespan) code
        yield c


def answer_of(problem_id):
    return problem_from_id(problem_id).answer


def test_health_and_skills(client):
    assert client.get("/health").json() == {"ok": True}
    skills = client.get("/skills").json()
    assert [s["id"] for s in skills][0] == "integer_ops"
    assert len(skills) == len(SKILLS)


def test_new_user_gets_root_skill_and_no_answer(client):
    p = client.get("/users/alice/next").json()
    assert p["skill"] == "integer_ops"
    assert "answer" not in p  # never leak the answer to the browser
    assert set(p) == {"id", "skill", "skill_name", "kind", "prompt", "expression"}


def test_skill_override_and_unknown_skill(client):
    assert client.get("/users/alice/next", params={"skill": "multi_step"}).json()["skill"] == "multi_step"
    assert client.get("/users/alice/next", params={"skill": "calculus"}).status_code == 404


def test_correct_answer_updates_mastery(client):
    p = client.get("/users/bob/next").json()
    r = client.post("/users/bob/attempts", json={"problem_id": p["id"], "answer": answer_of(p["id"])}).json()
    assert r["status"] == "correct" and r["correct"] and r["counts_for_mastery"]
    row = next(s for s in r["mastery"]["skills"] if s["id"] == "integer_ops")
    assert row["mastery"] == 1.0 and row["mastered"] and row["attempts"] == 1


def test_only_first_graded_attempt_counts(client, fake):
    p = client.get("/users/carol/next", params={"skill": "two_step"}).json()
    post = lambda a: client.post("/users/carol/attempts", json={"problem_id": p["id"], "answer": a}).json()

    assert post("abc")["counts_for_mastery"] is False      # invalid: ignored
    assert post("999")["counts_for_mastery"] is True       # first real attempt: wrong
    r = post(answer_of(p["id"]))                            # retry: right, but doesn't count
    assert r["correct"] and r["counts_for_mastery"] is False
    assert fake.calls[-1] == [("two_step", False)]


def test_users_are_separate(client, fake):
    p = client.get("/users/dave/next").json()
    client.post("/users/dave/attempts", json={"problem_id": p["id"], "answer": answer_of(p["id"])})
    m = client.get("/users/erin/mastery").json()
    assert all(s["attempts"] == 0 for s in m["skills"])
    assert m["recommended"] == "integer_ops"


def test_bad_input(client):
    assert client.get("/users/bad id!/mastery").status_code == 422
    assert client.post("/users/x/attempts", json={"problem_id": "nope", "answer": "1"}).status_code == 404
    assert client.post("/users/x/attempts", json={"problem_id": "two_step:1", "answer": "1" * 500}).status_code == 422
