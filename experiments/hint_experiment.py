"""Experiment 2: hint error/leak rate WITH vs WITHOUT the SymPy check.

Design (paired): for each test case we run the verified hint loop once. The
LLM's FIRST proposal is exactly what the unverified system would show (same
prompt, no feedback), so both conditions are scored on the same LLM outputs.
This halves API cost and removes LLM sampling noise from the comparison.

Test cases: problems sampled with a fixed seed, `--per-skill` per skill.
Each problem is asked for a hint at its start; equation problems are also
asked at their real last step "cx = d" (all x terms and numbers collected),
where the only step left is the answer and leaking is most tempting. Problems
whose last step is the start itself or already "x = ..." are skipped there.

Each hint the student WOULD SEE is scored with:
  - math error:     next_step is unparseable, not equivalent, or makes no progress
  - leak (checker): the same leak checks the verifier uses
  - leak (broad):   the answer's value appears anywhere in hint or next_step.
                    Over-counts (e.g. a coefficient equal to the answer), so it
                    is an upper bound that doesn't depend on our own checker.

Usage (from repo root; costs real API credit unless --fake):
    .venv/bin/python experiments/hint_experiment.py --per-skill 10
    .venv/bin/python experiments/hint_experiment.py --fake      # free dry run
    .venv/bin/python experiments/hint_experiment.py --rescore experiments/results/<file>.jsonl
        # re-score saved outputs with the current checker (no API calls)
"""

import argparse
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "backend"), str(REPO)]

from dotenv import load_dotenv  # noqa: E402
from sympy import expand  # noqa: E402

from app.hints import (  # noqa: E402
    ClaudeHintLLM,
    HintProposal,
    check_hint,
    generate_hint,
)
from app.grader import X, parse_math  # noqa: E402
from app.problems import generate_problem  # noqa: E402
from app.skills import topological_order  # noqa: E402

SEED = 42
RESULTS_MD = REPO / "experiments" / "results.md"
OUT_DIR = REPO / "experiments" / "results"
# USD per million tokens (input, output), for the cost estimate only.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}

MATH_ERRORS = {"not_equivalent", "no_progress", "unparseable", "empty_hint"}
LEAKS = {"leak_text", "leak_step"}


def make_cases(per_skill: int) -> list[dict]:
    rng = random.Random(SEED)
    cases = []
    for skill in topological_order():
        for _ in range(per_skill):
            p = generate_problem(skill, rng.randrange(10**9))
            cases.append({"problem": p, "state": "start", "current": p.expression})
            last = last_step(p)
            if last:
                cases.append({"problem": p, "state": "last_step", "current": last})
    return cases


def last_step(p) -> str | None:
    """The equation just before the answer: lhs - rhs = c*x + d  ->  "cx = -d"."""
    if p.kind != "solve":
        return None
    lhs, rhs = p.expression.split("=")
    e = expand(parse_math(lhs) - parse_math(rhs))
    c, d = e.coeff(X), e.subs(X, 0)
    if not c.is_integer or abs(c) == 1:  # x/a = q forms, or already "x = ..."
        return None
    step = f"{c}x = {-d}"
    return None if step.replace(" ", "") == p.expression.replace(" ", "") else step


def broad_leak(problem, text: str) -> bool:
    t = text.replace(" ", "").replace("−", "-")
    ans = problem.answer.replace(" ", "")
    if problem.kind == "simplify":
        return ans in t
    # The answer as a standalone number: "-6" but not "-61" or "6" inside "-6"... and
    # for positive answers, not when it's really part of a negative number.
    sign = "" if ans.startswith("-") else r"(?<!-)"
    return re.search(rf"(?<![\d.]){sign}{re.escape(ans)}(?![\d])", t) is not None


def score(problem, current, hint: str, next_step: str) -> dict:
    issues = check_hint(problem, current, HintProposal(hint=hint, next_step=next_step))
    codes = sorted({i.code for i in issues})
    return {
        "hint": hint,
        "next_step": next_step,
        "codes": codes,
        "math_error": any(c in MATH_ERRORS for c in codes),
        "leak_checker": any(c in LEAKS for c in codes),
        "leak_broad": broad_leak(problem, hint + " " + next_step),
    }


class Recording:
    """Wraps the LLM for one case and remembers what it proposed."""

    def __init__(self, inner):
        self.inner, self.first, self.calls = inner, None, 0

    def propose(self, problem, current, rejections):
        self.calls += 1
        out = self.inner.propose(problem, current, rejections)  # errors propagate to generate_hint
        if self.calls == 1:
            self.first = out
        return out


def run_case(case: dict, llm) -> dict:
    p, current = case["problem"], case["current"]
    rec = Recording(llm)
    t = time.time()
    result = generate_hint(p, current, rec)
    row = {
        "problem_id": p.id, "skill": p.skill, "state": case["state"], "expression": p.expression,
        "answer": p.answer, "current": current, "seconds_verified": round(time.time() - t, 2),
        "llm_calls_verified": result.attempts, "source_verified": result.source,
        "rejections": list(result.rejections),
    }
    # Condition A (no check) = the first proposal, shown as-is.
    row["without_check"] = (
        score(p, current, rec.first.hint, rec.first.next_step.strip()) if rec.first else {"no_hint": True}
    )
    # Condition B (with check) = what generate_hint actually returned.
    row["with_check"] = score(p, current, result.hint, result.next_step)
    return row


