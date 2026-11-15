"use client";

// Lesson tab: units as dropdowns (in teaching order). Each topic is split into
// clearly separated blocks: the idea, the steps, a worked example on a
// chalkboard, and a common mistake, plus practice / ask-the-tutor actions.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { BlockTitle, ProgressRing } from "@/components/Decor";
import { ArrowRightIcon, CheckIcon, ChevronDownIcon, LightbulbIcon, PencilIcon, WarningIcon } from "@/components/Icons";
import { useTutor } from "@/components/tutor/TutorProvider";
import { api, type Course, type MasteryReport } from "@/lib/api";
import { pretty } from "@/lib/math";
import { btn, card, theme } from "@/lib/ui";
import { useUserId } from "@/lib/user";

const ListIcon = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
    <path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" strokeLinecap="round" />
  </svg>
);
const BoardIcon = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
    <rect x="3" y="4" width="18" height="12" rx="2" />
    <path d="M8 20h8M12 16v4" strokeLinecap="round" />
  </svg>
);

export default function Lessons() {
  const { courseId } = useParams<{ courseId: string }>();
  const t = theme(courseId);
  const [userId] = useUserId();
  const tutor = useTutor();
  const [course, setCourse] = useState<Course | null>(null);
  const [report, setReport] = useState<MasteryReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.course(courseId).then(setCourse, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  useEffect(() => {
    if (userId) api.mastery(userId, courseId).then(setReport, () => {});
  }, [userId, courseId]);

  if (error) return <p className="text-sm text-red-700 dark:text-red-300">{error}</p>;
  if (!course)
    return <p className="text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>;

  const mastered = new Set(report?.skills.filter((s) => s.mastered).map((s) => s.id));
  // The first unit that isn't fully mastered starts open; the rest start closed.
  const openUnit = course.units.find((u) => !u.skills.every((s) => mastered.has(s.id)))?.id ?? course.units[0].id;

  let topic = 0; // topics are numbered across units
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight">Lessons</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-300">
          Open a unit to read its topics. Highlight any text to ask the AI tutor about it.
        </p>
      </div>

      {course.units.map((unit, u) => {
        const done = unit.skills.filter((s) => mastered.has(s.id)).length;
        const complete = done === unit.skills.length;
        return (
          <details key={unit.id} open={unit.id === openUnit} className={`group ${card} overflow-hidden`}>
            <summary className="flex cursor-pointer list-none items-center gap-4 p-5 transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40">
              <span
                className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg font-extrabold text-white shadow-md ${
                  complete ? "bg-gradient-to-br from-emerald-400 to-emerald-600" : t.gradient
                }`}
              >
                {complete ? <CheckIcon className="h-6 w-6" /> : u + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className={`block text-xs font-bold uppercase tracking-wider ${t.text}`}>
                  Unit {u + 1} · {unit.skills.length} {unit.skills.length === 1 ? "topic" : "topics"}
                </span>
                <span className="block text-xl font-extrabold tracking-tight">{unit.name}</span>
                <span className="mt-0.5 block truncate text-sm text-slate-500 dark:text-slate-400">
                  {unit.skills.map((s) => s.name).join(" · ")}
                </span>
              </span>
              {report && (
                <ProgressRing
                  value={done / unit.skills.length}
                  size={48}
                  stroke={5}
                  label={`${done}/${unit.skills.length}`}
                  className={complete ? "text-emerald-500" : t.text}
                  track="stroke-slate-200 dark:stroke-slate-700"
                />
              )}
              <ChevronDownIcon className="h-5 w-5 shrink-0 text-slate-400 transition-transform group-open:rotate-180" />
            </summary>

            <div className="space-y-6 border-t border-slate-200 bg-slate-50/60 p-4 sm:p-6 dark:border-slate-800 dark:bg-slate-950/40">
              {unit.skills.map((skill) => {
                const c = skill.concept;
                topic += 1;
                if (!c) return null;
                return (
                  <article key={skill.id} id={skill.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-slate-800 dark:bg-slate-900">
                    <header className="flex flex-wrap items-center gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
                      <span className={`flex h-9 w-9 items-center justify-center rounded-xl text-sm font-extrabold ${t.icon}`}>{topic}</span>
                      <h3 className="text-xl font-extrabold tracking-tight">{skill.name}</h3>
                      {mastered.has(skill.id) && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-bold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200">
                          <CheckIcon className="h-3 w-3" /> Mastered
                        </span>
                      )}
                    </header>

                    <div className="mt-5 grid gap-5 lg:grid-cols-2">
                      <div className="space-y-5">
                        <section className={`rounded-xl p-4 ${t.soft}`}>
                          <BlockTitle icon={<LightbulbIcon className="h-4 w-4" />} title="The idea" tone="bg-white/70 dark:bg-white/10" />
                          <p className="mt-2 leading-relaxed">{pretty(c.summary)}</p>
                        </section>
                        <section>
                          <BlockTitle icon={<ListIcon />} title="Steps" tone={t.icon} />
                          <ol className="mt-3 space-y-2.5">
                            {c.steps.map((step, i) => (
                              <li key={i} className="flex gap-3 text-sm leading-relaxed">
                                <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white ${t.gradient}`}>
                                  {i + 1}
                                </span>
                                <span>{pretty(step)}</span>
                              </li>
                            ))}
                          </ol>
                        </section>
                      </div>

                      <section className="chalkboard rounded-xl p-4 text-white shadow-inner">
                        <BlockTitle icon={<BoardIcon />} title="Worked example" tone="bg-white/15 text-white" />
                        <ol className="mt-3 space-y-2 font-mono text-[15px]">
                          {c.example.map((line, i) => {
                            const last = i === c.example.length - 1;
                            return (
                              <li key={i} className="flex items-baseline gap-2">
                                <span className="w-4 shrink-0 text-white/40">{i === 0 ? "" : "→"}</span>
                                <span className={last ? "rounded-md bg-white/15 px-2 py-0.5 font-bold text-amber-300" : "text-white/90"}>
                                  {pretty(line)}
                                </span>
                              </li>
                            );
                          })}
                        </ol>
                      </section>
                    </div>

                    <section className="mt-5 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-100">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-amber-200/70 dark:bg-amber-800/60">
                        <WarningIcon className="h-4 w-4" />
                      </span>
                      <p className="leading-relaxed">
                        <span className="font-bold">Watch out: </span>
                        {pretty(c.mistake)}
                      </p>
                    </section>

                    <footer className="mt-5 flex flex-wrap gap-2">
                      <Link href={`/courses/${courseId}/practice?skill=${skill.id}`} className={btn.secondary}>
                        <PencilIcon /> Practice this topic
                      </Link>
                      <button
                        onClick={() => tutor.ask(`Can you explain "${skill.name}" with an example?`, { unit: unit.id })}
                        disabled={tutor.busy}
                        className={btn.hint}
                      >
                        ✦ Ask the tutor about this
                      </button>
                    </footer>
                  </article>
                );
              })}

              <div className={`relative overflow-hidden rounded-2xl p-5 text-white shadow-md ${t.gradient}`}>
                <div className="relative flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-lg font-extrabold">Finished reading “{unit.name}”?</p>
                    <p className="text-sm text-white/85">Get a walkthrough from the AI tutor, or practice all topics in this unit mixed together.</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => tutor.ask(`Explain this unit: ${unit.name}`, { mode: "explain_unit", unit: unit.id })}
                      disabled={tutor.busy}
                      className="inline-flex items-center gap-2 rounded-lg bg-white/20 px-4 py-2 text-sm font-semibold backdrop-blur hover:bg-white/30 disabled:opacity-50"
                    >
                      ✦ Explain this unit
                    </button>
                    <Link
                      href={`/courses/${courseId}/practice?unit=${unit.id}`}
                      className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-900 shadow hover:bg-slate-100"
                    >
                      Practice this unit <ArrowRightIcon />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </details>
        );
      })}
    </div>
  );
}
