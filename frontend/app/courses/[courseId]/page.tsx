"use client";

// Lesson tab: units as dropdowns (in teaching order), each with its topics'
// lessons, the student's progress in that unit, and a unit practice button.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRightIcon, CheckIcon, ChevronDownIcon, PencilIcon, WarningIcon } from "@/components/Icons";
import { api, type Course, type MasteryReport } from "@/lib/api";
import { pretty } from "@/lib/math";
import { btn, card, theme } from "@/lib/ui";
import { useUserId } from "@/lib/user";

export default function Lessons() {
  const { courseId } = useParams<{ courseId: string }>();
  const t = theme(courseId);
  const [userId] = useUserId();
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
    <div className="space-y-4">
      {course.units.map((unit, u) => {
        const done = unit.skills.filter((s) => mastered.has(s.id)).length;
        const complete = done === unit.skills.length;
        return (
          <details key={unit.id} open={unit.id === openUnit} className={`group ${card} overflow-hidden`}>
            <summary className="flex cursor-pointer list-none items-center gap-4 p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <span
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                  complete ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200" : t.soft
                }`}
              >
                {complete ? <CheckIcon className="h-5 w-5" /> : u + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Unit {u + 1} · {unit.skills.length} {unit.skills.length === 1 ? "topic" : "topics"}
                </span>
                <span className="block text-lg font-bold">{unit.name}</span>
              </span>
              {report && (
                <span className="hidden text-sm text-slate-600 tabular-nums sm:block dark:text-slate-300">
                  {done}/{unit.skills.length} mastered
                </span>
              )}
              <ChevronDownIcon className="h-5 w-5 shrink-0 text-slate-400 transition-transform group-open:rotate-180" />
            </summary>

            <div className="divide-y divide-slate-200 border-t border-slate-200 dark:divide-slate-800 dark:border-slate-800">
              {unit.skills.map((skill) => {
                const c = skill.concept;
                topic += 1;
                if (!c) return null;
                return (
                  <article key={skill.id} id={skill.id} className="p-5">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-bold">
                        <span className={t.text}>{topic}.</span> {skill.name}
                      </h3>
                      {mastered.has(skill.id) && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200">
                          <CheckIcon className="h-3 w-3" /> Mastered
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-slate-700 dark:text-slate-200">{pretty(c.summary)}</p>

                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Steps</h4>
                        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
                          {c.steps.map((step, i) => (
                            <li key={i}>{pretty(step)}</li>
                          ))}
                        </ol>
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          Worked example
                        </h4>
                        <ol className="mt-2 space-y-1 rounded-lg bg-slate-50 p-3 font-mono text-sm dark:bg-slate-950">
                          {c.example.map((line, i) => (
                            <li key={i} className={i === c.example.length - 1 ? `font-bold ${t.text}` : ""}>
                              <span className="mr-2 inline-block w-4 text-slate-400">{i === 0 ? "" : "→"}</span>
                              {pretty(line)}
                            </li>
                          ))}
                        </ol>
                      </div>
                    </div>

                    <div className="mt-4 flex gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                      <WarningIcon className="mt-0.5 h-4 w-4 shrink-0" />
                      <p>
                        <span className="font-semibold">Common mistake: </span>
                        {pretty(c.mistake)}
                      </p>
                    </div>

                    <Link href={`/courses/${courseId}/practice?skill=${skill.id}`} className={`mt-4 ${btn.secondary}`}>
                      <PencilIcon /> Practice this topic
                    </Link>
                  </article>
                );
              })}
              <div className={`flex flex-wrap items-center justify-between gap-3 p-5 ${t.soft}`}>
                <p className="text-sm font-medium">Ready? Practice every topic in this unit, mixed together.</p>
                <Link href={`/courses/${courseId}/practice?unit=${unit.id}`} className={btn.primary(t)}>
                  Practice this unit <ArrowRightIcon />
                </Link>
              </div>
            </div>
          </details>
        );
      })}
    </div>
  );
}
