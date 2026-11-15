"use client";

// Top bar: Dashboard and one tab per course; the active tab is highlighted.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { COURSE_TABS } from "@/lib/courses";
import { theme } from "@/lib/ui";

export function NavBar() {
  const pathname = usePathname();
  const tabs = [
    { href: "/dashboard", label: "Dashboard", active: "bg-slate-900 text-white dark:bg-white dark:text-slate-900" },
    // Each course tab lights up in that course's own color.
    ...COURSE_TABS.map((c) => ({ href: `/courses/${c.id}`, label: c.name, active: theme(c.id).soft })),
  ];
  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-1 gap-y-2 px-4 py-2">
        <Link href="/" className="mr-4 flex items-center gap-2 font-bold">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-900 font-mono text-sm text-white dark:bg-white dark:text-slate-900">
            x²
          </span>
          Algebra Tutor
        </Link>
        {tabs.map((t) => {
          const active = pathname === t.href || pathname.startsWith(t.href + "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
                active ? t.active : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
              }`}
            >
              {t.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
