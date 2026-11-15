"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ArrowRightIcon, CheckIcon, LightbulbIcon, SkipIcon, WarningIcon, XIcon } from "@/components/Icons";
import { MasteryList } from "@/components/Mastery";
import { useTutorPage } from "@/components/tutor/TutorProvider";
import { api, type AttemptResult, type GradeStatus, type Hint, type MasteryReport, type Problem } from "@/lib/api";
import { pretty } from "@/lib/math";
import { btn, card, theme } from "@/lib/ui";
import { useUserId } from "@/lib/user";

const PLACEHOLDER: Record<Problem["kind"], string> = {
  solve: "x = …",
  simplify: "e.g. 2x + 7",
  evaluate: "a number",
  inequality: "e.g. x > 3 or x <= -2",
};

// Each result has its own color AND icon, so it's clear even without color.
const FEEDBACK: Record<GradeStatus, { style: string; Icon: typeof CheckIcon; title: string }> = {
  correct: {
    style: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
    Icon: CheckIcon,
    title: "Correct",
  },
  not_simplified: {
    style: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
    Icon: WarningIcon,
    title: "Almost",
  },
  incorrect: {
    style: "border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100",
    Icon: XIcon,
    title: "Not yet",
  },
  invalid: {
    style: "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
    Icon: WarningIcon,
    title: "Couldn't read that",
  },
};

const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));

// useSearchParams() needs a Suspense boundary in the Next.js app router.
export default function PracticePage() {
  return (
    <Suspense>
      <PracticeFromUrl />
    </Suspense>
  );
}

// Lesson links pass ?skill=... ("Practice this topic") or ?unit=... ("Practice this unit").
// The key remounts Practice when they change, so its state starts fresh.
function PracticeFromUrl() {
  const params = useSearchParams();
  const skill = params.get("skill") ?? "";
  const unit = params.get("unit") ?? undefined;
  return <Practice key={`${unit}|${skill}`} initialSkill={skill} unit={unit} />;
}

