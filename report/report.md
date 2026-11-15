# AI Algebra Tutor: Adaptive Practice with Deep Knowledge Tracing and Verified LLM Feedback

**MSCS Capstone Report** · Mingqi Zhao · Advisor: Bolei Zhou · November 14, 2026

> Draft written from the repository on 2026-11-14. Every number below comes from
> `experiments/results.md` or `data/processed/stats.json`. Sections marked **TODO**
> need your input. Rewrite the text in your own words before submitting.

---

## Abstract

Students learning algebra benefit from practice that adapts to what they already know
and from help at the exact step where they are stuck. Large language models (LLMs) can
explain mathematics fluently, but they also make errors and readily reveal answers, two
failure modes that are particularly harmful in a tutoring setting. This project builds an
adaptive algebra tutor that combines (1) a Deep Knowledge Tracing (DKT) model that
estimates each student's mastery of each skill, (2) a prerequisite-aware recommendation
rule that selects the next problem, and (3) LLM-generated hints and tutor explanations
whose every mathematical step is verified with a computer algebra system (SymPy) before
it is shown. On the ASSISTments 2009 dataset, split by student, DKT reaches a test AUC of
0.751 versus 0.708 for a Bayesian Knowledge Tracing (BKT) baseline. In a paired experiment
on 127 hint requests, verification reduced the answer-leak rate of a smaller LLM from
7.9% to 0% at a cost of 1.11 model calls per hint; a stronger LLM rarely needed
correction. In 40 tutor requests across eight units, every animated worked example shown
to students was fully verified and none revealed the answer to the student's current
problem. The system is deployed as a web platform with three courses (Pre-Algebra,
Algebra 1, Algebra 2), 8 units and 18 topics.

---

## 1. Introduction

### 1.1 Motivation
This project started from my experience as a K-12 tutor. Many of the students I worked with who
struggled most with algebra came from underrepresented minority groups, and they often had little
access to one-on-one help outside class: when they got stuck at home, there was no one to show them
the next step. I wanted to build a tool that lets these students learn algebra on their own, at
their own pace, with help available whenever they need it.

Practice is most useful when it targets what a student has not yet mastered, and help is
most useful when it addresses the step a student is stuck on. Classroom teachers cannot
provide either for every student at once. Intelligent tutoring systems have long tried to
fill this gap with knowledge tracing (estimating mastery from answer histories) and with
step-level feedback.

LLMs make natural-language explanations cheap, but they introduce two risks for tutoring:
- **Incorrect mathematics.** A fluent but wrong step can teach a misconception. ChatGPT-generated
  help failed quality checks on 32% of problems in one study of algebra and statistics hints
  (Pardos & Bhandari, 2024), and LLMs prompted as tutors often give factually incorrect feedback
  (Macina et al., 2023).
- **Answer leakage.** A tutor that simply gives the answer removes the learning opportunity.
  LLM tutors tend to reveal solutions too early (Macina et al., 2023), and in a field experiment
  with high school math students, unrestricted GPT-4 access improved practice performance but
  hurt later exam performance, an effect largely mitigated by a tutor designed not to give answers
  away (Bastani et al., 2025).

### 1.2 Research questions
- **RQ1.** Does a deep knowledge tracing model predict student performance better than the
  classic BKT baseline on held-out students?
- **RQ2.** How often do LLM-generated step hints contain mathematical errors or reveal the
  answer, and how much does verification with a computer algebra system reduce this, at
  what cost?
- **RQ3.** Can multi-step, animated LLM explanations be verified in the same way, and how
  often do they pass?

### 1.3 Contributions
1. A complete, deployed adaptive tutor for introductory algebra: template-generated
   problems, SymPy grading, DKT-based mastery, prerequisite-aware recommendation, lessons,
   and a dashboard.
