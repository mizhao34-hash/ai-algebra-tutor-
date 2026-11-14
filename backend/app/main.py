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


def _mastery_out(app: FastAPI, user_id: str) -> dict:
    history = db.kt_history(app.state.db_path, user_id)
    mastery = app.state.mastery_model.mastery(history)
    attempts = Counter(skill for skill, _ in history)
    correct = Counter(skill for skill, ok in history if ok)
    return {
        "user_id": user_id,
        "threshold": MASTERY_THRESHOLD,
        "recommended": recommend(mastery),
        "skills": [
            {
                "id": sid,
                "name": SKILLS[sid].name,
                "prerequisites": list(SKILLS[sid].prerequisites),
                "mastery": round(mastery[sid], 4),
                "mastered": mastery[sid] >= MASTERY_THRESHOLD,
                "unlocked": is_unlocked(sid, mastery),
                "attempts": attempts[sid],
                "correct": correct[sid],
            }
            for sid in topological_order()
        ],
    }


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

    @app.get("/users/{user_id}/mastery")
    def get_mastery(request: Request, user_id: str = UserId):
        return _mastery_out(request.app, user_id)

    @app.get("/users/{user_id}/next")
    def next_problem(request: Request, user_id: str = UserId, skill: str | None = Query(None)):
        if skill is None:
            skill = _mastery_out(request.app, user_id)["recommended"]
        elif skill not in SKILLS:
            raise HTTPException(404, f"unknown skill: {skill}")
        # A fresh random seed per request; the seed is part of the problem id.
        return _problem_out(generate_problem(skill, random.randrange(10**9)))

    @app.post("/users/{user_id}/attempts")
    def submit(body: AttemptIn, request: Request, user_id: str = UserId):
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
            "mastery": _mastery_out(request.app, user_id),
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
