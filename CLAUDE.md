# AI Algebra Tutor — MSCS Capstone

## Project summary
An adaptive algebra tutor for linear equations. A deep knowledge tracing (DKT) model
predicts each student's mastery per skill, the system recommends the next problem,
and an LLM gives step hints that are verified with SymPy before being shown.
Final quarter: ~8 weeks. Keep scope small. Do not add features beyond this file.

## Scope (in)
- One unit: linear equations, ~8-10 skills with prerequisite relations
- Template-generated problems, auto-graded with SymPy
- Knowledge tracing: BKT baseline (pyBKT) vs DKT (LSTM, PyTorch); SAKT optional
- Recommendation rule: lowest-mastery skill whose prerequisites are mastered (>= 0.7)
- LLM hints: one step at a time, JSON output, SymPy check, retry up to 3, no answer leakage
- Mastery dashboard
- Experiments: (1) BKT vs DKT AUC, (2) hint error/leak rate with vs without SymPy check

## Scope change (2026-11-14, decided by me)
- Turn the tutor into a small algebra learning platform. Top tabs: Dashboard | Pre-Algebra | Algebra 1 | Algebra 2.
  Each course has a Lesson tab (lessons by unit/topic) and a Practice tab (practice/hints/mastery);
  Dashboard lists joined courses and their mastery.
- Algebra only. Pre-Algebra + Algebra 1 skills use DKT (>= 1000 ASSISTments rows each).
  Algebra 2 (quadratics unit) has no ASSISTments data, so its mastery uses BKT with hand-set
  parameters (backend/app/bkt.py) — a documented limitation.
- Units are dropdowns in the Lesson tab; each unit has its own practice (?unit=) and progress on the Dashboard.
- 18 skills in 8 units. DKT: integers, exponents/roots, expressions, linear equations (11 skills).
  BKT: inequalities, polynomials, quadratics (7 skills).
- AI tutor (backend/app/tutor.py, frontend/components/tutor/): chat that follows the student across pages;
  ask by typing, highlighting text, or "Explain this unit". Replies include an animated worked example whose
  every step is SymPy-verified; never gives the answer to the problem on screen (uses a similar problem).
  Rate-limited (30/user/hour, 300/hour total). Experiment 3 in results.md.

## Scope (out)
Teacher dashboard, adaptive diagnostic, misconception model, RL, user study, auth beyond a simple user id.

## Stack
- ml/: Python 3.11, pandas, PyTorch, pyBKT, scikit-learn
- backend/: FastAPI, SQLite (Postgres later if needed), SymPy, LLM API
- frontend/: Next.js + Tailwind
- Deploy: Vercel (frontend), Docker on Render (backend)

## Repo layout
- data/raw, data/processed (raw data is gitignored)
- ml/ — preprocessing, models, training, evaluation
- backend/ — API, problem generator, grader, hint service
- frontend/
- experiments/ — scripts and results for the report
- report/

## Conventions
- Split data BY STUDENT (70/15/15), never by row
- Fixed random seeds; log every experiment result to experiments/results.md
- Write pytest tests for the grader and problem generator
- Explain non-obvious code with short comments; I must understand every part for my defense
- Secrets in .env (never commit)

## Progress log
- [x] Week 1: data preprocessing (ml/preprocess.py → data/processed/)
- [x] Week 2: BKT + DKT training and comparison (test AUC: BKT 0.708, DKT 0.751)
- [x] Week 3: problem templates + SymPy grader (backend/app: skills.py, problems.py, grader.py; 106 tests)
- [x] Week 4: backend API + model inference (FastAPI + SQLite, DKT mastery, recommendation rule; run: .venv/bin/uvicorn backend.app.main:app)
- [x] Week 5: frontend (Next.js 14 + Tailwind: /practice, /dashboard; run: cd frontend && npm run dev, with the backend on :8000)
- [x] Week 6: LLM hints + verification loop (backend/app/hints.py: Claude structured output, SymPy check, 3 retries, fallback; needs ANTHROPIC_API_KEY in .env)
- [x] Week 7: experiments + deployment (exp 2 in results.md + experiments/hint_audit.md; live: https://ai-algebra-tutor-pi.vercel.app, API https://algebra-tutor-api.onrender.com; see DEPLOY.md)
- [ ] Week 8: report + demo video — report draft in report/report.md (TODOs: name, citations check, screenshots, conclusion, reflection); demo notes on Desktop