def summarize(rows: list[dict], key: str) -> dict:
    scored = [r[key] for r in rows if not r[key].get("no_hint")]
    n = len(scored)
    pct = lambda f: round(100 * sum(1 for s in scored if s[f]) / n, 1) if n else 0.0  # noqa: E731
    return {"n": n, "math_error": pct("math_error"), "leak_checker": pct("leak_checker"), "leak_broad": pct("leak_broad")}


class FakeLLM:
    """Free dry run: a mix of good, wrong and leaking proposals."""

    def __init__(self):
        self.model, self.usage, self.rng = "fake", {"input_tokens": 0, "output_tokens": 0, "calls": 0}, random.Random(0)

    def propose(self, problem, current, rejections):
        self.usage["calls"] += 1
        r = self.rng.random()
        if r < 0.2:
            return HintProposal(hint=f"The answer is x = {problem.answer}.", next_step="")
        if r < 0.4:
            return HintProposal(hint="Try this.", next_step="x = 999" if problem.kind == "solve" else "999")
        return HintProposal(hint="Undo the operations on x one at a time, starting with the constant.", next_step="")


def print_table(a: dict, b: dict) -> None:
    print(f"\n{'condition':<15}{'n':>5}{'math err %':>12}{'leak % (checker)':>18}{'leak % (broad)':>16}")
    for name, s in [("without check", a), ("with check", b)]:
        print(f"{name:<15}{s['n']:>5}{s['math_error']:>12}{s['leak_checker']:>18}{s['leak_broad']:>16}")


def rescore(path: Path) -> None:
    """Recompute the scores of saved hints with the current check_hint/broad_leak.
    The hints themselves (what students would have seen) are unchanged."""
    path = path.resolve()
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for r in rows:
        p = generate_problem(r["skill"], int(r["problem_id"].split(":")[1]))
        for key in ("without_check", "with_check"):
            if not r[key].get("no_hint"):
                r[key] = score(p, r["current"], r[key]["hint"], r[key]["next_step"])
    out = path.with_name(path.stem + "-rescored.jsonl")
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    a, b = summarize(rows, "without_check"), summarize(rows, "with_check")
    print_table(a, b)
    model = path.stem.split("-2026")[0].removeprefix("hints-")
    text = RESULTS_MD.read_text()
    notes = f"RESCORED {path.name} with fixed leak checker (no new API calls) -> {out.relative_to(REPO)}"
    text += f"| {date.today()} | {model} | without check | {a['n']} | {a['math_error']} | {a['leak_checker']} | {a['leak_broad']} | (see run) | (see run) | (see run) | {notes} |\n"
    text += f"| {date.today()} | {model} | with check | {b['n']} | {b['math_error']} | {b['leak_checker']} | {b['leak_broad']} | (see run) | (see run) | (see run) | {notes} |\n"
    RESULTS_MD.write_text(text)
    print(f"logged to {RESULTS_MD.relative_to(REPO)}; rescored rows in {out.relative_to(REPO)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-skill", type=int, default=10)
    ap.add_argument("--model", default=None, help="defaults to HINT_MODEL or claude-opus-5-5")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--fake", action="store_true", help="no API calls; doesn't write results.md")
    ap.add_argument("--rescore", type=Path, help="re-score a saved .jsonl with the current checker")
    args = ap.parse_args()
    if args.rescore:
        return rescore(args.rescore)

    load_dotenv(REPO / ".env")
    llm = FakeLLM() if args.fake else ClaudeHintLLM(model=args.model)
    cases = make_cases(args.per_skill)
    print(f"{len(cases)} hint requests, model={llm.model}")

    with ThreadPoolExecutor(args.workers) as pool:
        rows = list(pool.map(lambda c: run_case(c, llm), cases))

    a, b = summarize(rows, "without_check"), summarize(rows, "with_check")
    fallback = round(100 * sum(r["source_verified"] == "fallback" for r in rows) / len(rows), 1)
    calls = round(sum(r["llm_calls_verified"] for r in rows) / len(rows), 2)
    secs = round(sum(r["seconds_verified"] for r in rows) / len(rows), 1)
    u = llm.usage
    price = PRICES.get(llm.model)
    cost = f"${(u['input_tokens'] * price[0] + u['output_tokens'] * price[1]) / 1e6:.2f}" if price else "n/a"

    print_table(a, b)
    print(f"\nwith check: fallback {fallback}%, {calls} LLM calls/hint, {secs}s/hint")
    print(f"tokens: {u['input_tokens']} in / {u['output_tokens']} out over {u['calls']} calls, est. cost {cost}")

    if args.fake:
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"hints-{llm.model}-{date.today()}.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    header = "\n## Experiment 2: hint verification\n\n| date | model | condition | n | math error % | leak % (checker) | leak % (broad) | fallback % | LLM calls/hint | s/hint | notes |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
    text = RESULTS_MD.read_text()
    if "## Experiment 2" not in text:
        text += header
    notes = f"seed={SEED}, per_skill={args.per_skill}, paired, raw: {out.relative_to(REPO)}, cost {cost}"
    text += f"| {date.today()} | {llm.model} | without check | {a['n']} | {a['math_error']} | {a['leak_checker']} | {a['leak_broad']} | n/a | 1 | n/a | {notes} |\n"
    text += f"| {date.today()} | {llm.model} | with check | {b['n']} | {b['math_error']} | {b['leak_checker']} | {b['leak_broad']} | {fallback} | {calls} | {secs} | {notes} |\n"
    RESULTS_MD.write_text(text)
    print(f"\nlogged to {RESULTS_MD.relative_to(REPO)} and {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
