"use client";

// Dashboard: the courses this user has joined and their mastery (per unit, and
// per skill grouped by prerequisite level), plus courses not started yet.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRightIcon, BookIcon, CheckIcon } from "@/components/Icons";
import { MasteryBar, StateChip, skillState } from "@/components/Mastery";
import { api, type Course, type JoinedCourse, type SkillMastery } from "@/lib/api";
import { btn, card, theme } from "@/lib/ui";
import { saveUserId, useUserId } from "@/lib/user";

/** Group skills by prerequisite depth: 0 = no prerequisites (inside this course),
 *  otherwise 1 + the deepest prerequisite. Works in one pass because the
 *  backend lists skills in topological order (prerequisites first). */
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

const pct = (x: number) => `${Math.round(x * 100)}%`;

export default function Dashboard() {
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [courses, setCourses] = useState<JoinedCourse[] | null>(null);
  const [catalog, setCatalog] = useState<Course[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    if (!userId) return;
    api.myCourses(userId).then(setCourses, (e) => setError(e instanceof Error ? e.message : String(e)));
    api.courses().then(setCatalog, () => {});
  }, [userId]);

  function switchUser() {
    saveUserId(null);
    router.push("/");
  }

  if (!userId) return null;
  if (error)
    return (
      <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
        {error}
      </div>
    );
  if (!courses)
    return <p className="text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>;

  const notStarted = catalog.filter((c) => !courses.some((j) => j.id === c.id));

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Welcome back, {userId}</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            A topic counts as mastered when you have a 70% predicted chance of answering it correctly.
          </p>
        </div>
        <button onClick={switchUser} className={btn.subtle}>
          Switch user
        </button>
      </div>

      {courses.length === 0 && (
        <p className="mt-6 text-slate-600 dark:text-slate-300">You haven&apos;t started a course yet. Pick one below.</p>
      )}

      <div className="mt-6 space-y-6">
        {courses.map((c) => {
          const t = theme(c.id);
          const s = c.summary;
          const names = Object.fromEntries(c.mastery.skills.map((k) => [k.id, k.name]));
          return (
            <section key={c.id} className={`${card} overflow-hidden`}>
              <div className={`h-1.5 ${t.bar}`} aria-hidden />
              <div className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className={`text-xs font-semibold uppercase tracking-wider ${t.text}`}>{c.grades}</p>
                    <h2 className="text-xl font-bold">{c.name}</h2>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link href={`/courses/${c.id}`} className={btn.secondary}>
                      <BookIcon /> Lesson
                    </Link>
                    <Link href={`/courses/${c.id}/practice`} className={btn.primary(t)}>
                      Continue: {names[c.mastery.recommended]} <ArrowRightIcon />
                    </Link>
                  </div>
                </div>

                <dl className="mt-4 grid grid-cols-3 gap-3">
                  {[
                    ["Topics mastered", `${s.mastered} / ${s.skills}`],
                    ["Problems tried", String(s.attempts)],
                    ["First-try accuracy", s.attempts ? pct(s.correct / s.attempts) : "—"],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-950">
                      <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
                      <dd className="mt-1 text-2xl font-bold tabular-nums">{value}</dd>
                    </div>
                  ))}
                </dl>

                <h3 className="mt-6 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Units</h3>
                <ul className="mt-2 space-y-2">
                  {c.units_progress.map((u) => {
                    const complete = u.mastered === u.skills;
                    return (
                      <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                        <span className="flex min-w-[12rem] flex-1 items-center gap-2 text-sm font-medium">
                          {complete && <CheckIcon className="h-4 w-4 text-emerald-600" />}
                          {u.name}
                        </span>
                        <span className="w-24 text-xs text-slate-500 tabular-nums dark:text-slate-400">
                          {u.mastered}/{u.skills} mastered
                        </span>
                        <span
                          className="h-2 w-32 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                          role="progressbar"
                          aria-label={`${u.name} average mastery`}
                          aria-valuenow={Math.round(u.average_mastery * 100)}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        >
                          <span
                            className={`block h-full rounded-full ${complete ? "bg-emerald-500" : t.bar}`}
                            style={{ width: pct(u.average_mastery) }}
                          />
                        </span>
                        <Link href={`/courses/${c.id}/practice?unit=${u.id}`} className={`${btn.subtle} ${t.text}`}>
                          Practice <ArrowRightIcon className="h-3.5 w-3.5" />
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>

              <details className="border-t border-slate-200 dark:border-slate-800">
                <summary className="cursor-pointer px-5 py-3 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  Topic breakdown
                </summary>
                <div className="space-y-5 px-5 pb-5">
                  {byLevel(c.mastery.skills).map((level, i) => (
                    <div key={i}>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Level {i + 1}</h4>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {level.map((k) => (
                          <div
                            key={k.id}
                            className={`rounded-lg border p-3 ${
                              k.id === c.mastery.recommended ? `${t.border} ring-2 ${t.ring}` : "border-slate-200 dark:border-slate-800"
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <h5 className="text-sm font-semibold">{k.name}</h5>
                              <StateChip state={skillState(k)} />
                            </div>
                            <p className="mt-1 text-xl font-bold tabular-nums">{pct(k.mastery)}</p>
                            <div className="mt-1">
                              <MasteryBar skill={k} threshold={c.mastery.threshold} />
                            </div>
                            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                              {k.attempts
                                ? `${k.correct} of ${k.attempts} right on first try`
                                : k.mastery > 0
                                  ? "Not practiced yet · estimated from your other answers"
                                  : "Not practiced yet"}
                            </p>
                            {k.prerequisites.length > 0 && (
                              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                                Needs: {k.prerequisites.map((p) => names[p]).join(", ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            </section>
          );
        })}
      </div>

      {notStarted.length > 0 && (
        <section className="mt-10">
          <h2 className="text-lg font-bold">{courses.length ? "More courses" : "Courses"}</h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {notStarted.map((c) => {
              const t = theme(c.id);
              return (
                <div key={c.id} className={`${card} flex flex-col overflow-hidden`}>
                  <div className={`h-1.5 ${t.bar}`} aria-hidden />
                  <div className="flex flex-1 flex-col p-5">
                  <p className={`text-xs font-semibold uppercase tracking-wider ${t.text}`}>{c.grades}</p>
                  <h3 className="text-lg font-bold">{c.name}</h3>
                  <p className="mt-2 flex-1 text-sm text-slate-600 dark:text-slate-300">{c.description}</p>
                  <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                    {c.units.length} units · {c.units.reduce((n, u) => n + u.skills.length, 0)} topics
                  </p>
                  <Link href={`/courses/${c.id}`} className={`mt-4 ${btn.primary(t)}`}>
                    Start course <ArrowRightIcon />
                  </Link>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
