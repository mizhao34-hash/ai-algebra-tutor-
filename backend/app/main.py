"""FastAPI app.

Run from the repo root:
    .venv/bin/uvicorn backend.app.main:app --reload
(or from backend/: ../.venv/bin/uvicorn app.main:app --reload, with the repo
root on PYTHONPATH so `ml` can be imported.)

Endpoints:
    GET  /health
    GET  /skills                        skill graph for the dashboard
    GET  /users/{user_id}/mastery       mastery per skill + recommended skill
    GET  /users/{user_id}/next          a new problem (recommended skill, or ?skill=)
    POST /users/{user_id}/attempts      grade an answer, return updated mastery
    POST /users/{user_id}/hints         one verified next-step hint (LLM + SymPy)
    GET  /courses                       course catalog
    GET  /courses/{course_id}           one course with its units and concept lessons
    POST /users/{user_id}/courses/{id}  join a course (idempotent)
    GET  /users/{user_id}/courses       joined courses with a mastery summary each
Mastery and next-problem take an optional ?course= to restrict to one course.

Problems sent to the client never include the answer; grading happens here by
regenerating the problem from its id.
"""

import os
import random
from pathlib import Path as FsPath
from collections import Counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from . import db
from .courses import CONCEPTS, COURSES
from .grader import InvalidInput, grade, normalize
from .hints import ClaudeHintLLM, HintConfigError, generate_hint, validate_current
from .mastery import DKTMastery
from .problems import generate_problem, problem_from_id
from .recommend import is_unlocked, recommend
from .skills import MASTERY_THRESHOLD, SKILLS, topological_order

# Secrets such as ANTHROPIC_API_KEY live in the repo-root .env (gitignored).
load_dotenv(FsPath(__file__).resolve().parents[2] / ".env")

# A simple user id is the only "auth" (see CLAUDE.md scope).
UserId = Path(pattern=r"^[A-Za-z0-9_-]{1,40}$")


class AttemptIn(BaseModel):
    problem_id: str = Field(max_length=80)
    answer: str = Field(max_length=200)


class HintIn(BaseModel):
    problem_id: str = Field(max_length=80)
    # The step the student is on; defaults to the problem itself. Must be valid
    # math equivalent to the problem, so no free text ever reaches the LLM.
    current: str | None = Field(None, max_length=80)


def _problem_out(problem) -> dict:
    # Deliberately leaves out problem.answer.
    return {
        "id": problem.id,
        "skill": problem.skill,
        "skill_name": SKILLS[problem.skill].name,
        "kind": problem.kind,
        "prompt": problem.prompt,
        "expression": problem.expression,
    }


def _course_skills(course_id: str | None) -> list[str] | None:
    if course_id is None:
        return None
    if course_id not in COURSES:
        raise HTTPException(404, f"unknown course: {course_id}")
    return COURSES[course_id].skills


def _mastery_out(app: FastAPI, user_id: str, course_id: str | None = None) -> dict:
    """Mastery for all skills, or only one course's skills (then prerequisites
    and unlocking only consider skills inside that course; see recommend.py)."""
    within = _course_skills(course_id)
    history = db.kt_history(app.state.db_path, user_id)
    mastery = app.state.mastery_model.mastery(history)
    attempts = Counter(skill for skill, _ in history)
    correct = Counter(skill for skill, ok in history if ok)
    return {
        "user_id": user_id,
        "course": course_id,
        "threshold": MASTERY_THRESHOLD,
        "recommended": recommend(mastery, within),
        "skills": [
            {
                "id": sid,
                "name": SKILLS[sid].name,
                "prerequisites": [p for p in SKILLS[sid].prerequisites if within is None or p in within],
                "mastery": round(mastery[sid], 4),
                "mastered": mastery[sid] >= MASTERY_THRESHOLD,
                "unlocked": is_unlocked(sid, mastery, within),
                "attempts": attempts[sid],
                "correct": correct[sid],
            }
            for sid in topological_order()
            if within is None or sid in within
        ],
    }


def _course_out(course, with_concepts: bool = False) -> dict:
    out = {
        "id": course.id,
        "name": course.name,
        "grades": course.grades,
        "description": course.description,
        "units": [
            {"id": u.id, "name": u.name, "skills": [{"id": s, "name": SKILLS[s].name} for s in u.skills]}
            for u in course.units
        ],
    }
    if with_concepts:
        for unit in out["units"]:
            for skill in unit["skills"]:
                c = CONCEPTS[skill["id"]]
                skill["concept"] = {
                    "summary": c.summary, "steps": list(c.steps), "example": list(c.example), "mistake": c.mistake,
                }
    return out


