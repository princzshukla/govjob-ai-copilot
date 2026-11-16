import { useMemo, useState } from "react";
import { JOBS } from "../../lib/jobs";
import { evaluateAll, PROFILE } from "../../lib/eligibility";

/**
 * The pages behind the nav. Eligibility and Roadmap are the product's core.
 * No motion library — instant render, no layout thrash on low-end devices.
 */

function PageShell({
  kicker,
  title,
  subtitle,
  action,
  children,
}: {
  kicker: string;
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg border border-line bg-white">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-line bg-cream/70 px-5 py-4">
        <div>
          <p className="text-[11px] font-bold tracking-[.16em] text-ink/50 uppercase">
            {kicker}
          </p>
          <h1 className="mt-1 text-[22px] font-extrabold tracking-tight text-ink">
            {title}
          </h1>
          <p className="mt-0.5 text-[14px] text-ink/65">{subtitle}</p>
        </div>
        {action}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* My Eligibility — the product's core feature                         */
/* ------------------------------------------------------------------ */

export function EligibilityPage() {
  const rows = useMemo(() => evaluateAll(JOBS), []);
  const eligible = rows.filter((r) => r.reasons.length === 0);
  const ineligible = rows.filter((r) => r.reasons.length > 0);
  const borderline = eligible.filter((r) => r.lastAttempt);

  return (
    <PageShell
      kicker="My Eligibility"
      title="Every rule, checked against you"
      subtitle={`${eligible.length} eligible · ${borderline.length} last attempt · ${ineligible.length} not eligible`}
      action={
        <button className="h-11 rounded-lg bg-saffron px-5 text-[14.5px] font-bold text-white transition-transform hover:-translate-y-0.5">
          Update Profile
        </button>
      }
    >
      {/* profile card */}
      <div className="mb-5 flex flex-wrap items-center gap-x-8 gap-y-3 border border-line bg-cream/50 px-5 py-4">
        <div>
          <p className="text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">Candidate</p>
          <p className="text-[16px] font-bold text-ink">{PROFILE.name}</p>
        </div>
        {[
          ["DOB", PROFILE.dob],
          ["Category", PROFILE.category],
          ["Domicile", PROFILE.domicile],
          ["Qualification", PROFILE.degree],
          ["Percentage", `${PROFILE.percentage}%`],
        ].map(([k, v]) => (
          <div key={k}>
            <p className="text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">{k}</p>
            <p className="text-[15px] font-semibold text-ink">{v}</p>
          </div>
        ))}
      </div>

      {/* summary strip */}
      <div className="mb-5 grid grid-cols-3 gap-3">
        <div className="bg-govgreen/15 px-4 py-3.5">
          <p className="font-ui text-[30px] font-extrabold tabular-nums text-govgreen">
            {eligible.length}
          </p>
          <p className="text-[13px] font-semibold text-ink/70">Eligible now</p>
        </div>
        <div className="bg-saffron/20 px-4 py-3.5">
          <p className="font-ui text-[30px] font-extrabold tabular-nums text-saffron">
            {borderline.length}
          </p>
          <p className="text-[13px] font-semibold text-ink/70">Last attempt</p>
        </div>
        <div className="bg-alert/10 px-4 py-3.5">
          <p className="font-ui text-[30px] font-extrabold tabular-nums text-alert">
            {ineligible.length}
          </p>
          <p className="text-[13px] font-semibold text-ink/70">Not eligible</p>
        </div>
      </div>

      {/* eligible list */}
      <p className="mb-2 text-[12px] font-bold tracking-[.14em] text-ink/55 uppercase">
        Eligible examinations
      </p>
      <div className="space-y-2.5">
        {eligible.map((r) => (
          <div
            key={r.job.id}
            className={`border border-line bg-white px-4 py-3.5 ${
              r.lastAttempt ? "border-l-4 border-l-saffron" : ""
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-govgreen/15 px-1.5 py-0.5 text-[11px] font-bold text-govgreen">
                    ELIGIBLE
                  </span>
                  {r.lastAttempt && (
                    <span className="rounded bg-saffron/20 px-1.5 py-0.5 text-[11px] font-bold text-saffron">
                      LAST ATTEMPT
                    </span>
                  )}
                </div>
                <p className="mt-1.5 text-[16px] font-bold text-ink">{r.job.title}</p>
                <p className="mt-0.5 text-[13.5px] text-ink/60">{r.job.department}</p>
              </div>
              <div className="flex items-center gap-6 text-right">
                <div>
                  <p className="text-[11px] font-bold tracking-[.12em] text-ink/50 uppercase">
                    Age at cutoff
                  </p>
                  <p className="text-[15px] font-bold tabular-nums text-ink">
                    {r.ageAtCutoff} <span className="font-normal text-ink/50">/ {r.maxAllowed}</span>
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-bold tracking-[.12em] text-ink/50 uppercase">
                    Syllabus overlap
                  </p>
                  <p className="text-[15px] font-bold tabular-nums text-ink">{r.overlap}%</p>
                </div>
                <button className="h-10 rounded-lg bg-ink px-4 text-[14px] font-bold text-white transition-colors hover:bg-saffron">
                  View Roadmap
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ineligible with reasons */}
      {ineligible.length > 0 && (
        <details className="mt-5 border border-line bg-white">
          <summary className="cursor-pointer px-4 py-3 text-[14.5px] font-bold text-ink/70">
            Not eligible ({ineligible.length}) — see reasons
          </summary>
          <div className="border-t border-line px-4 py-3">
            {ineligible.map((r) => (
              <div key={r.job.id} className="py-2.5">
                <p className="text-[15px] font-semibold text-ink">{r.job.title}</p>
                <ul className="mt-1 space-y-1">
                  {r.reasons.map((reason) => (
                    <li key={reason} className="flex items-start gap-2 text-[13.5px] text-alert">
                      <span className="font-bold">•</span>
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </details>
      )}
    </PageShell>
  );
}

/* ------------------------------------------------------------------ */
/* My Roadmap — week-by-week plan with progress                        */
/* ------------------------------------------------------------------ */

const PHASES = [
  { from: 1, to: 4, name: "Foundation & Concepts", focus: "Build the base" },
  { from: 5, to: 8, name: "Practice & PYQs", focus: "Solve previous papers" },
  { from: 9, to: 16, name: "Intensive Practice", focus: "Speed and accuracy" },
  { from: 17, to: 20, name: "Revision", focus: "Close the weak spots" },
  { from: 21, to: 24, name: "Full Mocks", focus: "Exam simulation" },
];

function weekPhase(week: number) {
  return PHASES.find((p) => week >= p.from && week <= p.to) ?? PHASES[0];
}

const PHASE_TOPICS: Record<string, string[]> = {
  "Foundation & Concepts": [
    "Ratio & proportion, percentage basics — 40 questions daily.",
    "Profit & loss, averages — read one full chapter, then drill.",
    "Time & work, speed & distance — focus on unit conversion.",
    "Basic algebra, simplification — 25 questions, 20 minutes.",
  ],
  "Practice & PYQs": [
    "Solve 2019–2025 papers; log every error in the mistake register.",
    "Sectional speed drills on percentage and ratio — 30 questions, 15 minutes.",
    "Mixed PYQ sets with a 25-minute timer.",
    "Accuracy block: 50 questions, target 90% before speed.",
  ],
  "Intensive Practice": [
    "Full sectional mocks under exam conditions, 1 hour each.",
    "Negative-marking drills — leave 5 questions blank on purpose.",
    "Timed mixed sets, then a full analysis of every wrong answer.",
    "Weak-topic relay: pick your lowest mastery subject and drill it.",
  ],
  Revision: [
    "Revise only topics where accuracy is below 70%.",
    "Formula sheet rebuild — write from memory, check, repeat.",
    "Re-solve every mistake-register entry from scratch.",
    "Mock test 3, then a full error-log review.",
  ],
  "Full Mocks": [
    "Full-length mock every other day; analyse the error log after each.",
    "Two full mocks back to back — build the endurance.",
    "Final mock under real timing, then light revision only.",
    "Rest, light reading, and a last glance at the formula sheet.",
  ],
};

function weekPlan(week: number) {
  const phase = weekPhase(week);
  const items = PHASE_TOPICS[phase.name];
  const idx = (week - phase.from) % items.length;
  return items[idx];
}

export function RoadmapPage() {
  const [weeks, setWeeks] = useState(24);
  const [done, setDone] = useState<number[]>([1, 2, 3, 4, 5]);
  const [exam, setExam] = useState(JOBS[0].title);

  const list = useMemo(
    () => Array.from({ length: weeks }, (_, i) => i + 1),
    [weeks],
  );
  const pct = Math.round((done.length / weeks) * 100);

  const toggle = (w: number) =>
    setDone((d) => (d.includes(w) ? d.filter((x) => x !== w) : [...d, w]));

  return (
    <PageShell
      kicker="My Roadmap"
      title="Your week-by-week preparation"
      subtitle={`${done.length} of ${weeks} weeks complete · ${exam}`}
      action={
        <button
          onClick={() => setDone([])}
          className="h-11 rounded-lg border-2 border-line bg-white px-4 text-[14px] font-bold text-ink transition-colors hover:border-line-strong"
        >
          Reset Progress
        </button>
      }
    >
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-[14.5px] font-semibold text-ink">
          Target exam
          <select
            value={exam}
            onChange={(e) => setExam(e.target.value)}
            className="h-11 rounded-lg border-2 border-line bg-white px-3 text-[14.5px] outline-none focus:border-saffron"
          >
            {JOBS.slice(0, 6).map((j) => (
              <option key={j.id}>{j.title}</option>
            ))}
          </select>
        </label>
        <div className="flex items-center gap-1.5">
          {[12, 24].map((w) => (
            <button
              key={w}
              onClick={() => setWeeks(w)}
              className={`h-11 rounded-lg border-2 px-4 text-[14px] font-bold transition-colors ${
                weeks === w
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-white hover:border-line-strong"
              }`}
            >
              {w} weeks
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3">
          <div className="h-3 w-40 overflow-hidden rounded-full bg-cream">
            <div
              className="h-full rounded-full bg-govgreen transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="font-ui text-[16px] font-extrabold tabular-nums text-ink">{pct}%</span>
        </div>
      </div>

      <div className="space-y-2.5">
        {list.map((week) => {
          const phase = weekPhase(week);
          const isDone = done.includes(week);
          return (
            <button
              key={week}
              onClick={() => toggle(week)}
              aria-pressed={isDone}
              className={`flex w-full items-start gap-4 border px-4 py-3.5 text-left transition-colors ${
                isDone
                  ? "border-govgreen/40 bg-govgreen/10"
                  : "border-line bg-white hover:bg-cream/60"
              }`}
            >
              <span
                className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full border-2 text-[12px] font-bold transition-colors ${
                  isDone ? "border-govgreen bg-govgreen text-white" : "border-line text-ink/50"
                }`}
              >
                {isDone ? "✓" : week}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-3">
                  <p className="text-[15.5px] font-bold text-ink">Week {week}</p>
                  <p className="text-[13px] font-semibold text-saffron">{phase.name}</p>
                  <p className="text-[13px] text-ink/55">{phase.focus}</p>
                </div>
                <p className="mt-1 text-[13.5px] text-ink/65">{weekPlan(week)}</p>
              </div>
              <span className="shrink-0 text-[12.5px] font-bold text-ink/45 tabular-nums">
                {isDone ? "DONE" : "PENDING"}
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-4 text-[13px] text-ink/55">
        Progress is saved to your account. The plan re-orders itself around whichever
        topic your drills score lowest.
      </p>
    </PageShell>
  );
}
