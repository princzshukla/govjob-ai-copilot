import { useState } from "react";
import type { FeedAdmitCard } from "../../lib/exams";
import { formatDateIN } from "../../lib/exams";
import { safeUrl } from "../../lib/safeUrl";
import { Link } from "react-router-dom";
import { slugFor } from "../../lib/slug";

/** Admit card card — official download link only, never a third-party mirror. */
export function AdmitCardCard({ card }: { card: FeedAdmitCard }) {
  const [open, setOpen] = useState(false);
  const isPdf = card.linkKind === "notice_pdf" || (card.linkKind == null && (card.admitUrl ?? "").toLowerCase().includes(".pdf"));
  const cta =
    card.linkKind === "candidate_portal"
      ? "Open Candidate Login"
      : card.linkKind === "notice_page"
        ? "Open Official Notice"
        : card.linkKind === "notice_pdf" || isPdf
          ? "Download Admit Card"
          : "Open Official Notice";
  const examDay = card.examDateISO ? `exam in ${card.examDays} day${card.examDays === 1 ? "" : "s"}` : null;

  return (
    <article className="rounded-lg border border-line bg-[#fbfaf7]">
      <div className="px-4 pt-3 sm:px-5 sm:pt-4">
        <div className="flex flex-wrap items-center gap-2">
          {card.isNew && (
            <span className="rounded bg-govgreen px-1.5 py-0.5 text-[11px] font-bold text-white">NEW</span>
          )}
          <span className="text-[12.5px] text-ink/55">{card.department}</span>
          {card.noticeSubtype === "exam_city" && (
            <span className="rounded bg-saffron/15 px-1.5 py-0.5 text-[11px] font-bold text-saffron">EXAM CITY</span>
          )}
          {card.lastChecked && (
            <span className="ml-auto text-[11.5px] text-ink/45">Last checked {formatDateIN(card.lastChecked)}</span>
          )}
        </div>

        <h3 className="font-ui mt-1.5 text-[17px] font-bold leading-snug text-ink sm:text-[18px]">
          <Link
            to={`/admit-cards/${slugFor(card.title, card.id)}`}
            className="hover:underline hover:underline-offset-2"
          >
            {card.title}
          </Link>
        </h3>
        {card.examName && (
          <p className="mt-1 text-[13px] text-ink/65 sm:text-[14px]">{card.examName}</p>
        )}
      </div>

      <div className="px-4 pb-3 pt-3 sm:px-5 sm:pb-4">
        <p className="min-h-11 text-[13px] font-semibold leading-snug text-ink/70 sm:text-[14px]">
          {examDay ? (
            <>
              Exam date: <span className="tabular-nums">{formatDateIN(card.examDateISO)}</span>
              <span className="text-ink/45"> · {examDay}</span>
            </>
          ) : (
            "Exam date: check the notice"
          )}
        </p>
        <div className="mt-2 flex items-center gap-2 sm:mt-0">
          <button
            onClick={() => setOpen((v) => !v)}
            className="h-11 shrink-0 rounded-lg border border-line bg-paper px-4 text-[13.5px] font-semibold text-ink/75 transition-colors hover:border-line-strong hover:text-ink"
            aria-expanded={open}
          >
            {open ? "Hide" : "Details"}
          </button>
          {card.admitUrl ? (
            <a
              href={safeUrl(card.admitUrl)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-11 flex-1 items-center justify-center gap-1.5 rounded-lg bg-ink px-4 text-[13.5px] font-bold text-white transition-colors hover:bg-saffron sm:flex-none sm:ml-auto"
            >
              {cta}
              <span aria-hidden="true">↗</span>
            </a>
          ) : (
            <span
              className="inline-flex h-11 flex-1 items-center justify-center rounded-lg border border-line text-[13px] font-semibold text-ink/45 sm:flex-none sm:ml-auto sm:px-4"
              title="Official download link is not on file yet"
            >
              Link pending
            </span>
          )}
        </div>
      </div>

      {open && (
        <div className="border-t border-line px-4 py-4 sm:px-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <div>
              <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">Exam date</p>
              <p className="mt-0.5 text-[13.5px] leading-snug text-ink">{formatDateIN(card.examDateISO)}</p>
            </div>
            <div>
              <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">Released</p>
              <p className="mt-0.5 text-[13.5px] leading-snug text-ink">{formatDateIN(card.notificationISO)}</p>
            </div>
          </div>
          <p className="mt-3 text-[12px] leading-relaxed text-ink/55">
            {card.linkKind === "candidate_portal"
              ? "The admit card downloads on the board's official portal after you log in with your application/registration number and date of birth — no public file link exists (by design, boards only release it to candidates)."
              : `This link opens the board's official notice${isPdf ? " (PDF)" : ""}. If it does not load, the board's website is the source of truth — availability can change without notice.`}
          </p>
          {card.sourceUrl && (
            <a
              href={safeUrl(card.sourceUrl)}
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
