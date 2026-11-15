"use client";

// Dashboard: a welcome banner with overall progress, then each joined course
// (gradient header, stats, unit progress, topic breakdown), then courses not started.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FloatingSymbols, ProgressRing } from "@/components/Decor";
import { ArrowRightIcon, BookIcon, CheckIcon } from "@/components/Icons";
import { MasteryBar, StateChip, skillState } from "@/components/Mastery";
import { api, type Course, type JoinedCourse, type SkillMastery } from "@/lib/api";
import { card, theme } from "@/lib/ui";
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
  const totals = courses.reduce(
    (a, c) => ({
      mastered: a.mastered + c.summary.mastered,
      skills: a.skills + c.summary.skills,
      attempts: a.attempts + c.summary.attempts,
      correct: a.correct + c.summary.correct,
    }),
    { mastered: 0, skills: 0, attempts: 0, correct: 0 },
  );

  return (
    <div className="space-y-10">
      {/* Welcome banner */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-900 to-violet-800 px-6 py-8 text-white shadow-xl sm:px-8">
        <FloatingSymbols symbols={["x²", "√", "≤", "π", "±", "∑"]} />
        <div className="relative">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-indigo-200">Your learning dashboard</p>
              <h1 className="mt-1 text-3xl font-extrabold tracking-tight sm:text-4xl">Welcome back, {userId} 👋</h1>
              <p className="mt-2 max-w-xl text-indigo-100/90">
                A topic counts as mastered when you have a 70% predicted chance of getting it right.
              </p>
            </div>
            <button onClick={switchUser} className="rounded-lg px-3 py-1.5 text-sm font-semibold text-indigo-100 hover:bg-white/10">
              Switch user
            </button>
          </div>
          <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Courses", String(courses.length)],
              ["Topics mastered", `${totals.mastered} / ${totals.skills || 0}`],
              ["Problems tried", String(totals.attempts)],
              ["First-try accuracy", totals.attempts ? pct(totals.correct / totals.attempts) : "—"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur">
                <dt className="text-xs font-medium text-indigo-200">{label}</dt>
                <dd className="mt-1 text-2xl font-extrabold tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {courses.length > 0 && (
        <section className="space-y-6">
          <h2 className="text-2xl font-extrabold tracking-tight">Your courses</h2>
          {courses.map((c) => {
            const t = theme(c.id);
            const s = c.summary;
            const names = Object.fromEntries(c.mastery.skills.map((k) => [k.id, k.name]));
            return (
              <article key={c.id} className={`${card} overflow-hidden`}>
                <header className={`relative overflow-hidden px-5 py-5 text-white ${t.gradient}`}>
                  <FloatingSymbols symbols={t.symbols.slice(0, 3)} />
                  <div className="relative flex flex-wrap items-center gap-4">
                    <ProgressRing value={s.mastered / s.skills} size={60} label={`${s.mastered}/${s.skills}`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold uppercase tracking-wider text-white/80">{c.grades}</p>
                      <h3 className="text-2xl font-extrabold tracking-tight">{c.name}</h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link href={`/courses/${c.id}`} className="inline-flex items-center gap-2 rounded-lg bg-white/20 px-4 py-2 text-sm font-semibold backdrop-blur hover:bg-white/30">
                        <BookIcon /> Lesson
                      </Link>
                      <Link href={`/courses/${c.id}/practice`} className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-900 shadow hover:bg-slate-100">
                        Continue: {names[c.mastery.recommended]} <ArrowRightIcon />
                      </Link>
                    </div>
                  </div>
                </header>

                <div className="grid gap-6 p-5 lg:grid-cols-[14rem_1fr]">
                  <dl className="grid grid-cols-3 gap-3 lg:grid-cols-1">
                    {[
                      ["Topics mastered", `${s.mastered} / ${s.skills}`],
                      ["Problems tried", String(s.attempts)],
                      ["First-try accuracy", s.attempts ? pct(s.correct / s.attempts) : "—"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-950">
                        <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
                        <dd className="mt-0.5 text-xl font-extrabold tabular-nums">{value}</dd>
                      </div>
                    ))}
                  </dl>

                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Units</h4>
                    <ul className="mt-2 space-y-2">
                      {c.units_progress.map((u, i) => {
                        const complete = u.mastered === u.skills;
                        return (
                          <li key={u.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-slate-200 px-3 py-2.5 dark:border-slate-800">
                            <span
                              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold ${
                                complete ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-200" : t.icon
                              }`}
                            >
                              {complete ? <CheckIcon className="h-4 w-4" /> : i + 1}
                            </span>
                            <span className="min-w-[10rem] flex-1 text-sm font-semibold">{u.name}</span>
                            <span className="w-24 text-xs text-slate-500 tabular-nums dark:text-slate-400">
                              {u.mastered}/{u.skills} mastered
                            </span>
                            <span
                              className="h-2 w-28 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                              role="progressbar"
                              aria-label={`${u.name} average mastery`}
                              aria-valuenow={Math.round(u.average_mastery * 100)}
                              aria-valuemin={0}
                              aria-valuemax={100}
                            >
                              <span className={`block h-full rounded-full ${complete ? "bg-emerald-500" : t.bar}`} style={{ width: pct(u.average_mastery) }} />
                            </span>
                            <Link href={`/courses/${c.id}/practice?unit=${u.id}`} className={`inline-flex items-center gap-1 text-sm font-semibold ${t.text}`}>
                              Practice <ArrowRightIcon className="h-3.5 w-3.5" />
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>

                <details className="border-t border-slate-200 dark:border-slate-800">
                  <summary className="cursor-pointer px-5 py-3 text-sm font-bold hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    Topic breakdown
                  </summary>
                  <div className="space-y-5 bg-slate-50/60 px-5 pb-5 pt-2 dark:bg-slate-950/40">
                    {byLevel(c.mastery.skills).map((level, i) => (
                      <div key={i}>
                        <h5 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Level {i + 1}</h5>
                        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                          {level.map((k) => (
                            <div
                              key={k.id}
                              className={`rounded-xl border bg-white p-3 dark:bg-slate-900 ${
                                k.id === c.mastery.recommended ? `${t.border} ring-2 ${t.ring}` : "border-slate-200 dark:border-slate-800"
                              }`}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <h6 className="text-sm font-bold">{k.name}</h6>
                                <StateChip state={skillState(k)} />
                              </div>
                              <p className="mt-1 text-xl font-extrabold tabular-nums">{pct(k.mastery)}</p>
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
                                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Needs: {k.prerequisites.map((p) => names[p]).join(", ")}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              </article>
            );
          })}
        </section>
      )}

      {notStarted.length > 0 && (
        <section>
          <h2 className="text-2xl font-extrabold tracking-tight">{courses.length ? "Explore more courses" : "Pick a course to start"}</h2>
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {notStarted.map((c) => {
              const t = theme(c.id);
              return (
                <Link key={c.id} href={`/courses/${c.id}`} className={`${card} group flex flex-col overflow-hidden transition hover:-translate-y-1 hover:shadow-lg`}>
                  <div className={`relative h-28 overflow-hidden ${t.gradient}`}>
                    <FloatingSymbols symbols={t.symbols} />
                    <span className="absolute bottom-3 left-4 rounded-full bg-white/25 px-3 py-1 text-xs font-bold text-white backdrop-blur">{c.grades}</span>
                  </div>
                  <div className="flex flex-1 flex-col p-5">
                    <h3 className="text-xl font-extrabold tracking-tight">{c.name}</h3>
                    <p className="mt-2 flex-1 text-sm text-slate-600 dark:text-slate-300">{c.description}</p>
                    <p className="mt-3 text-xs font-medium text-slate-500 dark:text-slate-400">
                      {c.units.length} units · {c.units.reduce((n, u) => n + u.skills.length, 0)} topics
                    </p>
                    <span className={`mt-4 inline-flex items-center gap-1 text-sm font-bold ${t.text}`}>
                      Start course <ArrowRightIcon className="transition group-hover:translate-x-1" />
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