2. A verification layer for LLM output in tutoring. Each proposed step is checked for
   mathematical equivalence, progress, and answer leakage, with feedback-driven retries and
   safe fallbacks. It is applied both to one-step hints and to multi-step tutor walkthroughs.
3. Three experiments: DKT vs BKT (RQ1), hint verification with two LLMs including a manual
   audit (RQ2), and tutor walkthrough verification (RQ3).

---

## 2. Background and related work

> All references were checked online on 2026-11-14 (DBLP, publisher and proceedings pages)
> and read by the author.

- **Bayesian Knowledge Tracing (BKT)** models each skill as a hidden binary state
  (learned / not learned) with four parameters: prior, learn, guess, slip (Corbett &
  Anderson, 1995). We use the pyBKT library (Badrinath, Wang & Pardos, 2021).
- **Deep Knowledge Tracing (DKT)** replaces the per-skill HMM with a recurrent network over
  the whole interaction sequence, which lets it learn relationships between skills
  (Piech et al., 2015). Attention-based variants such as SAKT (Pandey & Karypis, 2019)
  were listed as optional in this project and were not implemented.
- **ASSISTments** is an online math-practice platform whose 2009–2010 skill-builder data
  is a standard knowledge tracing benchmark (Feng, Heffernan & Koedinger, 2009).
- **SymPy** is an open-source computer algebra system in Python (Meurer et al., 2017),
  used here for grading and verification.
- **LLMs as tutors.** Pardos & Bhandari (2024) found that ChatGPT-generated help on algebra and
  statistics produced learning gains comparable to human-authored help, but 32% of generated help
  failed quality checks; self-consistency (sampling several answers and keeping the majority)
  reduced errors to nearly 0% for algebra. Macina et al. (2023) released MathDial, a tutoring
  dialogue dataset, motivated by LLMs that solve problems well but tutor poorly, giving incorrect
  feedback or revealing solutions. Bastani et al. (2025) showed in a field experiment that
  answer-giving AI can harm learning, while a tutor with guardrails largely avoids this.
  Wang et al. (2024) improve LLM responses to student math mistakes by modelling expert
  remediation decisions.
- **Tools for LLM math.** Program-aided language models (PAL; Gao et al., 2023) have the LLM
  write a program and let an interpreter compute the result, improving math accuracy.
- **How this project differs.** These approaches improve the *likelihood* that an LLM is correct
  (self-consistency, program execution, better prompts or data). This project instead treats
  every student-facing math step as a claim to *check*: each hint step and each line of a tutor
  walkthrough is verified with SymPy for equivalence, progress, and answer leakage before display,
  with retries and safe fallbacks. The experiments measure what the check catches, and its cost.

---

## 3. System design

### 3.1 Overview

```mermaid
flowchart LR
  subgraph Browser["Frontend (Next.js on Vercel)"]
    L[Lessons] --- P[Practice] --- D[Dashboard] --- T[AI tutor panel]
  end
  subgraph API["Backend (FastAPI in Docker on Render)"]
    G[Problem generator] --> GR[SymPy grader]
    KT[Mastery: DKT + BKT] --> R[Recommendation rule]
    H[Hint + tutor service] --> V[SymPy verifier]
    DB[(SQLite)]
  end
  Browser <-->|JSON over HTTPS| API
  H <-->|structured output| C[Claude API]
  KT -.->|trained offline| M[DKT LSTM, PyTorch]
```

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | Next.js 14, Tailwind | Courses, lessons, practice, dashboard, tutor chat |
| Backend | FastAPI, SQLite | Problems, grading, mastery, recommendation, hints, tutor |
| ML | PyTorch (DKT), pyBKT (baseline) | Knowledge tracing |
| Math | SymPy | Grading and verification of every LLM step |
| LLM | Claude (Opus 5.5 by default) | Hints and tutor explanations, as structured JSON |
| Deployment | Vercel, Docker on Render | Public web app |

TODO: add 3–4 screenshots (lesson page, practice page with hint, tutor walkthrough, dashboard).

