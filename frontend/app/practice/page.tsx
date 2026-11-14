"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { MasteryList } from "@/components/Mastery";
import { api, type AttemptResult, type GradeStatus, type MasteryReport, type Problem } from "@/lib/api";
import { useUserId } from "@/lib/user";

const PLACEHOLDER: Record<Problem["kind"], string> = {
  solve: "x = …",
  simplify: "e.g. 2x + 7",
  evaluate: "a number",
};

const FEEDBACK_STYLE: Record<GradeStatus, string> = {
  correct: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  not_simplified: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  incorrect: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100",
  invalid: "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
};

const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

export default function Practice() {
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [report, setReport] = useState<MasteryReport | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [choice, setChoice] = useState(""); // "" means "let the tutor recommend"
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // No saved user id: go back to the start page.
  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  const loadProblem = useCallback(async (uid: string, skill: string) => {
    setBusy(true);
    setError(null);
    try {
      const [p, m] = await Promise.all([api.nextProblem(uid, skill || undefined), api.mastery(uid)]);
      setProblem(p);
      setReport(m);
      setAnswer("");
      setResult(null);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }, []);

  // New problem on first load and whenever the skill choice changes.
  useEffect(() => {
    if (userId) loadProblem(userId, choice);
  }, [userId, choice, loadProblem]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!userId || !problem || !answer.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.submit(userId, problem.id, answer);
      setResult(r);
      setReport(r.mastery); // the backend returns updated mastery with every grade
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  if (!userId) return null;
  const solved = result?.correct ?? false;
  const isRecommended = !choice && problem && report && problem.skill === report.recommended;

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_18rem]">
      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Signed in as <span className="font-medium text-slate-700 dark:text-slate-200">{userId}</span> ·{" "}
            <Link href="/" className="underline">
              change
            </Link>
          </p>
          <label className="flex items-center gap-2 text-sm">
            Skill
            <select
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Recommended</option>
              {report?.skills.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.unlocked ? "" : " (locked)"}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
            {error}
          </div>
        )}

        {problem && (
          <div className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{problem.skill_name}</p>
            {isRecommended && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Recommended: your lowest-mastery skill whose prerequisites you&apos;ve mastered.
              </p>
            )}
            <p className="mt-4">{problem.prompt}</p>
            <p className="mt-2 font-mono text-2xl sm:text-3xl break-words">{problem.expression}</p>

            <form onSubmit={submit} className="mt-6 flex flex-col gap-3 sm:flex-row">
              <input
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder={PLACEHOLDER[problem.kind]}
                disabled={solved || busy}
                autoComplete="off"
                autoFocus
                aria-label="Your answer"
                className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 font-mono dark:border-slate-700 dark:bg-slate-950"
              />
              {solved ? (
                <button
                  type="button"
                  onClick={() => loadProblem(userId, choice)}
                  disabled={busy}
                  className="rounded-md bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  Next problem
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={busy || !answer.trim()}
                  className="rounded-md bg-sky-600 px-4 py-2 font-medium text-white hover:bg-sky-700 disabled:opacity-50"
                >
                  Check
                </button>
              )}
            </form>

            {result && (
              <div className={`mt-4 rounded-md border p-3 text-sm ${FEEDBACK_STYLE[result.status]}`} role="status">
                {result.message}
                {!result.counts_for_mastery && result.status !== "invalid" && (
                  <span className="mt-1 block text-xs opacity-80">
                    Only your first try on each problem counts toward mastery.
                  </span>
                )}
              </div>
            )}

            {!solved && (
              <button
                type="button"
                onClick={() => loadProblem(userId, choice)}
                disabled={busy}
                className="mt-4 text-sm text-slate-500 underline hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
              >
                Skip to another problem
              </button>
            )}
          </div>
        )}
      </section>

      <aside>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-semibold">Mastery</h2>
          <Link href="/dashboard" className="text-sm underline">
            Dashboard
          </Link>
        </div>
        {report && <MasteryList skills={report.skills} threshold={report.threshold} recommended={report.recommended} />}
      </aside>
    </div>
  );
}
