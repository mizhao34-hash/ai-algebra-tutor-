"""Experiment 3: how reliable are the AI tutor's animated walkthroughs, and
what does the SymPy check catch?

Design (paired, like experiment 2): each request runs the real tutor loop
(ask_tutor). The LLM's FIRST reply is what a tutor WITHOUT the check would show;
the final result is what students actually see. Both are scored by check_reply
(math errors, answer leaks).

Requests, per unit (8 units):
  - 3 x "Explain this unit" (mode explain_unit)
  - 2 x "I'm stuck, can you just tell me the answer?" while a practice problem
    from that unit is on screen (tests the no-answer rule)

Usage (from repo root; costs API credit, roughly $0.50):
    .venv/bin/python experiments/tutor_experiment.py
"""

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "backend"), str(REPO)]

from dotenv import load_dotenv  # noqa: E402

from app.courses import UNITS  # noqa: E402
from app.problems import generate_problem  # noqa: E402
from app.tutor import ClaudeTutorLLM, TutorContext, ask_tutor, check_reply  # noqa: E402

SEED = 42
RESULTS_MD = REPO / "experiments" / "results.md"
OUT_DIR = REPO / "experiments" / "results"
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

MATH = ("not mathematically valid", "can't be parsed", "both a starting problem", "at most")
LEAK = ("reveals the answer", "same answer", "step label reveals")


def make_cases() -> list[dict]:
    rng = random.Random(SEED)
    cases = []
    for unit_id, (course_id, unit) in UNITS.items():
        for _ in range(3):
            cases.append({"kind": "explain_unit", "course": course_id, "unit": unit_id, "problem": None,
                          "messages": [{"role": "user", "content": "Please explain this unit to me with an example."}]})
        for _ in range(2):
            p = generate_problem(rng.choice(unit.skills), rng.randrange(10**9))
            cases.append({"kind": "ask_answer", "course": course_id, "unit": unit_id, "problem": p,
                          "messages": [{"role": "user", "content": "I'm stuck, can you just tell me the answer?"}]})
    return cases


class Recording:
    def __init__(self, inner):
        self.inner, self.first = inner, None

    def reply(self, system, messages, rejections):
        out = self.inner.reply(system, messages, rejections)
        if self.first is None:
            self.first = out
        return out


def categorize(issues: list[str]) -> dict:
    return {
        "math_error": any(any(k in i for k in MATH) for i in issues),
        "leak": any(any(k in i for k in LEAK) for i in issues),
    }


def run(case: dict, llm) -> dict:
    ctx = TutorContext(mode="explain_unit" if case["kind"] == "explain_unit" else "chat",
                       course=case["course"], unit=case["unit"], problem=case["problem"])
    rec = Recording(llm)
    t = time.time()
    result = ask_tutor(case["messages"], ctx, rec)
    first_issues = check_reply(rec.first, ctx) if rec.first else ["no reply"]
    return {
        "kind": case["kind"], "unit": case["unit"],
        "problem": case["problem"].expression if case["problem"] else None,
        "seconds": round(time.time() - t, 2), "attempts": result.attempts, "source": result.source,
        "first": {"message": rec.first.message if rec.first else None,
                  "walkthrough": rec.first.walkthrough.model_dump() if rec.first else None,
                  "has_walkthrough": bool(rec.first and rec.first.walkthrough.steps),
                  "issues": first_issues, **categorize(first_issues)},
        "shown": {"message": result.message,
                  "walkthrough": result.walkthrough.model_dump() if result.walkthrough else None,
                  "verified_walkthrough": result.verified, "fallback": result.source == "fallback"},
        "rejections": result.rejections,
    }


def pct(n, d):
    return round(100 * n / d, 1) if d else 0.0


def main():
    load_dotenv(REPO / ".env")
    llm = ClaudeTutorLLM()
    cases = make_cases()
    print(f"{len(cases)} tutor requests, model={llm.model}")
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(lambda c: run(c, llm), cases))

    n = len(rows)
    first_math = sum(r["first"]["math_error"] for r in rows)
    first_leak = sum(r["first"]["leak"] for r in rows)
    first_with_w = sum(r["first"]["has_walkthrough"] for r in rows)
    shown_verified = sum(r["shown"]["verified_walkthrough"] for r in rows)
    text_only = sum((not r["shown"]["verified_walkthrough"]) and not r["shown"]["fallback"] for r in rows)
    fallback = sum(r["shown"]["fallback"] for r in rows)
    calls = round(sum(r["attempts"] for r in rows) / n, 2)
    secs = round(sum(r["seconds"] for r in rows) / n, 1)
    u = llm.usage
    price = PRICES.get(llm.model)
    cost = f"${(u['input_tokens'] * price[0] + u['output_tokens'] * price[1]) / 1e6:.2f}" if price else "n/a"

    print(f"\nwithout check (first reply): walkthrough in {pct(first_with_w, n)}%, "
          f"math error {pct(first_math, n)}%, leak {pct(first_leak, n)}%")
    print(f"with check (shown): verified walkthrough {pct(shown_verified, n)}%, text only {pct(text_only, n)}%, "
          f"fallback {pct(fallback, n)}%, {calls} calls/request, {secs}s/request")
    print(f"tokens {u['input_tokens']} in / {u['output_tokens']} out, est. cost {cost}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"tutor-{llm.model}-{date.today()}.jsonl"
    out.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows))
    text = RESULTS_MD.read_text()
    if "## Experiment 3" not in text:
        text += ("\n## Experiment 3: AI tutor walkthroughs\n\n"
                 "| date | model | n | first reply: math error % | first reply: leak % | shown: verified walkthrough % "
                 "| shown: text only % | shown: fallback % | LLM calls/request | s/request | notes |\n"
                 "|---|---|---|---|---|---|---|---|---|---|---|\n")
    text += (f"| {date.today()} | {llm.model} | {n} | {pct(first_math, n)} | {pct(first_leak, n)} | "
             f"{pct(shown_verified, n)} | {pct(text_only, n)} | {pct(fallback, n)} | {calls} | {secs} | "
             f"seed={SEED}, 8 units x (3 explain + 2 ask-for-answer), paired; raw: {out.relative_to(REPO)}; cost {cost} |\n")
    RESULTS_MD.write_text(text)
    print(f"logged to {RESULTS_MD.relative_to(REPO)} and {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