### 3.2 Curriculum and skill graph
The platform has three courses, 8 units and 18 topics (skills), each with prerequisites:

| Course | Units (topics) |
|---|---|
| Pre-Algebra | Integers (1) · Exponents and square roots (2) · Algebraic expressions (2) |
| Algebra 1 | One-step equations (2) · Multi-step equations (4) · Linear inequalities (2) |
| Algebra 2 | Polynomials (2) · Quadratic equations (3) |

Prerequisites form a directed acyclic graph (checked by a test). Every topic has a lesson
with an idea, steps, a worked example and a common mistake. **Every line of every worked
example is verified with SymPy in the test suite**, so a lesson cannot silently teach an
incorrect step.

### 3.3 Problem generation and grading
Each topic has a template generator. Problems are generated "answer first" (for example,
pick the solution x, then build the equation around it), so answers are always integers,
and a problem is fully determined by `skill:seed`. The server therefore regenerates a
problem from its id to grade it and never sends the answer to the browser.

The grader parses answers with SymPy and checks:
1. **Equivalence:** the same value, or the same solution set (any order) for quadratics
   and inequalities.
2. **Simplest form:** judged on the *unevaluated* parse, so `x = 8/2` is marked "right
   value, not simplified".
3. **Targeted feedback,** for example "that's one solution, but there's another one", or
   "right boundary, check the direction of the inequality sign".

**Security.** SymPy's parser uses `eval`, so student text is restricted to a character
whitelist, a length cap, `sqrt(` as the only word, and exponents of at most 4 that cannot be
chained (which blocks inputs like `9^9^9`).

### 3.4 Knowledge tracing in the live system
DKT was trained on ASSISTments skills, not on our topics, so each topic is mapped to one
or more ASSISTments skills. A topic's answers are fed to the LSTM as its first mapped
skill, and its mastery is the mean predicted P(correct) over its mapped skills. We only
map to ASSISTments skills with at least 1,000 training rows (enforced by a test); the
closest-named skills for "Algebraic Simplification" (84 rows) and "Distributive Property"
(10 rows) failed this rule and were replaced by related, well-trained skills.

Inequalities, polynomials and quadratics have essentially no ASSISTments data (for
example, 26 rows for the quadratic formula). For these 7 topics the system uses **BKT with
hand-set parameters** (prior 0.1, learn 0.1, guess 0.25, slip 0.1), reporting P(correct on
the next attempt) so that the 0.7 mastery threshold means the same thing for both models.
With these settings, two correct first attempts in a row reach mastery.

Only each problem's **first graded attempt** updates mastery, matching how ASSISTments
defines correctness; requesting a hint before answering makes the attempt count as
incorrect.

### 3.5 Recommendation rule
Recommend the lowest-mastery topic whose prerequisites are all mastered (≥ 0.7). Ties go
to the more basic topic (topological order). Within a course or unit, only prerequisites
inside that course or unit gate a topic, so a student can start Algebra 1 directly.

### 3.6 Verified LLM hints
A hint is a JSON object `{hint, next_step}` produced with Claude's structured output.
Before a student sees it, `next_step` must:
1. parse safely;
2. be equivalent to the student's current step (same solution set);
3. make progress, judged on the written form, because distributing changes the form but
   not the value;
4. not be the final answer.

The hint text is also scanned for the answer. Rejected hints are retried with the reasons
(at most 3 attempts), then replaced by a fixed, safe hint for the skill.

### 3.7 The AI tutor
A chat panel follows the student across the site. Students can type a question, highlight
text on the page, or ask for a whole unit to be explained. A reply has a short message and
an optional **walkthrough** (a starting expression and a list of `{operation, result}`
steps), which the frontend animates line by line, highlighting what was added or removed
and flagging inequality sign flips.

