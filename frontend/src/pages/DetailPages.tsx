import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import type { AdmitCard, ExamNotification } from "../types";
import { formatDateIN } from "../lib/exams";
import { slugFor } from "../lib/slug";
import { getPrerenderData } from "../lib/prerender-data";
import { jobFaqs } from "../seo/faq";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <tr className="border-b border-line">
      <th scope="row" className="py-2 pr-4 text-left font-semibold text-ink/60">
        {label}
      </th>
      <td className="py-2 text-left text-ink">{value}</td>
    </tr>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto max-w-[900px] px-4 py-8 sm:px-5">
      <nav className="mb-5 text-[12.5px] text-ink/55" aria-label="Breadcrumb">
        <Link to="/" className="underline underline-offset-2">Home</Link>
        <span aria-hidden="true"> / </span>
        <span>Notification</span>
      </nav>
      {children}
    </main>
  );
}

export function JobPage() {
  const { key = "" } = useParams();
  const data = getPrerenderData();
  const [exam, setExam] = useState<ExamNotification | null>(
    () => data?.exam ?? data?.exams?.find((e) => slugFor(e.title, e.id) === key) ?? null,
  );

  useEffect(() => {
    if (exam || !key) return;
    let cancelled = false;
    fetch(`/api/v1/eligibility/exams/${encodeURIComponent(key)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((row) => {
        if (!cancelled && row) setExam(row);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [key, exam]);

  if (!exam) {
    return (
      <Shell>
        <p className="text-ink/60">Loading notification…</p>
      </Shell>
    );
  }

  const faqs = jobFaqs(exam);
  const closed = exam.application_deadline < new Date().toISOString().slice(0, 10);
  const related = (data?.exams ?? [])
    .filter((e) => e.id !== exam.id && e.organizing_body === exam.organizing_body)
    .slice(0, 4);

  return (
    <Shell>
      {closed && (
        <p className="mb-4 rounded-lg border border-line-strong bg-white px-4 py-3 text-[13.5px] font-semibold text-ink/70">
          Closed cycle — kept for reference. Check the official board site for the next notification.
        </p>
      )}

      <p className="font-mono text-[11px] font-bold uppercase tracking-[.18em] text-saffron">
        {exam.organizing_body}
      </p>
      <h1 className="mt-2 text-[28px] font-extrabold leading-tight tracking-tight text-ink sm:text-[36px]">
        {exam.title}
      </h1>

      <p className="mt-4 max-w-3xl text-[15.5px] leading-relaxed text-ink/80">
        The application window on file closes on {formatDateIN(exam.application_deadline)}.
        Candidates need {exam.allowed_degrees?.join(", ") || "the required qualification"} and must be
        between {exam.min_age} and {exam.max_age_general} years old as of {formatDateIN(exam.age_cutoff_date)}.
      </p>

      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Key facts</h2>
        <table className="mt-3 w-full text-[14px]">
          <tbody>
            <Fact label="Notification date" value={formatDateIN(exam.notification_date)} />
            <Fact label="Applications open" value={formatDateIN(exam.application_start_date ?? null)} />
            <Fact label="Application deadline" value={formatDateIN(exam.application_deadline)} />
            <Fact label="Exam date" value={formatDateIN(exam.exam_date)} />
            <Fact label="Age band" value={`${exam.min_age}–${exam.max_age_general} years`} />
            <Fact label="Age cutoff date" value={formatDateIN(exam.age_cutoff_date)} />
            <Fact label="Qualification" value={exam.allowed_degrees?.join(", ") || "Not stated"} />
            <Fact
              label="Minimum percentage"
              value={exam.min_percentage ? `${Number(exam.min_percentage)}%` : "Not stated"}
            />
            <Fact label="Domicile" value={exam.state_restriction || "Pan-India"} />
            <Fact
              label="Final-year students"
              value={exam.allows_final_year === null ? "Not stated" : exam.allows_final_year ? "Allowed" : "Not allowed"}
            />
            <Fact
              label="Attempt limit"
              value={exam.max_attempts ? String(exam.max_attempts) : "Not stated"}
            />
            <Fact
              label="Last verified"
              value={formatDateIN(exam.verified_on || exam.last_checked_at)}
            />
          </tbody>
        </table>
      </section>

      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">
          Eligibility, rule by rule
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-[14.5px] leading-relaxed text-ink/80">
          <li>Age must be between {exam.min_age} and {exam.max_age_general} years on {formatDateIN(exam.age_cutoff_date)}.</li>
          <li>
            Qualification: {exam.allowed_degrees?.join(", ") || "see the official notification"}
            {exam.allowed_streams?.length ? ` in ${exam.allowed_streams.join(", ")}` : ""}.
          </li>
          {exam.min_percentage ? <li>Minimum {Number(exam.min_percentage)}% in the qualifying examination.</li> : null}
          <li>{exam.state_restriction ? `This vacancy is restricted to ${exam.state_restriction}.` : "This is a Pan-India vacancy."}</li>
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">How to apply</h2>
        <p className="mt-2 text-[14.5px] leading-relaxed text-ink/80">
          {exam.apply_url
            ? "The official application portal is linked below. Apply only through that link."
            : "No application portal is on file. Use the official notification PDF for application instructions."}
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          {exam.apply_url && (
            <a href={exam.apply_url} target="_blank" rel="noopener noreferrer" className="rounded-full bg-ink px-5 py-2.5 text-[13.5px] font-bold text-white">
              Apply on official portal
            </a>
          )}
          {exam.official_pdf_url && (
            <a href={exam.official_pdf_url} target="_blank" rel="noopener noreferrer" className="rounded-full border-2 border-ink px-5 py-2.5 text-[13.5px] font-bold text-ink">
              Official notification PDF
            </a>
          )}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Sources and verification</h2>
        <ul className="mt-3 space-y-2 text-[14.5px] text-ink/80">
          {exam.source_url && (
            <li>
              Official source:{" "}
              <a href={exam.source_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2">
                {exam.source_url}
              </a>
            </li>
          )}
          <li>Last checked: {formatDateIN(exam.last_checked_at)}</li>
          <li>Verification status: {exam.verification_status || "check required"}</li>
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Questions candidates ask</h2>
        <dl className="mt-4 space-y-5">
          {faqs.map(({ question, answer }) => (
            <div key={question}>
              <dt className="text-[14.5px] font-bold text-ink">{question}</dt>
              <dd className="mt-1 text-[14px] leading-relaxed text-ink/70">{answer}</dd>
            </div>
          ))}
        </dl>
      </section>

      {related.length > 0 && (
        <section className="mt-10 border-t border-line pt-6">
          <h2 className="text-[21px] font-extrabold tracking-tight text-ink">More from {exam.organizing_body}</h2>
          <ul className="mt-3 space-y-2">
            {related.map((row) => (
              <li key={row.id}>
                <Link to={`/jobs/${slugFor(row.title, row.id)}`} className="text-[14.5px] underline underline-offset-2">
                  {row.title}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </Shell>
  );
}

export function AdmitCardPage() {
  const { key = "" } = useParams();
  const data = getPrerenderData();
  const [card, setCard] = useState<AdmitCard | null>(
    () => data?.admitCard ?? data?.admitCards?.find((c) => slugFor(c.title, c.id) === key) ?? null,
  );

  useEffect(() => {
    if (card || !key) return;
    let cancelled = false;
    fetch(`/api/v1/admit-cards/${encodeURIComponent(key)}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((row) => {
        if (!cancelled && row) setCard(row);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [key, card]);

  if (!card) {
    return (
      <Shell>
        <p className="text-ink/60">Loading admit card…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <p className="font-mono text-[11px] font-bold uppercase tracking-[.18em] text-saffron">
        {card.organizing_body}
      </p>
      <h1 className="mt-2 text-[28px] font-extrabold leading-tight tracking-tight text-ink sm:text-[36px]">
        {card.title}
      </h1>
      <p className="mt-4 max-w-3xl text-[15.5px] leading-relaxed text-ink/80">
        The exam date on file is {formatDateIN(card.exam_date)}. The link below is the official
        download or candidate portal published by the board — we never substitute a third-party copy.
      </p>
      <section className="mt-8">
        <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Key facts</h2>
        <table className="mt-3 w-full text-[14px]">
          <tbody>
            <Fact label="Organising body" value={card.organizing_body} />
            <Fact label="Exam" value={card.exam_name || "Not stated"} />
            <Fact label="Notice type" value={card.notice_subtype === "exam_city" ? "Exam-city intimation" : "Admit card"} />
            <Fact label="Notification date" value={formatDateIN(card.notification_date)} />
            <Fact label="Exam date" value={formatDateIN(card.exam_date)} />
            <Fact label="Link type" value={card.link_kind || "Notice PDF"} />
            <Fact label="Last checked" value={formatDateIN(card.last_checked_at)} />
          </tbody>
        </table>
      </section>
      {card.admit_url && (
        <section className="mt-8">
          <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Official download</h2>
          <a href={card.admit_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block rounded-full bg-ink px-5 py-2.5 text-[13.5px] font-bold text-white">
            Open official link
          </a>
          <p className="mt-3 text-[13.5px] text-ink/60">
            Carry a valid photo ID to the centre. Check your admit card for the reporting time.
          </p>
        </section>
      )}
      {card.source_url && (
        <section className="mt-8">
          <h2 className="text-[21px] font-extrabold tracking-tight text-ink">Source</h2>
          <a href={card.source_url} target="_blank" rel="noopener noreferrer" className="text-[14.5px] underline underline-offset-2">
            {card.source_url}
          </a>
        </section>
      )}
    </Shell>
  );
}
