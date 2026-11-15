"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MasteryBar, StateChip, skillState } from "@/components/Mastery";
import { api, type MasteryReport, type SkillMastery } from "@/lib/api";
import { useUserId } from "@/lib/user";

/** Group skills by prerequisite depth: 0 = no prerequisites, otherwise
 *  1 + the deepest prerequisite. Works in one pass because the backend lists
 *  skills in topological order (prerequisites first). */
function byLevel(skills: SkillMastery[]): SkillMastery[][] {
  const depth: Record<string, number> = {};
  const levels: SkillMastery[][] = [];
  for (const s of skills) {
    const d = s.prerequisites.length ? 1 + Math.max(...s.prerequisites.map((p) => depth[p])) : 0;
    depth[s.id] = d;
    (levels[d] ??= []).push(s);
  }
  return levels;
}

export default function Dashboard() {
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [report, setReport] = useState<MasteryReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    if (!userId) return;
    api.mastery(userId).then(setReport, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [userId]);

  if (!userId) return null;
  if (error)
    return (
      <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
        {error}
      </div>
    );
  if (!report)
    return <p className="text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>;

  const names = Object.fromEntries(report.skills.map((s) => [s.id, s.name]));
  const mastered = report.skills.filter((s) => s.mastered).length;
  const attempts = report.skills.reduce((n, s) => n + s.attempts, 0);
  const correct = report.skills.reduce((n, s) => n + s.correct, 0);
  const pct = (x: number) => `${Math.round(x * 100)}%`;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Mastery dashboard</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {userId} · a skill is mastered at {pct(report.threshold)} predicted chance of answering correctly
          </p>
        </div>
        <Link href="/practice" className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">
          Practice {names[report.recommended]}
        </Link>
      </div>

      <dl className="mt-6 grid grid-cols-3 gap-3">
        {[
          ["Skills mastered", `${mastered} / ${report.skills.length}`],
          ["Problems tried", String(attempts)],
          ["First-try accuracy", attempts ? pct(correct / attempts) : "—"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
            <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
            <dd className="mt-1 text-xl font-semibold tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-8 space-y-6">
        {byLevel(report.skills).map((level, i) => (
          <section key={i}>
            <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Level {i + 1}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {level.map((s) => (
                <div
                  key={s.id}
                  className={`rounded-lg border bg-white p-4 dark:bg-slate-900 ${
                    s.id === report.recommended
                      ? "border-sky-500 ring-2 ring-sky-500/30"
                      : "border-slate-200 dark:border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-sm font-medium">{s.name}</h3>
                    <StateChip state={skillState(s)} />
                  </div>
                  <p className="mt-2 text-2xl font-semibold tabular-nums">{pct(s.mastery)}</p>
                  <div className="mt-2">
                    <MasteryBar skill={s} threshold={report.threshold} />
                  </div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    {s.attempts
                      ? `${s.correct} of ${s.attempts} right on first try`
                      : attempts
                        ? "Not practiced yet · estimated from your other answers"
                        : "Not practiced yet"}
                  </p>
                  {s.prerequisites.length > 0 && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Needs: {s.prerequisites.map((p) => names[p]).join(", ")}
                    </p>
                  )}
                  {s.id === report.recommended && (
                    <p className="mt-2 text-xs font-medium text-sky-700 dark:text-sky-300">Recommended next</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