def create_app(db_path: str | None = None, mastery_model=None, hint_llm=None) -> FastAPI:
    """Tests pass a temporary db and fakes; production uses env vars."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_path = db_path or os.environ.get("TUTOR_DB", "tutor.db")
        db.init(app.state.db_path)
        app.state.mastery_model = mastery_model or DKTMastery()  # loads the checkpoint once
        app.state.hint_llm = hint_llm  # created on first hint request, so the app runs without an API key
        yield

    app = FastAPI(title="AI Algebra Tutor", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/skills")
    def skills():
        return [
            {"id": sid, "name": SKILLS[sid].name, "prerequisites": list(SKILLS[sid].prerequisites)}
            for sid in topological_order()
        ]

    @app.get("/courses")
    def courses():
        return [_course_out(c) for c in COURSES.values()]

    @app.get("/courses/{course_id}")
    def course(course_id: str):
        if course_id not in COURSES:
            raise HTTPException(404, f"unknown course: {course_id}")
        return _course_out(COURSES[course_id], with_concepts=True)

    @app.post("/users/{user_id}/courses/{course_id}")
    def join(request: Request, course_id: str, user_id: str = UserId):
        if course_id not in COURSES:
            raise HTTPException(404, f"unknown course: {course_id}")
        db.join_course(request.app.state.db_path, user_id, course_id)
        return {"joined": course_id}

    @app.get("/users/{user_id}/courses")
    def my_courses(request: Request, user_id: str = UserId):
        out = []
        for course_id, joined_at in db.joined_courses(request.app.state.db_path, user_id):
            m = _mastery_out(request.app, user_id, course_id)
            skills = m["skills"]
            out.append({
                **_course_out(COURSES[course_id]),
                "joined_at": joined_at,
                "summary": {
                    "skills": len(skills),
                    "mastered": sum(s["mastered"] for s in skills),
                    "average_mastery": round(sum(s["mastery"] for s in skills) / len(skills), 4),
                    "attempts": sum(s["attempts"] for s in skills),
                    "correct": sum(s["correct"] for s in skills),
                },
                "mastery": m,
            })
        return out

    @app.get("/users/{user_id}/mastery")
    def get_mastery(request: Request, user_id: str = UserId, course: str | None = Query(None)):
        return _mastery_out(request.app, user_id, course)

    @app.get("/users/{user_id}/next")
    def next_problem(
        request: Request, user_id: str = UserId, skill: str | None = Query(None), course: str | None = Query(None)
    ):
        within = _course_skills(course)
        if skill is None:
            skill = _mastery_out(request.app, user_id, course)["recommended"]
        elif skill not in SKILLS or (within is not None and skill not in within):
            raise HTTPException(404, f"unknown skill: {skill}")
        # A fresh random seed per request; the seed is part of the problem id.
        return _problem_out(generate_problem(skill, random.randrange(10**9)))

    @app.post("/users/{user_id}/attempts")
    def submit(body: AttemptIn, request: Request, user_id: str = UserId, course: str | None = Query(None)):
        try:
            problem = problem_from_id(body.problem_id)
        except ValueError:
            raise HTTPException(404, "unknown problem")
        result = grade(problem, body.answer)
        first = db.add_attempt(request.app.state.db_path, user_id, problem.id, problem.skill, body.answer, result.status)
        return {
            "status": result.status,
            "correct": result.correct,
            "message": result.message,
            "counts_for_mastery": first,
            "mastery": _mastery_out(request.app, user_id, course),
        }

    @app.post("/users/{user_id}/hints")
    def hint(body: HintIn, request: Request, user_id: str = UserId):
        try:
            problem = problem_from_id(body.problem_id)
        except ValueError:
            raise HTTPException(404, "unknown problem")
        current = normalize(body.current) if body.current else problem.expression
        try:
            validate_current(problem, current)
        except InvalidInput as e:
            raise HTTPException(400, f"invalid current step: {e}")
        try:
            if request.app.state.hint_llm is None:
                request.app.state.hint_llm = ClaudeHintLLM()
            result = generate_hint(problem, current, request.app.state.hint_llm)
        except HintConfigError as e:
            raise HTTPException(503, str(e))
        db.add_hint(request.app.state.db_path, user_id, problem.id, current, result)
        # Rejection reasons stay server-side: they can quote the answer.
        return {
            "hint": result.hint,
            "next_step": result.next_step,
            "verified": result.verified,
            "source": result.source,
        }

    return app


app = create_app()
