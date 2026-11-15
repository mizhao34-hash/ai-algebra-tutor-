"use client";

// The chat panel (a drawer on the right, full screen on phones), the floating
// "Ask tutor" button, and the "Ask about this" button for highlighted text.
import { useEffect, useRef, useState } from "react";
import { COURSE_TABS } from "@/lib/courses";
import { pretty } from "@/lib/math";
import { useTutor } from "./TutorProvider";
import { WalkthroughPlayer } from "./WalkthroughPlayer";

const SparkleIcon = ({ className = "h-4 w-4" }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
    <path d="M12 2l1.8 5.4L19 9l-5.2 1.6L12 16l-1.8-5.4L5 9l5.2-1.6L12 2zm7 11l.9 2.6 2.6.9-2.6.9L19 20l-.9-2.6-2.6-.9 2.6-.9L19 13zM5 14l.7 2 2 .7-2 .7L5 19.5l-.7-2-2-.7 2-.7L5 14z" />
  </svg>
);

/** Turn `code` in tutor messages into math-styled spans; everything else is plain text. */
function MessageText({ text }: { text: string }) {
  return (
    <>
      {text.split(/(`[^`]+`)/g).map((part, i) =>
        part.startsWith("`") ? (
          <code key={i} className="rounded bg-violet-100 px-1 font-mono text-[13px] dark:bg-violet-900/60">
            {pretty(part.slice(1, -1))}
          </code>
        ) : (
          <span key={i}>{pretty(part)}</span>
        ),
      )}
    </>
  );
}

export function TutorPanel() {
  const { enabled, open, setOpen, busy, entries, page, ask, reset } = useTutor();
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries, busy, open]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  if (!enabled) return null;

  const courseName = COURSE_TABS.find((c) => c.id === page.course)?.name;
  const where = page.problemId ? "Your current problem" : courseName ?? "Algebra";

  function send(e?: React.FormEvent) {
    e?.preventDefault();
    const q = draft.trim();
    if (!q || busy) return;
    setDraft("");
    ask(q);
  }

  const suggestions = page.problemId
    ? ["I'm stuck. What should I do first?", "Can you show me a similar example?"]
    : page.course
      ? ["What should I learn first here?", "Show me an example step by step"]
      : ["What can you help me with?"];

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-5 right-5 z-40 inline-flex items-center gap-2 rounded-full bg-violet-600 px-5 py-3 font-semibold text-white shadow-lg shadow-violet-600/30 transition hover:bg-violet-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-600"
        >
          <SparkleIcon /> Ask the AI tutor
        </button>
      )}

      {open && (
        <aside
          aria-label="AI tutor"
          className="fixed inset-0 z-50 flex flex-col bg-white shadow-2xl sm:inset-y-0 sm:left-auto sm:right-0 sm:w-[26rem] sm:border-l sm:border-slate-200 dark:bg-slate-900 sm:dark:border-slate-800"
        >
          <header className="flex items-center gap-3 border-b border-slate-200 bg-violet-600 px-4 py-3 text-white dark:border-slate-800">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20">
              <SparkleIcon className="h-5 w-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-bold leading-tight">AI Tutor</p>
              <p className="truncate text-xs text-violet-100">Helping with: {where}</p>
            </div>
            {entries.length > 0 && (
              <button onClick={reset} className="rounded-md px-2 py-1 text-xs font-semibold text-violet-100 hover:bg-white/15">
                New chat
              </button>
            )}
            <button onClick={() => setOpen(false)} aria-label="Close tutor" className="rounded-md p-1.5 hover:bg-white/15">
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
              </svg>
            </button>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-4 dark:bg-slate-950">
            {entries.length === 0 && (
              <div className="rounded-xl bg-white p-4 text-sm shadow-sm dark:bg-slate-900">
                <p className="font-semibold">Hi! I&apos;m your algebra tutor.</p>
                <p className="mt-1 text-slate-600 dark:text-slate-300">
                  Ask me anything, highlight any text on the page and click <b>Ask about this</b>, or use{" "}
                  <b>Explain this unit</b> in a lesson. I show worked examples step by step, and every step is
                  checked by a math engine.
                </p>
                {page.problemId && (
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    I won&apos;t give you the answer to the problem you&apos;re working on, but I&apos;ll help you get there.
                  </p>
                )}
              </div>
            )}

            {entries.map((e, i) =>
              e.role === "user" ? (
                <div key={i} className="ml-10 rounded-2xl rounded-br-md bg-violet-600 px-3.5 py-2 text-sm text-white">
                  {e.content}
                </div>
              ) : (
                <div key={i} className="mr-4">
                  <div
                    className={`rounded-2xl rounded-bl-md px-3.5 py-2.5 text-sm leading-relaxed shadow-sm ${
                      e.error
                        ? "border border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100"
                        : "bg-white text-slate-800 dark:bg-slate-900 dark:text-slate-100"
                    }`}
                  >
                    <MessageText text={e.content} />
                  </div>
                  {e.reply?.walkthrough && <WalkthroughPlayer walkthrough={e.reply.walkthrough} />}
                </div>
              ),
            )}

            {busy && (
              <div className="mr-4 inline-flex items-center gap-2 rounded-2xl bg-white px-3.5 py-2.5 text-sm text-slate-500 shadow-sm dark:bg-slate-900">
                <span className="inline-flex gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500 [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500 [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-500" />
                </span>
                Thinking and checking the math…
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-slate-200 p-3 dark:border-slate-800">
            {entries.length === 0 && (
              <div className="mb-2 flex flex-wrap gap-1.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => ask(s)}
                    disabled={busy}
                    className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-800 hover:bg-violet-100 disabled:opacity-50 dark:border-violet-800 dark:bg-violet-950 dark:text-violet-200"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <form onSubmit={send} className="flex items-end gap-2">
              <textarea
                ref={inputRef}
                value={draft}
                onChange={(e) => setDraft(e.target.value.slice(0, 500))}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) send(e);
                }}
                rows={2}
                placeholder="Ask a question… (Enter to send)"
                aria-label="Message the AI tutor"
                className="flex-1 resize-none rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus:border-violet-500 focus:outline-none dark:border-slate-700 dark:bg-slate-950"
              />
              <button
                type="submit"
                disabled={busy || !draft.trim()}
                className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        </aside>
      )}

      <SelectionAsk />
    </>
  );
}

