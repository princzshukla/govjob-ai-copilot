import { useEffect, useState } from "react";
import { Share2 } from "lucide-react";
import type { FeedExam } from "../../lib/exams";
import { formatDateIN } from "../../lib/exams";
import { shareLink, whatsappShareUrl } from "../../lib/share";
import { safeUrl } from "../../lib/safeUrl";
import { toast } from "../../lib/toast";
import { AdLabel } from "./AdSlot";

/** Static width — no width animation on low-end devices. */
export function DeadlineBar({ days }: { days: number }) {
  const pct = days <= 0 ? 0 : Math.max(6, Math.min(100, (days / 45) * 100));
  const tone = days <= 7 ? "bg-alert" : days <= 14 ? "bg-saffron" : "bg-govgreen";
  return (
    <div className="h-[5px] w-full overflow-hidden rounded-full bg-cream">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-cream px-1.5 py-0.5 text-[12px] font-medium text-ink sm:px-2 sm:py-1 sm:text-[12.5px]">
      {children}
    </span>
  );
}

function DetailGrid({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">
        {label}
      </p>
      <p className="mt-0.5 text-[13.5px] leading-snug text-ink">{value}</p>
    </div>
  );
}

function currentExamId(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("exam");
}

/** The organic notification card. Details expand in place — no modal. */
export function JobCard({
  exam,
  verdict,
}: {
  exam: FeedExam;
  /** set after an eligibility check; null when the user has no profile yet */
  verdict?: "eligible" | "borderline" | "check" | "ineligible" | null;
}) {
  const [open, setOpen] = useState(() => currentExamId() === exam.id);
  const closed = exam.deadlineDays <= 0;
  const pct = exam.minPercentage;

  useEffect(() => {
    const onPop = () => setOpen(currentExamId() === exam.id);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [exam.id]);

  const toggleDetails = () => {
    if (!open) {
      const params = new URLSearchParams(window.location.search);
      params.set("exam", exam.id);
      window.history.pushState({}, "", `${window.location.pathname}?${params.toString()}`);
      setOpen(true);
    } else if (currentExamId() === exam.id) {
      window.history.back();
    } else {
      setOpen(false);
    }
  };

  const onShare = async () => {
    const url = exam.applyUrl || exam.pdfUrl || exam.sourceUrl || window.location.href;
    try {
      const result = await shareLink(exam.title, url);
      if (result === "copied") {
        toast("info", "Link copied", "Share it with a friend who's preparing.");
      }
    } catch {
      toast("warn", "Couldn't copy", "Try the official notification link instead.");
    }
  };

  const shareUrl = whatsappShareUrl(
    exam.title,
    exam.applyUrl || exam.pdfUrl || exam.sourceUrl || window.location.href,
  );

  return (
    <article className="scroll-mt-24 rounded-lg border border-line bg-[#fbfaf7]">
      <div className="px-4 pt-3 sm:px-5 sm:pt-4">
        <div className="flex flex-wrap items-center gap-2">
          {exam.isNew && (
            <span className="rounded bg-govgreen px-1.5 py-0.5 text-[11px] font-bold text-white">
              NEW
            </span>
          )}
          <span className="text-[12.5px] text-ink/55">{exam.state}</span>
          {exam.lastChecked && (
            <span className="ml-auto text-[11.5px] text-ink/45">
              Verified {formatDateIN(exam.lastChecked)}
            </span>
          )}
        </div>

        <h3 className="font-ui mt-1.5 text-[17px] font-bold leading-snug text-ink sm:text-[18px]">
          {exam.title}
        </h3>
        <p className="mt-1 text-[13px] text-ink/65 sm:text-[14px]">
          {exam.department}
          {exam.postType ? <span className="text-ink/45"> · {exam.postType}</span> : null}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          <Chip>
            Min {pct === null ? "—" : `${pct}%`}
          </Chip>
          <Chip>
            Age {exam.ageMin}–{exam.ageMax}
          </Chip>
          {verdict && (
            <span
              className={`rounded px-2 py-1 text-[12.5px] font-bold ${
                verdict === "eligible"
                  ? "bg-govgreen/15 text-govgreen"
                  : verdict === "borderline"
                    ? "bg-saffron/25 text-saffron"
                    : verdict === "check"
                      ? "border border-saffron/50 text-saffron"
                      : "bg-alert/10 text-alert"
              }`}
            >
              {verdict === "eligible"
                ? "You qualify"
                : verdict === "borderline"
                  ? "Last attempt"
                  : verdict === "check"
                    ? "Check notification"
                    : "Not eligible"}
            </span>
          )}
        </div>
      </div>

      {/* mobile deadline + actions */}
      <div className="px-4 pb-3 pt-3 sm:hidden">
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <DeadlineBar days={exam.deadlineDays} />
          </div>
          <p
            className={`whitespace-nowrap text-[14px] font-semibold tabular-nums ${
              closed ? "text-alert" : exam.deadlineDays <= 7 ? "text-alert" : "text-ink/70"
            }`}
          >
            {closed ? "Closed" : `${exam.deadlineDays}d left`}
          </p>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={toggleDetails}
            aria-expanded={open}
            aria-controls={`details-${exam.id}`}
            className="h-11 shrink-0 rounded-lg border-2 border-line bg-white px-4 text-[14px] font-semibold text-ink"
          >
            {open ? "Hide" : "Details"}
          </button>
          <button
            onClick={onShare}
            aria-label="Share this job"
            className="grid size-11 shrink-0 place-items-center rounded-lg border-2 border-line bg-white text-ink/70"
          >
            <Share2 size={18} aria-hidden="true" />
          </button>
          {closed ? (
            <button
              disabled
              className="h-11 flex-1 cursor-not-allowed rounded-lg bg-ink/15 text-[13.5px] font-bold text-ink/55"
            >
              Window closed
            </button>
          ) : exam.applyUrl ? (
            <a
              href={safeUrl(exam.applyUrl)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-11 flex-1 items-center justify-center rounded-lg bg-saffron text-[14px] font-bold text-white"
            >
              Apply Now
            </a>
          ) : (
            <button
              disabled
              title="Official application portal is not on file yet"
              className="h-11 flex-1 cursor-not-allowed rounded-lg bg-saffron/50 text-[13.5px] font-bold text-white/80"
            >
              Apply
            </button>
          )}
        </div>
      </div>

      {/* desktop deadline + actions */}
      <div className="hidden flex-wrap items-center gap-x-3 gap-y-2 px-5 pb-4 pt-3 sm:flex">
        <div className="min-w-[130px] flex-1">
          <DeadlineBar days={exam.deadlineDays} />
        </div>
        <p
          className={`whitespace-nowrap text-[14px] font-semibold tabular-nums ${
            closed ? "text-alert" : exam.deadlineDays <= 7 ? "text-alert" : "text-ink/70"
          }`}
        >
          {closed ? "Closed" : `${exam.deadlineDays} days left`}
        </p>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={toggleDetails}
            aria-expanded={open}
            aria-controls={`details-${exam.id}`}
            className="h-11 rounded-lg border-2 border-line bg-white px-4 text-[14px] font-semibold text-ink transition-colors hover:border-line-strong"
          >
            {open ? "Hide" : "Details"}
          </button>
          <button
            onClick={onShare}
            aria-label="Share this job"
            className="grid size-11 place-items-center rounded-lg border-2 border-line bg-white text-ink/70 hover:border-line-strong"
          >
            <Share2 size={18} aria-hidden="true" />
          </button>
          {closed ? (
            <button
              disabled
              title="This application window is closed"
              className="h-11 cursor-not-allowed rounded-lg bg-ink/15 px-5 text-[14px] font-bold text-ink/55"
            >
              Window closed
            </button>
          ) : exam.applyUrl ? (
            <a
              href={safeUrl(exam.applyUrl)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-11 items-center rounded-lg bg-saffron px-5 text-[14px] font-bold text-white shadow-[0_2px_0_rgba(0,0,0,.12)]"
            >
              Apply Now
            </a>
          ) : (
            <button
              disabled
              title="Official application portal is not on file yet"
              className="h-11 cursor-not-allowed rounded-lg bg-saffron/50 px-5 text-[14px] font-bold text-white/80"
            >
              Apply
            </button>
          )}
        </div>
      </div>

      {open && (
        <div
          id={`details-${exam.id}`}
          className="border-t border-line bg-[#fbfaf7] px-4 py-4 sm:px-5"
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <DetailGrid label="Application last date" value={formatDateIN(exam.lastDateISO)} />
            <DetailGrid
              label="Age at cutoff"
              value={`${exam.ageMin}–${exam.ageMax} yrs (cutoff ${formatDateIN(exam.cutoffDate)})`}
            />
            <DetailGrid label="Exam date" value={formatDateIN(exam.examDate)} />
            <DetailGrid
              label="Allowed degrees"
              value={exam.degrees.length ? exam.degrees.join(", ") : "—"}
            />
            {exam.streams.length > 0 && (
              <DetailGrid label="Allowed streams" value={exam.streams.join(", ")} />
            )}
            <DetailGrid
              label="Final year students"
              value={
                exam.allowsFinalYear === null
                  ? "Check notification"
                  : exam.allowsFinalYear
                    ? "Allowed"
                    : "Not allowed"
              }
            />
          </div>

          {exam.topics.length > 0 && (
            <div className="mt-4">
              <p className="text-[10.5px] font-bold tracking-[.12em] text-ink/50 uppercase">
                Topics for the paper
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {exam.topics.slice(0, 12).map((t) => (
                  <span key={t} className="rounded bg-cream px-2 py-1 text-[12px] font-medium text-ink/80">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-3">
            {exam.applyUrl && (
              <a
                href={safeUrl(exam.applyUrl)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-11 items-center rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white hover:bg-ink"
              >
                Apply on official portal ↗
              </a>
            )}
            {exam.pdfUrl && (
              <a
                href={safeUrl(exam.pdfUrl)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-11 items-center rounded-lg border-2 border-ink px-4 text-[13.5px] font-bold text-ink hover:border-saffron hover:text-saffron"
              >
                Official notification (PDF) ↗
              </a>
            )}
            {exam.sourceUrl && !exam.applyUrl && (
              <a
                href={safeUrl(exam.sourceUrl)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[13px] font-semibold text-saffron hover:underline"
              >
                Source: official portal ↗
              </a>
            )}
            <a
              href={safeUrl(shareUrl)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-11 items-center gap-1.5 rounded-lg border-2 border-line px-4 text-[13px] font-semibold text-ink/70 hover:border-saffron hover:text-saffron"
            >
              <Share2 size={15} aria-hidden="true" /> Share on WhatsApp
            </a>
          </div>
        </div>
      )}
    </article>
  );
}

/**
 * A paid placement.
 *
 * Visually distinct (dashed rule, tinted paper, muted type) and explicitly
 * labelled before anything else on the card — never mistaken for a notification.
 */
export function SponsoredJobCard({ job }: { job: import("../../lib/ads").SponsoredJob }) {
  return (
    <article
      aria-label="Sponsored job listing"
      className="group rounded-lg border border-dashed border-ink/25 bg-cream/50 px-4 py-4 transition-colors hover:bg-cream/80 sm:px-5"
    >
      <div className="flex flex-wrap items-center gap-2">
        <AdLabel kind="Sponsored" />
        <span className="text-[12.5px] text-ink/55">{job.state}</span>
        <span className="ml-auto text-[12px] font-medium text-ink/55">
          Paid placement · not a government notification
        </span>
      </div>

      <h3 className="font-ui mt-1.5 text-[17px] font-bold leading-snug text-ink/75 sm:text-[18px]">
        {job.title}
      </h3>
      <p className="mt-1 text-[13px] text-ink/55 sm:text-[14px]">{job.department}</p>

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="rounded bg-white px-2 py-1 text-[12.5px] font-medium text-ink/70">
          {job.qualification}
        </span>
        <span className="rounded bg-white px-2 py-1 text-[12.5px] font-semibold text-ink/70">
          {job.salary}
        </span>
      </div>

      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        <p className="whitespace-nowrap text-[14px] font-semibold tabular-nums text-ink/55">
          {job.deadlineDays} days left
        </p>
        <button className="ml-auto h-11 rounded-lg border-2 border-ink/30 bg-white px-4 text-[14px] font-semibold text-ink/70 hover:border-ink/50">
          Details
        </button>
        <button className="h-11 rounded-lg border-2 border-ink/25 bg-white px-5 text-[14px] font-bold text-ink/70 hover:border-ink/50">
          Apply Now
        </button>
      </div>
    </article>
  );
}