function Practice({ initialSkill, unit }: { initialSkill: string; unit?: string }) {
  const router = useRouter();
  const { courseId } = useParams<{ courseId: string }>();
  const t = theme(courseId);
  const [userId, loaded] = useUserId();
  const [report, setReport] = useState<MasteryReport | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [choice, setChoice] = useState(initialSkill); // "" means "let the tutor recommend"
  const [hints, setHints] = useState<Hint[]>([]); // hints so far for this problem, oldest first
  const [hintBusy, setHintBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The AI tutor knows the unit and the problem on screen (and won't give its answer).
  useTutorPage({ unit, problemId: problem?.id });

  // No saved user id: go back to the start page.
  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  const loadProblem = useCallback(
    async (uid: string, skill: string) => {
      setBusy(true);
      setError(null);
      try {
        const [p, m] = await Promise.all([
          api.nextProblem(uid, skill || undefined, courseId, unit),
          api.mastery(uid, courseId, unit),
        ]);
        setProblem(p);
        setReport(m);
        setAnswer("");
        setResult(null);
        setHints([]);
      } catch (e) {
        setError(errorText(e));
      } finally {
        setBusy(false);
      }
    },
    [courseId, unit],
  );

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
      const r = await api.submit(userId, problem.id, answer, courseId, unit);
      setResult(r);
      setReport(r.mastery); // the backend returns updated mastery with every grade
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  async function getHint() {
    if (!userId || !problem) return;
    // Each hint continues from the last step shown, so hints walk through the solution.
    const lastStep = [...hints].reverse().find((h) => h.next_step)?.next_step;
    setHintBusy(true);
    setError(null);
    try {
      const h = await api.hint(userId, problem.id, lastStep);
      setHints((prev) => [...prev, h]);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setHintBusy(false);
    }
  }

  if (!userId) return null;
  const solved = result?.correct ?? false;
  const isRecommended = !choice && problem && report && problem.skill === report.recommended;
  // An LLM hint with no next_step means the next step IS the answer: no more hints.
  const lastHint = hints[hints.length - 1];
  const hintsDone = lastHint !== undefined && lastHint.source === "llm" && !lastHint.next_step;
  const feedback = result ? FEEDBACK[result.status] : null;

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_17rem]">
      <section className="min-w-0">
        {/* Scope + skill picker */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {report?.unit ? (
              <>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${t.soft}`}>Unit</span>{" "}
                <span className="font-semibold">{report.unit.name}</span>
                <Link href={`/courses/${courseId}/practice`} className={`ml-3 ${btn.subtle}`}>
                  Practice whole course
                </Link>
              </>
            ) : (
              <>
                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${t.soft}`}>Course</span>{" "}
                <span className="font-semibold">All units</span>
              </>
            )}
          </p>
          <label className="flex items-center gap-2 text-sm font-medium">
            Topic
            <select
              value={choice}
              onChange={(e) => setChoice(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Recommended for you</option>
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
          <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
            {error}
          </div>
        )}

        {!problem && !error && (
          <div className={`${card} p-6 text-sm text-slate-500 dark:text-slate-400`}>
            Loading your next problem… If the server was idle, it can take up to a minute to wake up.
          </div>
        )}

        {problem && (
          <div className={card}>
            {/* Problem */}
            <div className="border-b border-slate-200 p-6 dark:border-slate-800">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`text-sm font-semibold ${t.text}`}>{problem.skill_name}</span>
                {isRecommended && (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                    Recommended for you
                  </span>
                )}
              </div>
              <p className="mt-4 text-slate-700 dark:text-slate-200">{problem.prompt}</p>
              <p className="mt-3 rounded-lg bg-slate-50 px-4 py-5 text-center font-mono text-3xl tracking-wide break-words dark:bg-slate-950">
                {pretty(problem.expression)}
              </p>
              {isRecommended && (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Chosen because it&apos;s your lowest-mastery topic in this {report?.unit ? "unit" : "course"} whose
                  prerequisites you&apos;ve mastered.
                </p>
              )}
            </div>

            {/* Answer */}
            <div className="p-6">
              <form onSubmit={submit}>
                <label htmlFor="answer" className="text-sm font-semibold">
                  Your answer
                </label>
                <div className="mt-2 flex flex-col gap-3 sm:flex-row">
                  <input
                    id="answer"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    // Quadratics have two answers; show the format we accept.
                    placeholder={problem.prompt.includes("both") ? "x = …, x = …" : PLACEHOLDER[problem.kind]}
                    disabled={solved || busy}
                    autoComplete="off"
                    autoFocus
                    aria-label="Your answer"
                    className="flex-1 rounded-lg border-2 border-slate-300 bg-white px-3 py-2.5 font-mono text-lg focus:border-slate-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950"
                  />
                  {solved ? (
                    <button type="button" onClick={() => loadProblem(userId, choice)} disabled={busy} className={btn.primary(t, "lg")}>
                      Next problem <ArrowRightIcon />
                    </button>
                  ) : (
                    <button type="submit" disabled={busy || !answer.trim()} className={btn.primary(t, "lg")}>
                      <CheckIcon /> Check
                    </button>
                  )}
                </div>
              </form>

              {result && feedback && (
                <div className={`mt-4 flex gap-3 rounded-lg border p-3 text-sm ${feedback.style}`} role="status">
                  <feedback.Icon className="mt-0.5 h-5 w-5 shrink-0" />
                  <div>
                    <p className="font-semibold">{feedback.title}</p>
                    <p>{result.message}</p>
                    {!result.counts_for_mastery && result.status !== "invalid" && (
                      <p className="mt-1 text-xs opacity-80">Only your first try on each problem counts toward mastery.</p>
                    )}
                  </div>
                </div>
              )}

              {hints.length > 0 && (
                <ol className="mt-4 space-y-2">
                  {hints.map((h, i) => (
                    <li
                      key={i}
                      className="flex gap-3 rounded-lg border border-violet-200 bg-violet-50 p-3 text-sm text-violet-950 dark:border-violet-900 dark:bg-violet-950 dark:text-violet-100"
                    >
                      <LightbulbIcon className="mt-0.5 h-5 w-5 shrink-0" />
                      <div>
                        <p className="font-semibold">Hint {i + 1}</p>
                        <p>{h.hint}</p>
                        {h.next_step && <p className="mt-1 font-mono text-base">→ {pretty(h.next_step)}</p>}
                      </div>
                    </li>
                  ))}
                </ol>
              )}

              {/* Help and skip: clearly secondary to Check */}
              {!solved && (
                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
                  <button type="button" onClick={getHint} disabled={hintBusy || busy || hintsDone} className={btn.hint}>
                    <LightbulbIcon />
                    {hintBusy ? "Thinking…" : hints.length ? "Next hint" : "Get a hint"}
                  </button>
                  <button type="button" onClick={() => loadProblem(userId, choice)} disabled={busy} className={btn.subtle}>
                    Skip this problem <SkipIcon />
                  </button>
                </div>
              )}
              {!solved && !result && hints.length === 0 && (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Using a hint before your first answer means this problem won&apos;t count as solved on your own.
                </p>
              )}
              {hintsDone && !solved && (
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">That&apos;s the last hint: the next step is the answer.</p>
              )}
            </div>
          </div>
        )}
      </section>

      <aside className={`${card} h-fit p-4`}>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-semibold">Your mastery</h2>
          <Link href={`/courses/${courseId}`} className={btn.subtle}>
            Review lesson
          </Link>
        </div>
        {report && <MasteryList skills={report.skills} threshold={report.threshold} recommended={report.recommended} />}
      </aside>
    </div>
  );
}
