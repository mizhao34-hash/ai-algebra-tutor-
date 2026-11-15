"use client";

// Plays a worked example one step at a time. For each step:
//   1. the operation label appears ("Subtract 5 from both sides"),
//   2. in the previous line, the parts that go away are struck through,
//   3. the new line slides in with its new parts glowing green,
//   4. if an inequality sign flips, the sign itself spins and turns red.
// Every line was verified by SymPy on the server before reaching the browser.
import { useEffect, useMemo, useState } from "react";
import type { Walkthrough } from "@/lib/api";
import { pretty } from "@/lib/math";

/** Split pretty math into pieces, keeping the original spaces as their own
 *  pieces (so "x ≤ -1" is displayed exactly as written). Only the non-space
 *  pieces (numbers, x, √49, operators, words) take part in the diff. */
function tokenize(line: string): string[] {
  return pretty(line).match(/\s+|√?\d+(?:\.\d+)?|x[²³⁴]?|≤|≥|[<>=+\-−×÷*/()]|[a-z]+|./gi) ?? [];
}
const isSpace = (t: string) => /^\s+$/.test(t);

/** Longest-common-subsequence diff over the non-space pieces: which pieces of
 *  `a` were removed and which of `b` were added (indices into the full arrays). */
function diff(fullA: string[], fullB: string[]): { removed: boolean[]; added: boolean[] } {
  const ia = fullA.flatMap((t, i) => (isSpace(t) ? [] : [i]));
  const ib = fullB.flatMap((t, i) => (isSpace(t) ? [] : [i]));
  const inner = lcsDiff(ia.map((i) => fullA[i]), ib.map((i) => fullB[i]));
  const removed = new Array<boolean>(fullA.length).fill(false);
  const added = new Array<boolean>(fullB.length).fill(false);
  ia.forEach((i, k) => (removed[i] = inner.removed[k]));
  ib.forEach((i, k) => (added[i] = inner.added[k]));
  return { removed, added };
}

function lcsDiff(a: string[], b: string[]): { removed: boolean[]; added: boolean[] } {
  const n = a.length, m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--) dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const removed = new Array<boolean>(n).fill(true), added = new Array<boolean>(m).fill(true);
  for (let i = 0, j = 0; i < n && j < m; ) {
    if (a[i] === b[j]) {
      removed[i] = added[j] = false;
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) i++;
    else j++;
  }
  return { removed, added };
}

const RELATIONS = ["<", ">", "≤", "≥"];
const direction = (tokens: string[]) => {
  const op = tokens.find((t) => RELATIONS.includes(t));
  return op ? (op === "<" || op === "≤" ? "less" : "greater") : null;
};

function Tokens({ tokens, mark }: { tokens: string[]; mark: (i: number, t: string) => string }) {
  return (
    <>
      {tokens.map((t, i) => (isSpace(t) ? <span key={i}>{t}</span> : <span key={i} className={mark(i, t)}>{t}</span>))}
    </>
  );
}

const STEP_MS = 2200;

export function WalkthroughPlayer({ walkthrough }: { walkthrough: Walkthrough }) {
  const lines = useMemo(() => [walkthrough.problem, ...walkthrough.steps.map((s) => s.result)].map(tokenize), [walkthrough]);
  const total = walkthrough.steps.length;
  const [shown, setShown] = useState(0); // how many steps are visible (0 = just the problem)
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing || shown >= total) return;
    const id = setTimeout(() => setShown((s) => s + 1), shown === 0 ? 900 : STEP_MS);
    return () => clearTimeout(id);
  }, [playing, shown, total]);

  useEffect(() => {
    if (shown >= total) setPlaying(false);
  }, [shown, total]);

  // The latest transition is the one we animate.
  const last = shown > 0 ? diff(lines[shown - 1], lines[shown]) : null;
  const flipped = shown > 0 && direction(lines[shown - 1]) !== null && direction(lines[shown - 1]) !== direction(lines[shown]);

  const ctrl =
    "rounded-md px-2.5 py-1 text-xs font-semibold text-violet-900 hover:bg-violet-200 disabled:opacity-40 dark:text-violet-100 dark:hover:bg-violet-900";

  return (
    <div className="mt-3 rounded-xl border border-violet-200 bg-white p-3 dark:border-violet-900 dark:bg-slate-950">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-violet-700 dark:text-violet-300">
        Worked example · step {shown} of {total}
      </p>
      <ol className="space-y-1 font-mono text-[15px]">
        {lines.slice(0, shown + 1).map((tokens, i) => {
          const isPrev = shown > 0 && i === shown - 1;
          const isNew = shown > 0 && i === shown;
          const isFinal = i === total && shown === total;
          return (
            <li key={i} className={isNew ? "tutor-fade-up" : ""}>
              {i > 0 && (
                <p className="tutor-fade-up my-1 flex items-center gap-1.5 font-sans text-xs text-violet-800 dark:text-violet-200">
                  <span aria-hidden>↓</span>
                  <span className="rounded-full bg-violet-100 px-2 py-0.5 font-medium dark:bg-violet-900/60">
                    {pretty(walkthrough.steps[i - 1].operation)}
                  </span>
                  {isNew && flipped && (
                    <span className="rounded-full bg-rose-100 px-2 py-0.5 font-semibold text-rose-800 dark:bg-rose-900/60 dark:text-rose-100">
                      sign flips!
                    </span>
                  )}
                </p>
              )}
              <p className={`whitespace-pre-wrap rounded px-1 ${isFinal ? "font-bold text-violet-800 dark:text-violet-200" : ""}`}>
                <Tokens
                  tokens={tokens}
                  mark={(j, t) => {
                    if (isPrev && last?.removed[j]) return "tutor-removed";
                    if (isNew && flipped && RELATIONS.includes(t)) return "tutor-flip";
                    if (isNew && last?.added[j]) return "tutor-added";
                    return "";
                  }}
                />
              </p>
            </li>
          );
        })}
      </ol>
      <div className="mt-3 flex flex-wrap items-center gap-1 border-t border-violet-100 pt-2 dark:border-violet-900">
        <button className={ctrl} onClick={() => setShown((s) => Math.max(0, s - 1))} disabled={shown === 0} aria-label="Previous step">
          ◀ Back
        </button>
        {shown < total ? (
          <button className={ctrl} onClick={() => setPlaying((p) => !p)}>
            {playing ? "❚❚ Pause" : "▶ Play"}
          </button>
        ) : (
          <button
            className={ctrl}
            onClick={() => {
              setShown(0);
              setPlaying(true);
            }}
          >
            ↺ Replay
          </button>
        )}
        <button className={ctrl} onClick={() => setShown((s) => Math.min(total, s + 1))} disabled={shown === total} aria-label="Next step">
          Next ▶
        </button>
        <span className="ml-auto text-[11px] text-slate-500 dark:text-slate-400" title="Every step was checked by a computer algebra system">
          ✓ steps checked
        </span>
      </div>
    </div>
  );
}
