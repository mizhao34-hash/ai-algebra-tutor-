"use client";

// The AI tutor follows the student around the site: one conversation, kept
// while they move between pages. Pages tell the tutor where the student is
// (course / unit / current problem) with useTutorPage(), so answers fit the
// page, and so the tutor never gives away the answer to the problem on screen.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, type TutorReply, type TutorRequest } from "@/lib/api";
import { useUserId } from "@/lib/user";

export type PageContext = { course?: string; unit?: string; problemId?: string };

export type ChatEntry =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; reply?: TutorReply; error?: boolean };

type AskOptions = { mode?: TutorRequest["mode"]; selection?: string; unit?: string; course?: string };

type TutorState = {
  enabled: boolean;
  open: boolean;
  setOpen: (open: boolean) => void;
  busy: boolean;
  entries: ChatEntry[];
  page: PageContext;
  setPage: (update: (prev: PageContext) => PageContext) => void;
  ask: (question: string, options?: AskOptions) => void;
  reset: () => void;
};

const TutorCtx = createContext<TutorState | null>(null);

export function useTutor(): TutorState {
  const t = useContext(TutorCtx);
  if (!t) throw new Error("useTutor must be used inside <TutorProvider>");
  return t;
}

/** Register where the student is. Only the given keys are set, and only
 *  those are removed again when the page goes away (pages nest: the course
 *  layout sets `course`, the practice page adds `unit` and `problemId`). */
export function useTutorPage(ctx: PageContext) {
  const { setPage } = useTutor();
  const { course, unit, problemId } = ctx;
  useEffect(() => {
    const part: PageContext = {};
    if (course !== undefined) part.course = course;
    if (unit !== undefined) part.unit = unit;
    if (problemId !== undefined) part.problemId = problemId;
    setPage((prev) => ({ ...prev, ...part }));
    return () =>
      setPage((prev) => {
        const next = { ...prev };
        for (const k of Object.keys(part) as (keyof PageContext)[]) delete next[k];
        return next;
      });
  }, [course, unit, problemId, setPage]);
}

const HISTORY = 10; // recent messages sent along, so follow-up questions make sense

export function TutorProvider({ children }: { children: React.ReactNode }) {
  const [userId] = useUserId();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [page, setPageState] = useState<PageContext>({});
  const entriesRef = useRef(entries);
  entriesRef.current = entries;

  const setPage = useCallback((update: (prev: PageContext) => PageContext) => setPageState(update), []);

  const ask = useCallback(
    async (question: string, options: AskOptions = {}) => {
      if (!userId || busy) return;
      const mode = options.mode ?? "chat";
      setOpen(true);
      // Conversation so far (successful turns only), as plain text for the model.
      const history = entriesRef.current
        .filter((e) => !(e.role === "assistant" && e.error))
        .map((e) => ({ role: e.role, content: e.content }))
        .slice(-HISTORY);
      // For "explain this unit" the server adds the request itself.
      const messages = mode === "explain_unit" ? history : [...history, { role: "user" as const, content: question }];
      setEntries((prev) => [...prev, { role: "user", content: question }]);
      setBusy(true);
      try {
        const reply = await api.tutor(userId, {
          messages,
          mode,
          course: options.course ?? page.course,
          unit: options.unit ?? page.unit,
          problem_id: page.problemId,
          selection: options.selection,
        });
        setEntries((prev) => [...prev, { role: "assistant", content: reply.message, reply }]);
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        // Drop the unanswered question from the history we send next time, but keep it on screen.
        setEntries((prev) => [...prev, { role: "assistant", content: msg, error: true }]);
      } finally {
        setBusy(false);
      }
    },
    [userId, busy, page],
  );

  const reset = useCallback(() => setEntries([]), []);

  return (
    <TutorCtx.Provider value={{ enabled: !!userId, open, setOpen, busy, entries, page, setPage, ask, reset }}>
      {children}
    </TutorCtx.Provider>
  );
}
