import { useState } from "react";
import type { FeedAdmitCard } from "../../lib/exams";
import { formatDateIN } from "../../lib/exams";

/** Admit card card — official download link only, never a third-party mirror. */
export function AdmitCardCard({ card }: { card: FeedAdmitCard }) {
  const [open, setOpen] = useState(false);
  const isPdf = (card.admitUrl ?? "").toLowerCase().includes(".pdf");
  const examDay = card.examDateISO ? `exam in ${card.examDays} day${card.examDays === 1 ? "" : "s"}` : null;

  return (
    <article className="rounded-lg border border-line bg-[#fbfaf7]">
      <div className="px-5 pt-4">
        <div className="flex flex-wrap items-center gap-2">
          {card.isNew && (
            <span className="rounded bg-govgreen px-1.5 py-0.5 text-[11px] font-bold text-white">
              NEW
            </span>
          )}
          <span className="text-[12.5px] text-ink/55">{card.department}</span>
          {card.lastChecked && (
            <span className="ml-auto text-[11.5px] text-ink/45">
              Last checked {formatDateIN(card.lastChecked)}
            </span>
          )}
        </div>

        <h3 className="font-ui mt-1.5 text-[18px] font-bold leading-snug text-ink">
          {card.title}
        </h3>
        {card.examName && (
          <p className="mt-1 text-[14px] text-ink/65">{card.examName}</p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-5 pb-4 pt-3">
        <p className="min-w-[130px] flex-1 text-[14px] font-semibold text-ink/70">
          {examDay ? (
            <>
              Exam date: <span className="tabular-nums">{formatDateIN(card.examDateISO)}</span>
              <span className="text-ink/45"> · {examDay}</span>
            </>
          ) : (
            "Exam date: check the notice"
          )}
        </p>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setOpen((v) => !v)}
            className="h-10 rounded-lg border border-line bg-paper px-3 text-[13px] font-semibold text-ink/75 transition-colors hover:border-line-strong hover:text-ink"
            aria-expanded={open}
          >
            Details
          </button>
          {card.admitUrl ? (
            <a
              href={card.admitUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-10 items-center gap-1.5 rounded-lg bg-ink px-4 text-[13.5px] font-bold text-white transition-colors hover:bg-saffron"
            >
              {isPdf ? "Download Admit Card" : "Open Official Notice"}
              <span aria-hidden="true">↗</span>
            </a>
          ) : (
            <span
              className="inline-flex h-10 cursor-not-allowed items-center rounded-lg border border-line px-4 text-[13px] font-semibold text-ink/45"
              title="Official download link is not on file yet"
            >
              Link pending
            </span>
          )}
        </div>
      </div>

      {open && (
        <div className="border-t border-line px-5 py-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">
                Exam date
              </p>
              <p className="mt-0.5 text-[13.5px] leading-snug text-ink">
                {formatDateIN(card.examDateISO)}
              </p>
            </div>
            <div>
              <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">
                Released
              </p>
              <p className="mt-0.5 text-[13.5px] leading-snug text-ink">
                {formatDateIN(card.notificationISO)}
              </p>
            </div>
          </div>
          <p className="mt-3 text-[12px] leading-relaxed text-ink/55">
            The link opens the board's official notice{isPdf ? " (PDF)" : ""}. If it does not load,
            the board's website is the source of truth — availability can change without notice.
          </p>
          {card.sourceUrl && (
            <a
              href={card.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-block text-[13px] font-semibold text-saffron underline-offset-2 hover:underline"
            >
              Source: official notice ↗
            </a>
          )}
        </div>
      )}
    </article>
  );
}
