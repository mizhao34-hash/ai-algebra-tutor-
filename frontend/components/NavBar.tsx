"use client";

// Top bar: Dashboard and one tab per course; the active tab is highlighted.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { COURSE_TABS } from "@/lib/courses";

export function NavBar() {
  const pathname = usePathname();
  const tabs = [{ href: "/dashboard", label: "Dashboard" }, ...COURSE_TABS.map((c) => ({ href: `/courses/${c.id}`, label: c.name }))];
  return (
    <header className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-1 gap-y-2 px-4 py-2">
        <Link href="/" className="mr-4 font-semibold">
          Algebra Tutor
        </Link>
        {tabs.map((t) => {
          const active = pathname === t.href || pathname.startsWith(t.href + "/");
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={active ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 text-sm ${
                active
                  ? "bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-white"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
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
