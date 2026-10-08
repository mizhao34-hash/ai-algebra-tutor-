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
- [ ] Week 3: problem templates + SymPy grader
- [ ] Week 4: backend API + model inference
- [ ] Week 5: frontend
- [ ] Week 6: LLM hints + verification loop
- [ ] Week 7: experiments + deployment
- [ ] Week 8: report + demo video