Each step must be equivalent to the starting line. Substitute-back "check" steps with no
x, such as `-7(8) + 4 = -52`, are allowed if they are true. When a practice problem is on
screen, the tutor is given a similar problem with different numbers to use instead, and
any reply whose message states the answer, or whose example has the same solution set,
is rejected. Unverifiable walkthroughs are dropped (text only), and the tutor is
rate-limited (30 messages per user per hour, 300 in total) because every message costs
API credit.

---

## 4. Data

ASSISTments 2009–2010 skill-builder data (`data/processed/stats.json`):

| Step | Rows | Students |
|---|---|---|
| Raw file | 525,534 | 4,217 |
| Drop rows without a skill | 459,208 | |
| One row per answer (deduplicate `order_id`) | 283,105 | |
| Students with ≥ 2 answers | 282,969 | 4,027 |

The deduplication step matters. The raw file repeats an answer once per tagged skill, and
keeping those copies would let a sequence model see the answer it is about to predict,
inflating AUC. After cleaning there are 112 skills. Students (not rows) are split
70/15/15 into train (2,818 students, 201,797 rows), validation (604, 44,778) and test
(605, 36,394), so no student appears in more than one split. All seeds are fixed at 42.

---

## 5. Experiments and results

### 5.1 Experiment 1: DKT vs BKT (RQ1)
**Setup.** DKT: an embedding of (skill, correct) tokens (size 100), an LSTM (hidden size
100), dropout 0.2, Adam (lr 1e-3), batch size 64, training windows of 200 answers, gradient
clipping at 1.0, and early stopping on validation AUC (patience 3, at most 30 epochs).
Evaluation runs on full sequences. BKT: pyBKT 1.4.3, one model per skill, 5 random restarts.
Both models predict every answer except each student's first, and are scored identically
(`ml/evaluation.py`).

| Model | Val AUC | Val ACC | Test AUC | Test ACC |
|---|---|---|---|---|
| BKT (pyBKT) | 0.716 | 0.721 | 0.708 | 0.708 |
| **DKT (LSTM)** | **0.755** | **0.739** | **0.751** | **0.731** |

Test predictions: n = 35,789. **DKT improves test AUC by 0.043 over BKT**, consistent with
DKT's ability to share information across skills.

### 5.2 Experiment 2: Verified hints (RQ2)
**Setup.** 127 hint requests: 10 problems per skill for the 9 linear-equation skills, plus
the real "last step" (cx = d) for equation problems, where leaking is most tempting. The
design is **paired**: the LLM's first proposal is exactly what an unverified system would
show, and the verified system's final output is what students see. Both are scored on the
same outputs. Leaks are measured by the checker and by a broad "answer value appears
anywhere" measure, which was then **manually audited** (`experiments/hint_audit.md`).

| Model | Condition | Math errors | Leaks (audited) | Wrong prose found* | LLM calls / hint |
|---|---|---|---|---|---|
| Claude Opus 5.5 | without check | 0% | 0.8% (1) | 0 | 1 |
| Claude Opus 5.5 | with check | 0% | 0.8% (1) | 0 | 1.0 |
| Claude Haiku 5.5 | without check | 0% | 7.9% (10) + 1 borderline | 2 | 1 |
| Claude Haiku 5.5 | with check | 0% | **0%** + 1 borderline | 2 | 1.11 |

\*Only broad-flagged hints were audited for wrong prose, so this is a lower bound.

