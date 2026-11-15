"use client";

// Shared frame for a course: a colored header, and Lesson / Practice tabs on
// the left (on top on phones). Each course has its own accent color (lib/ui.ts).
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BookIcon, PencilIcon } from "@/components/Icons";
import { useTutorPage } from "@/components/tutor/TutorProvider";
import { api, type Course } from "@/lib/api";
import { theme } from "@/lib/ui";
import { useUserId } from "@/lib/user";

export default function CourseLayout({ children }: { children: React.ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>();
  const pathname = usePathname();
  const router = useRouter();
  const [userId, loaded] = useUserId();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState<string | null>(null);
  const t = theme(courseId);
  useTutorPage({ course: courseId }); // the AI tutor knows which course you're in

  useEffect(() => {
    if (loaded && !userId) router.replace("/");
  }, [loaded, userId, router]);

  useEffect(() => {
    api.course(courseId).then(setCourse, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, [courseId]);

  // Opening a course joins it (idempotent), so it shows up on the Dashboard.
  useEffect(() => {
    if (userId) api.join(userId, courseId).catch(() => {});
  }, [userId, courseId]);

  if (!userId) return null;

  const tabs = [
    { href: `/courses/${courseId}`, label: "Lesson", Icon: BookIcon },
    { href: `/courses/${courseId}/practice`, label: "Practice", Icon: PencilIcon },
  ];

  return (
    <div>
      <div className={`mb-6 rounded-xl px-5 py-4 ${t.soft}`}>
        <p className="text-xs font-semibold uppercase tracking-wider opacity-70">{course?.grades ?? "Course"}</p>
        <h1 className="mt-0.5 text-2xl font-bold">{course?.name ?? (error ? "Course" : "Loading…")}</h1>
        {course && <p className="mt-1 text-sm opacity-80">{course.description}</p>}
        {error && <p className="mt-2 text-sm text-red-700 dark:text-red-300">{error}</p>}
      </div>

      <div className="grid gap-6 md:grid-cols-[11rem_1fr]">
        <nav aria-label="Course sections" className="flex gap-2 md:flex-col">
          {tabs.map(({ href, label, Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2 rounded-lg border-l-4 px-3 py-2.5 text-sm font-semibold ${
                  active
                    ? `${t.border} ${t.soft}`
                    : "border-transparent text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}
