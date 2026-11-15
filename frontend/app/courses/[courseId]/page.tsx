"use client";

// Lesson tab: units as dropdowns (in teaching order), each with its topics'
// lessons, the student's progress in that unit, and a unit practice button.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Course, type MasteryReport } from "@/lib/api";
import { pretty } from "@/lib/math";
import { useUserId } from "@/lib/user";

export default function Lessons() {
  const { courseId } = useParams<{ courseId: string }>();
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
      <p className="text-slate-600 dark:text-slate-300">{course.description}</p>
      {course.units.map((unit, u) => {
        const done = unit.skills.filter((s) => mastered.has(s.id)).length;
        return (
          <details
            key={unit.id}
            open={unit.id === openUnit}
            className="group rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
          >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 p-4">
              <span>
                <span className="block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Unit {u + 1}
                </span>
                <span className="text-lg font-semibold">{unit.name}</span>
                <span className="ml-2 text-sm text-slate-500 dark:text-slate-400">
                  {unit.skills.length} {unit.skills.length === 1 ? "topic" : "topics"}
                </span>
              </span>
              <span className="flex items-center gap-3">
                {report && (
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      done === unit.skills.length
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200"
                        : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                    }`}
                  >
                    {done}/{unit.skills.length} mastered
                  </span>
                )}
                <span aria-hidden className="text-slate-400 transition-transform group-open:rotate-180">
                  ▾
                </span>
              </span>
            </summary>

            <div className="space-y-5 border-t border-slate-200 p-4 dark:border-slate-800">
              {unit.skills.map((skill) => {
                const c = skill.concept;
                topic += 1;
                if (!c) return null;
                return (
                  <article key={skill.id} id={skill.id}>
                    <h3 className="text-lg font-semibold">
                      {topic}. {skill.name}
                      {mastered.has(skill.id) && (
                        <span className="ml-2 align-middle text-xs font-medium text-emerald-700 dark:text-emerald-300">
                          ✓ mastered
                        </span>
                      )}
                    </h3>
                    <p className="mt-2">{pretty(c.summary)}</p>

                    <h4 className="mt-4 text-sm font-semibold">Steps</h4>
                    <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm">
                      {c.steps.map((step, i) => (
                        <li key={i}>{pretty(step)}</li>
                      ))}
                    </ol>

                    <h4 className="mt-4 text-sm font-semibold">Worked example</h4>
                    <ol className="mt-1 space-y-1 rounded-md bg-slate-50 p-3 font-mono text-sm dark:bg-slate-950">
                      {c.example.map((line, i) => (
                        <li key={i} className={i === c.example.length - 1 ? "font-semibold" : ""}>
                          <span className="mr-2 inline-block w-4 text-slate-400">{i === 0 ? "" : "→"}</span>
                          {pretty(line)}
                        </li>
                      ))}
                    </ol>

                    <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
                      <span className="font-semibold">Common mistake: </span>
                      {pretty(c.mistake)}
                    </div>

                    <Link
                      href={`/courses/${courseId}/practice?skill=${skill.id}`}
                      className="mt-3 inline-block text-sm font-medium text-sky-700 underline dark:text-sky-300"
                    >
                      Practice this topic
                    </Link>
                  </article>
                );
              })}

              <Link
                href={`/courses/${courseId}/practice?unit=${unit.id}`}
                className="inline-block rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
              >
                Practice this unit
              </Link>
            </div>
          </details>
        );
      })}
    </div>
  );
}
