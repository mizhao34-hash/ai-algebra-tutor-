"use client";

// Lesson tab: every skill's lesson, grouped by unit in teaching order.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Course } from "@/lib/api";
import { pretty } from "@/lib/math";

export default function Concepts() {
  const { courseId } = useParams<{ courseId: string }>();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.course(courseId).then(setCourse, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  if (error) return <p className="text-sm text-red-700 dark:text-red-300">{error}</p>;
  if (!course)
    return <p className="text-slate-500">Loading… If the server was idle, it can take up to a minute to wake up.</p>;

  let topic = 0; // topics are numbered across units
  return (
    <div className="space-y-10">
      <p className="text-slate-600 dark:text-slate-300">{course.description}</p>
      {course.units.map((unit, u) => (
        <section key={unit.id}>
          <h2 className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Unit {u + 1} · {unit.name}
          </h2>
          <div className="mt-3 space-y-6">
            {unit.skills.map((skill) => {
              const c = skill.concept;
              topic += 1;
              if (!c) return null;
              return (
                <article
                  key={skill.id}
                  id={skill.id}
                  className="rounded-lg border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900"
                >
                  <h3 className="text-lg font-semibold">
                    {topic}. {skill.name}
                  </h3>
                  <p className="mt-2">{c.summary}</p>

                  <h4 className="mt-4 text-sm font-semibold">Steps</h4>
                  <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm">
                    {c.steps.map((step, i) => (
                      <li key={i}>{step}</li>
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
                    {c.mistake}
                  </div>

                  <Link
                    href={`/courses/${courseId}/practice?skill=${skill.id}`}
                    className="mt-4 inline-block rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
                  >
                    Practice this skill
                  </Link>
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