/** When the student highlights text on the page, offer to ask the tutor about it. */
function SelectionAsk() {
  const { enabled, ask } = useTutor();
  const [sel, setSel] = useState<{ text: string; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!enabled) return;
    function update() {
      const s = window.getSelection();
      const text = s?.toString().trim() ?? "";
      if (!s || s.rangeCount === 0 || text.length < 2 || text.length > 300) return setSel(null);
      const node = s.anchorNode instanceof Element ? s.anchorNode : s.anchorNode?.parentElement;
      // Only text on the page itself, not inside the tutor panel or form fields.
      if (!node?.closest("main") || node.closest("aside[aria-label='AI tutor'], input, textarea")) return setSel(null);
      const rect = s.getRangeAt(0).getBoundingClientRect();
      setSel({ text, x: Math.min(rect.left, window.innerWidth - 190), y: rect.bottom + 8 });
    }
    const clear = () => setSel(null);
    document.addEventListener("mouseup", update);
    document.addEventListener("keyup", update);
    window.addEventListener("scroll", clear, true);
    return () => {
      document.removeEventListener("mouseup", update);
      document.removeEventListener("keyup", update);
      window.removeEventListener("scroll", clear, true);
    };
  }, [enabled]);

  if (!sel) return null;
  return (
    <button
      // preventDefault on mousedown keeps the selection from being cleared before the click.
      onMouseDown={(e) => e.preventDefault()}
      onClick={() => {
        ask(`Can you explain this: “${sel.text}”`, { mode: "selection", selection: sel.text });
        window.getSelection()?.removeAllRanges();
        setSel(null);
      }}
      style={{ left: Math.max(8, sel.x), top: sel.y }}
      className="tutor-fade-up fixed z-50 inline-flex items-center gap-1.5 rounded-full bg-violet-600 px-3.5 py-1.5 text-sm font-semibold text-white shadow-lg hover:bg-violet-700"
    >
      <SparkleIcon /> Ask about this
    </button>
  );
}
