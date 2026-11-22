import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { slugFor } from "../../lib/slug";

import { getAllExams } from "../../lib/api";
import { safeUrl } from "../../lib/safeUrl";
import { getPrerenderData } from "../../lib/prerender-data";
import type { ExamNotification } from "../../types";

function closedExams(all: ExamNotification[]): ExamNotification[] {
  const today = new Date().toISOString().slice(0, 10);
  return all
    .filter((e) =>
      e.window_state ? e.window_state === "closed" : !!e.application_deadline && e.application_deadline < today,
    )
    .sort((a, b) => (b.application_deadline || "").localeCompare(a.application_deadline || ""));
}

/** Archive of notifications whose application window has closed.
 *  Data is honest: real (past) deadlines from the official notices, never extended
 *  just to keep a row visible in the live feed. */
export function ClosedJobsPage() {
  const [exams, setExams] = useState<ExamNotification[] | null>(() => {
    const prerendered = getPrerenderData()?.exams;
    return prerendered ? closedExams(prerendered) : null;
  });
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    getAllExams()
      .then((res) => {
        if (!alive) return;
        setExams(closedExams(res.exams));
      })
      .catch(() => {
        if (alive) setError("Could not load the archive. Please try again.");
      });
    return () => {
      alive = false;
    };
  }, []);

  const byYear = useMemo(() => {
    const groups = new Map<string, ExamNotification[]>();
    for (const exam of exams ?? []) {
      const year = (exam.application_deadline || "unknown").slice(0, 4);
      groups.set(year, [...(groups.get(year) ?? []), exam]);
    }
    return [...groups.entries()];
  }, [exams]);

  if (error) {
    return (
      <div className="mx-auto max-w-[1280px] px-4 py-10 text-center text-sm text-red-700 sm:px-5">
        {error}
      </div>
    );
  }
  if (exams === null) {
    return (
      <div className="mx-auto max-w-[1280px] px-4 py-10 text-center text-sm text-ink/50 sm:px-5">
        Loading archive…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
      <div className="mb-5">
        <h1 className="text-[22px] font-extrabold tracking-tight text-ink">Closed Jobs</h1>
        <p className="mt-1 text-[13px] text-ink/60">
          {exams.length} past notifications. Application windows have ended — listed for reference and official
          source links only.
        </p>
      </div>

      {byYear.map(([year, rows]) => (
        <section key={year} className="mb-8">
          <h3 className="mb-3 border-b border-line pb-2 font-mono text-[13px] font-bold tracking-wide text-ink/50">
            {year}
          </h3>
          <ul className="space-y-2">
            {rows.map((exam) => {
              const href = safeUrl(exam.apply_url || exam.official_pdf_url || exam.source_url);
              return (
                <li
                  key={exam.id}
                  className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-line bg-white/60 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="text-[14px] font-semibold leading-snug text-ink">
                      <Link
                        to={`/jobs/${slugFor(exam.title, exam.id)}`}
                        className="hover:underline hover:underline-offset-2"
                      >
                        {exam.title}
                      </Link>
                    </p>
                    <p className="mt-0.5 text-[12px] text-ink/55">
                      {exam.organizing_body} · Closed {exam.application_deadline}
                    </p>
                  </div>
                  {href && (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 rounded border border-ink px-3 py-1.5 text-[12px] font-bold text-ink hover:bg-ink hover:text-white"
                    >
                      Official notice
                    </a>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