**Findings.**
- Verification removed every detectable leak from the weaker model for 11% extra calls.
- The stronger model rarely needed it.
- SymPy cannot check wording. The one Opus leak was in prose ("0 divided by any nonzero
  number is 0" when x = 0), and Haiku twice called a correct student step wrong.
- The experiment also surfaced three bugs in our own pipeline: a progress check that
  rejected correct distribution steps, a leak check that read `8x = 0` as `x = 0`, and an
  initial design whose "last step" states were unreachable from the problem. The first run
  is kept in the log, marked invalid.

### 5.3 Experiment 3: Verified tutor walkthroughs (RQ3)
**Setup.** 40 tutor requests: for each of the 8 units, three "explain this unit" requests
and two "just tell me the answer" requests made while a practice problem was on screen.
The design is paired as in Experiment 2.

| Measure | Result |
|---|---|
| First replies with a walkthrough | 100% |
| First-reply math errors (after the checker fix) | 0% |
| First-reply answer leaks | 0% |
| Shown with a fully verified walkthrough | 100% |
| LLM calls per request / latency | 1.05 / 3.4 s |
| Cost (40 requests, Opus 5.5) | $0.45 |

**Finding.** The initial run reported 5% "math errors". Inspection showed both cases were
correct substitute-back checks that the verifier wrongly rejected. After the verifier was
fixed, both runs are reported. This illustrates a general point: a verifier is a model of
validity, and its false positives cost pedagogical quality, here a useful "check your
answer" step.

---

## 6. Engineering and testing

- **Tests:** 291 automated backend tests (pytest) cover the grader (including security
  inputs), generators (300 seeds per skill, each verified by SymPy), lessons (every worked
  example line), recommendation, BKT, mastery routing, hints, the tutor and the API.
- **Reproducibility:** fixed seeds, by-student splits, every experiment logged in
  `experiments/results.md` together with its raw outputs.
- **Deployment:** Docker image with CPU-only PyTorch on Render, Next.js on Vercel, CORS
  restricted to the site, and the API key held only in server environment variables.
- **End-to-end checks:** an automated headless-browser walkthrough of the live site
  (sign-in, lessons, practice, hints, tutor, dashboard, phone width).

---

## 7. Limitations

1. **Approximate skill mapping.** Tutor topics are mapped onto ASSISTments skills by hand.
   Several topics share one ASSISTments skill, so their mastery estimates move together.
2. **Hand-set BKT parameters** for 7 topics with no training data.
3. **Verification covers math, not language.** Misleading wording can pass.
4. **No learning-outcome evaluation.** Experiments measure prediction accuracy and output
   safety, not whether students learn more; a user study was out of scope.
5. **Small LLM experiments** (127 hints and 40 tutor requests) and a single-annotator
   manual audit.
6. **Infrastructure.** The free hosting tier sleeps when idle and resets the SQLite
   database on restart.

## 8. Future work
- A study with the students who motivated this project, measuring learning gains and how they use the lessons and the tutor.
- Training knowledge tracing on data that covers Algebra 2 topics, or fitting BKT
  parameters from the platform's own logs.
- Checking the explanation text, for example by extracting and verifying every equation
  in the prose.
- Attention-based knowledge tracing (SAKT), which was optional in the original plan.
- Persistent storage (Postgres) for real deployments.

## 9. Conclusion
This project built and deployed an adaptive algebra tutor whose LLM features are constrained by a computer algebra system. On held-out ASSISTments students, DKT predicted performance better than BKT (test AUC 0.751 vs. 0.708), answering RQ1. For RQ2, verifying each hint step with SymPy removed every detectable answer leak from a weaker LLM (7.9% to 0%) at about 11% more model calls, while a stronger LLM rarely needed correction. For RQ3, multi-step tutor walkthroughs could be verified in the same way: all 40 shown walkthroughs passed every check. The main lesson is that LLMs become usable as math tutors when their mathematical claims are treated as claims to verify rather than as trusted output, but the verifier is itself a model that must be tested: in both LLM experiments, our own checker produced errors that only careful inspection of its outputs revealed.

## 10. Reflection
The hardest part was not any single model but the joints between components. DKT was trained on ASSISTments skills, so connecting it to my own curriculum required a skill mapping, and some of the closest-named skills had almost no training data; I had to set a minimum-data rule and fall back to BKT where data did not exist. The experiments were also humbling: three bugs in my own verification pipeline, and a false alarm that made the tutor look worse than it was, only surfaced because I inspected individual outputs instead of trusting summary numbers. The scope also grew during the project, from one unit of linear equations to a three-course platform with lessons and an AI tutor. This came from my original motivation: the students I tutored needed to be able to learn on their own, and practice problems alone are not enough for that. A student working alone also needs a place to learn the concepts and someone to ask when they are stuck. If I started again, I would plan an evaluation with the students who motivated this project from the beginning, since whether they actually learn more is the question this project cannot yet answer, and I would write tests for the verifier before running experiments with it.

---

## References

> Checked online on 2026-11-14. TODO: format in your program's required citation style.

- Bastani, H., Bastani, O., Sungu, A., Ge, H., Kabakcı, Ö., & Mariman, R. (2025). Generative AI without guardrails can harm learning: Evidence from high school mathematics. *Proceedings of the National Academy of Sciences, 122*, e2422633122.
- Badrinath, A., Wang, F., & Pardos, Z. (2021). pyBKT: An accessible library of Bayesian knowledge tracing models. *Proceedings of the 14th International Conference on Educational Data Mining (EDM 2021).* arXiv:2105.00385.
- Corbett, A. T., & Anderson, J. R. (1995). Knowledge tracing: Modeling the acquisition of procedural knowledge. *User Modeling and User-Adapted Interaction, 4*(4), 253–278. https://doi.org/10.1007/BF01099821
- Feng, M., Heffernan, N., & Koedinger, K. (2009). Addressing the assessment challenge with an online system that tutors as it assesses. *User Modeling and User-Adapted Interaction, 19*(3), 243–266.
- Gao, L., Madaan, A., Zhou, S., Alon, U., Liu, P., Yang, Y., Callan, J., & Neubig, G. (2023). PAL: Program-aided language models. *Proceedings of the 40th International Conference on Machine Learning (ICML 2023)*, PMLR 202, 10764–10799.
- Macina, J., et al. (2023). MathDial: A dialogue tutoring dataset with rich pedagogical properties grounded in math reasoning problems. *Findings of the Association for Computational Linguistics: EMNLP 2023*, 5602–5621.
- Meurer, A., et al. (2017). SymPy: Symbolic computing in Python. *PeerJ Computer Science, 3*, e103. https://doi.org/10.7717/peerj-cs.103
- Pardos, Z. A., & Bhandari, S. (2024). ChatGPT-generated help produces learning gains equivalent to human tutor-authored help on mathematics skills. *PLOS ONE, 19*, e0304013.
- Pandey, S., & Karypis, G. (2019). A self-attentive model for knowledge tracing. *Proceedings of the 12th International Conference on Educational Data Mining (EDM 2019)*, 384–389.
- Piech, C., Bassen, J., Huang, J., Ganguli, S., Sahami, M., Guibas, L., & Sohl-Dickstein, J. (2015). Deep knowledge tracing. *Advances in Neural Information Processing Systems 28 (NIPS 2015)*, 505–513.
- Wang, R. E., Zhang, Q., Robinson, C., Loeb, S., & Demszky, D. (2024). Bridging the novice-expert gap via models of decision-making: A case study on remediating math mistakes. *Proceedings of NAACL 2024*, 2174–2199.

---

## Appendix: where things are in the repository

| Item | Path |
|---|---|
| Preprocessing, DKT, BKT, evaluation | `ml/` |
| Skills, courses and lessons, generator, grader | `backend/app/skills.py`, `courses.py`, `problems.py`, `grader.py` |
| Mastery (DKT + BKT), recommendation | `backend/app/mastery.py`, `bkt.py`, `recommend.py` |
| Hints, tutor, API | `backend/app/hints.py`, `tutor.py`, `main.py` |
| Experiments and logs | `experiments/` (`results.md`, `hint_audit.md`, raw `.jsonl`) |
| Frontend | `frontend/` |
| Deployment | `backend/Dockerfile`, `render.yaml`, `DEPLOY.md` |
