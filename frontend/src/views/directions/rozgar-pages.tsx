import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import * as api from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { toast } from "../../lib/toast";
import {
  loadDraftProfile,
  saveDraftProfile,
  clearDraftProfile,
} from "../../lib/draft";
import { STATES } from "../../lib/exams";
import type {
  CandidateProfile,
  EligibilityCheckResponse,
  ExamMatchResult,
  SavedRoadmap,
  TopicMasteryItem,
} from "../../types";

/**
 * My Eligibility and My Roadmap — the product's core, wired to the live backend.
 * No motion library — instant render, low-end friendly.
 */

const input =
  "h-11 w-full rounded-lg border-2 border-line bg-white px-3 text-[14.5px] text-ink outline-none placeholder:text-ink/45 focus:border-saffron";
const label = "mb-1 text-[10.5px] font-bold tracking-[.14em] text-ink/50 uppercase";

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
/* My Eligibility                                                      */
/* ------------------------------------------------------------------ */

function ResultRow({ r, tone }: { r: ExamMatchResult; tone: "ok" | "warn" | "bad" }) {
  const border =
    tone === "ok" ? "border-govgreen/40" : tone === "warn" ? "border-saffron/50" : "border-line";
  return (
    <div className={`border-l-4 ${border} bg-cream/30 px-4 py-3`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[15.5px] font-bold leading-snug text-ink">{r.title}</p>
          <p className="mt-0.5 text-[13px] text-ink/60">{r.organizing_body}</p>
        </div>
        <div className="flex items-center gap-4 text-right">
          <div>
            <p className="text-[10px] font-bold tracking-[.12em] text-ink/50 uppercase">
              Age
            </p>
            <p className="text-[14px] font-bold tabular-nums text-ink">
              {r.candidate_age_at_cutoff} <span className="font-normal text-ink/50">/ {r.max_allowed_age}</span>
            </p>
          </div>
          {r.syllabus_overlap_pct !== null && r.syllabus_overlap_pct !== undefined && (
            <div>
              <p className="text-[10px] font-bold tracking-[.12em] text-ink/50 uppercase">
                Overlap
              </p>
              <p className="text-[14px] font-bold tabular-nums text-ink">
                {Math.round(r.syllabus_overlap_pct)}%
              </p>
            </div>
          )}
          {r.apply_url && (
            <a
              href={r.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-9 items-center rounded-lg bg-saffron px-3 text-[13px] font-bold text-white"
            >
              Apply ↗
            </a>
          )}
          {r.official_pdf_url && (
            <a
              href={r.official_pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex h-9 items-center rounded-lg border-2 border-ink px-3 text-[13px] font-bold text-ink hover:bg-ink hover:text-white"
            >
              PDF ↗
            </a>
          )}
        </div>
      </div>
      {tone === "bad" && r.reasons_failed.length > 0 && (
        <ul className="mt-2 space-y-1">
          {r.reasons_failed.map((reason) => (
            <li key={reason} className="flex items-start gap-2 text-[13px] text-alert">
              <span className="font-bold">•</span>
              {reason}
            </li>
          ))}
        </ul>
      )}
      {tone === "warn" && (
        <p className="mt-2 text-[12.5px] font-semibold text-saffron">
          Some rule needs a human check — read the notification before applying.
        </p>
      )}
    </div>
  );
}

export function EligibilityPage({
  result,
  onResultChange,
}: {
  result: EligibilityCheckResponse | null;
  onResultChange: (r: EligibilityCheckResponse) => void;
}) {
  const { user, promptSignIn } = useAuth();
  const [profile, setProfile] = useState<CandidateProfile>(() => loadDraftProfile() ?? {});
  const [parsing, setParsing] = useState(false);
  const [resumeMsg, setResumeMsg] = useState<string | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [checking, setChecking] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(null);

  const update = (field: keyof CandidateProfile, value: unknown) =>
    setProfile((p) => {
      const next = { ...p, [field]: value };
      saveDraftProfile(next);
      return next;
    });

  const handleResume = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setResumeMsg(null);
    if (file.size > 5 * 1024 * 1024) {
      setResumeMsg("PDF must be under 5 MB.");
      e.target.value = "";
      return;
    }
    if (!/\.pdf$/i.test(file.name) && file.type !== "application/pdf") {
      setResumeMsg("Please upload a PDF resume.");
      e.target.value = "";
      return;
    }
    setParsing(true);
    try {
      const data = await api.parseResume(file);
      setProfile((p) => {
        const next = { ...p, ...(data.extracted_profile ?? {}) };
        saveDraftProfile(next);
        return next;
      });
      setMissing((data.missing_fields ?? []).map((m) => m.label || m.field_name));
      setResumeMsg(data.message ?? "Resume parsed — review the fields below.");
    } catch (err) {
      setResumeMsg(err instanceof Error ? err.message : "Could not parse the resume.");
    } finally {
      setParsing(false);
      e.target.value = "";
    }
  };

  const runCheck = async (e?: FormEvent) => {
    e?.preventDefault();
    setFormError(null);
    setChecking(true);
    try {
      const res = await api.checkEligibility(profile);
      onResultChange(res);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Eligibility check failed.");
    } finally {
      setChecking(false);
    }
  };

  const saveProfile = async () => {
    if (!user) {
      promptSignIn("login");
      return;
    }
    setSaving(true);
    try {
      const res = await api.saveCandidateProfile(profile, savedId);
      setSavedId(res.profile_id);
      toast("success", "Profile saved", "Your eligibility profile is in your account.");
    } catch (err) {
      toast("warn", "Could not save profile", err instanceof Error ? err.message : "Try again.");
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    clearDraftProfile();
    setProfile({});
    setMissing([]);
    setResumeMsg(null);
    setFormError(null);
  };

  const counts = result
    ? {
        eligible: result.eligible_now.length,
        borderline: result.borderline_last_chance.length,
        manual: result.check_manually.length,
        ineligible: result.ineligible.length,
      }
    : null;

  return (
    <PageShell
      kicker="My Eligibility"
      title="Every rule, checked against you"
      subtitle={
        result
          ? `${counts?.eligible} eligible · ${counts?.borderline} last attempt · ${counts?.manual} to verify · ${counts?.ineligible} not eligible`
          : "Upload your resume (or enter details) — every notification is checked rule-by-rule."
      }
    >
      {/* resume upload */}
      <div className="mb-5 flex flex-wrap items-center gap-3 border border-line bg-cream/40 px-4 py-3">
        <label
          className={`inline-flex h-11 cursor-pointer items-center rounded-lg bg-ink px-4 text-[13.5px] font-bold text-white transition-colors hover:bg-saffron ${
            parsing ? "cursor-wait opacity-60" : ""
          }`}
        >
          <input
            type="file"
            accept=".pdf,application/pdf"
            className="sr-only"
            onChange={handleResume}
            disabled={parsing}
          />
          {parsing ? "Reading your resume…" : "Upload resume (PDF)"}
        </label>
        <p className="text-[12.5px] text-ink/60">
          Parsed on the server, never stored without your say-so. Guests: 3/day.
        </p>
        {resumeMsg && (
          <p role="status" className="w-full text-[12.5px] font-medium text-ink/75">
            {resumeMsg}
          </p>
        )}
        {missing.length > 0 && (
          <div className="flex w-full flex-wrap gap-1.5">
            {missing.map((m) => (
              <span
                key={m}
                className="rounded border border-saffron/50 bg-saffron/10 px-2 py-1 text-[12px] font-semibold text-saffron"
              >
                Missing: {m}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* profile form */}
      <form onSubmit={runCheck} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <label className={label} htmlFor="f-name">Full name</label>
          <input
            id="f-name"
            value={profile.full_name ?? ""}
            onChange={(e) => update("full_name", e.target.value)}
            placeholder="Aarav Kumar"
            className={input}
          />
        </div>
        <div>
          <label className={label} htmlFor="f-dob">Date of birth *</label>
          <input
            id="f-dob"
            type="date"
            value={profile.dob ?? ""}
            onChange={(e) => update("dob", e.target.value)}
            className={input}
            required
          />
        </div>
        <div>
          <label className={label} htmlFor="f-gender">Gender</label>
          <select
            id="f-gender"
            value={profile.gender ?? "Male"}
            onChange={(e) => update("gender", e.target.value)}
            className={input}
          >
            {["Male", "Female", "Other"].map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={label} htmlFor="f-category">Category *</label>
          <select
            id="f-category"
            value={profile.category ?? "General"}
            onChange={(e) => update("category", e.target.value)}
            className={input}
            required
          >
            {["General", "EWS", "OBC-NCL", "SC", "ST"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={label} htmlFor="f-domicile">Domicile state *</label>
          <select
            id="f-domicile"
            value={profile.domicile_state ?? ""}
            onChange={(e) => update("domicile_state", e.target.value)}
            className={input}
            required
          >
            <option value="">Select state…</option>
            {STATES.filter((s) => s !== "All India").map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={label} htmlFor="f-degree">Highest qualification *</label>
          <input
            id="f-degree"
            value={profile.highest_degree ?? ""}
            onChange={(e) => update("highest_degree", e.target.value)}
            placeholder="Graduate, B.Tech…"
            className={input}
            required
          />
        </div>
        <div>
          <label className={label} htmlFor="f-stream">Stream / branch</label>
          <input
            id="f-stream"
            value={profile.stream ?? ""}
            onChange={(e) => update("stream", e.target.value)}
            placeholder="Computer Science"
            className={input}
          />
        </div>
        <div>
          <label className={label} htmlFor="f-pct">Graduation % *</label>
          <input
            id="f-pct"
            type="number"
            inputMode="decimal"
            min={0}
            max={100}
            step="0.01"
            value={profile.percentage_cgpa ?? ""}
            onChange={(e) => update("percentage_cgpa", e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="58"
            className={input}
            required
          />
        </div>
        <div>
          <label className={label} htmlFor="f-year">Passing year</label>
          <input
            id="f-year"
            type="number"
            inputMode="numeric"
            min={1980}
            max={2035}
            value={profile.passing_year ?? ""}
            onChange={(e) => update("passing_year", e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="2024"
            className={input}
          />
        </div>
        <label className="flex items-center gap-2 self-end pb-2 text-[14px] font-semibold text-ink">
          <input
            type="checkbox"
            checked={profile.is_pwd === true || profile.is_pwd === "true" || profile.is_pwd === "yes"}
            onChange={(e) => update("is_pwd", e.target.checked)}
            className="size-5 accent-saffron"
          />
          PwD (with disability certificate)
        </label>
      </form>

      {formError && (
        <p role="alert" className="mt-3 rounded-lg border border-alert/40 bg-alert/10 px-4 py-2 text-[13.5px] font-medium text-alert">
          {formError}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={() => runCheck()}
          disabled={checking}
          className="h-12 rounded-lg bg-saffron px-6 text-[15px] font-bold text-white shadow-[0_2px_0_rgba(0,0,0,.12)] transition-opacity disabled:opacity-60"
        >
          {checking ? "Checking every rule…" : "Check eligibility"}
        </button>
        <button
          onClick={saveProfile}
          disabled={saving}
          className="h-12 rounded-lg bg-ink px-5 text-[14px] font-bold text-white transition-colors hover:bg-saffron disabled:opacity-60"
        >
          {saving ? "Saving…" : user ? "Save to my account" : "Sign in to save"}
        </button>
        <button
          onClick={reset}
          className="h-12 rounded-lg px-4 text-[13px] font-semibold text-ink/55 hover:text-ink"
        >
          Clear
        </button>
      </div>

      {/* results */}
      {result && counts && (
        <div className="mt-6 space-y-4 border-t border-line pt-5">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {[
              ["Eligible", counts.eligible, "text-govgreen bg-govgreen/15"],
              ["Last attempt", counts.borderline, "text-saffron bg-saffron/20"],
              ["Verify these", counts.manual, "text-ink bg-cream"],
              ["Not eligible", counts.ineligible, "text-alert bg-alert/10"],
            ].map(([label, n, cls]) => (
              <div key={label as string} className={`px-4 py-3 ${cls}`}>
                <p className="font-ui text-[26px] font-extrabold tabular-nums leading-none">
                  {n}
                </p>
                <p className="mt-1 text-[12px] font-semibold text-ink/70">{label}</p>
              </div>
            ))}
          </div>

          {(result.eligible_now.length > 0 || result.borderline_last_chance.length > 0) && (
            <>
              <p className="text-[11px] font-bold tracking-[.16em] text-ink/55 uppercase">
                Eligible examinations
              </p>
              <div className="space-y-2">
                {[...result.eligible_now, ...result.borderline_last_chance].map((r) => (
                  <div key={r.exam_id} className="relative">
                    {r.is_last_attempt_age && (
                      <span className="absolute right-3 top-2 rounded bg-saffron px-1.5 py-0.5 text-[10.5px] font-extrabold tracking-wide text-white">
                        LAST ATTEMPT
                      </span>
                    )}
                    <ResultRow r={r} tone="ok" />
                  </div>
                ))}
              </div>
            </>
          )}

          {result.check_manually.length > 0 && (
            <>
              <p className="text-[11px] font-bold tracking-[.16em] text-saffron uppercase">
                Verify against the notification
              </p>
              <div className="space-y-2">
                {result.check_manually.map((r) => (
                  <ResultRow key={r.exam_id} r={r} tone="warn" />
                ))}
              </div>
            </>
          )}

          {result.ineligible.length > 0 && (
            <details className="border border-line">
              <summary className="cursor-pointer px-4 py-3 text-[14px] font-bold text-ink/70">
                Not eligible ({result.ineligible.length}) — see reasons
              </summary>
              <div className="space-y-2 border-t border-line p-3">
                {result.ineligible.map((r) => (
                  <ResultRow key={r.exam_id} r={r} tone="bad" />
                ))}
              </div>
            </details>
          )}

          {!user && (
            <div className="flex flex-wrap items-center justify-between gap-3 border-2 border-dashed border-saffron/50 bg-saffron/5 px-4 py-3">
              <p className="text-[13.5px] font-semibold text-ink/80">
                Sign in to save this profile — it follows you across devices.
              </p>
              <button
                onClick={() => promptSignIn("login")}
                className="h-10 rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white hover:opacity-90"
              >
                Sign in
              </button>
            </div>
          )}
        </div>
      )}
    </PageShell>
  );
}

/* ------------------------------------------------------------------ */
/* My Roadmap                                                          */
/* ------------------------------------------------------------------ */

export function RoadmapPage() {
  const { user, promptSignIn } = useAuth();
  const [exams, setExams] = useState<{ id: string; title: string }[] | null>(null);
  const [examId, setExamId] = useState("");
  const [weeks, setWeeks] = useState(12);
  const [roadmap, setRoadmap] = useState<SavedRoadmap | null>(null);
  const [loadingRoadmap, setLoadingRoadmap] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [done, setDone] = useState<number[]>([]);
  const [mastery, setMastery] = useState<TopicMasteryItem[]>([]);

  useEffect(() => {
    api
      .getExams()
      .then((r) => {
        const slim = r.exams
          .filter((e) => e.is_active)
          .map((e) => ({ id: e.id, title: e.title }));
        setExams(slim);
        setExamId((cur) => cur || slim[0]?.id || "");
      })
      .catch(() => setExams([]));
  }, []);

  useEffect(() => {
    if (!user || !examId) return;
    setLoadingRoadmap(true);
    api
      .getMyRoadmap(examId)
      .then((r) => {
        setRoadmap(r);
        setDone(r?.completed_weeks ?? []);
        if (r) {
          api
            .fetchUserMastery(examId)
            .then((m) => setMastery(m.topics.slice(0, 8)))
            .catch(() => setMastery([]));
        } else {
          setMastery([]);
        }
      })
      .catch(() => {
        setRoadmap(null);
        setDone([]);
      })
      .finally(() => setLoadingRoadmap(false));
  }, [user, examId]);

  const generate = async () => {
    if (!examId) return;
    setGenerating(true);
    setGenError(null);
    try {
      await api.generateRoadmap(examId, weeks);
      const saved = await api.getMyRoadmap(examId);
      setRoadmap(saved);
      setDone(saved?.completed_weeks ?? []);
      toast("success", "Roadmap ready", `${weeks}-week plan generated and saved.`);
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Could not generate the roadmap.");
    } finally {
      setGenerating(false);
    }
  };

  const toggleWeek = async (weekNumber: number) => {
    if (!roadmap) return;
    const nowDone = !done.includes(weekNumber);
    setDone((d) => (nowDone ? [...d, weekNumber] : d.filter((x) => x !== weekNumber)));
    try {
      const prog = await api.toggleRoadmapWeek(
        roadmap.roadmap_id,
        weekNumber,
        nowDone,
      );
      setDone(prog.completed_weeks);
    } catch (err) {
      setDone((d) => (nowDone ? d.filter((x) => x !== weekNumber) : [...d, weekNumber]));
      toast("warn", "Could not save", err instanceof Error ? err.message : "Try again.");
    }
  };

  if (!user) {
    return (
      <PageShell
        kicker="My Roadmap"
        title="Your week-by-week plan"
        subtitle="Sign in to generate and track a personalised study plan."
      >
        <div className="flex flex-col items-center gap-4 py-10 text-center">
          <p className="max-w-md text-[14.5px] text-ink/65">
            A week-by-week AI plan for your target exam — saved to your account,
            with progress tracking and mastery badges.
          </p>
          <button
            onClick={() => promptSignIn("login")}
            className="h-12 rounded-lg bg-saffron px-6 text-[15px] font-bold text-white"
          >
            Sign in to build your roadmap
          </button>
        </div>
      </PageShell>
    );
  }

  const pct =
    roadmap && roadmap.roadmap.weekly_breakdown.length > 0
      ? Math.round((done.length / roadmap.roadmap.weekly_breakdown.length) * 100)
      : 0;

  return (
    <PageShell
      kicker="My Roadmap"
      title="Your week-by-week preparation"
      subtitle={
        roadmap
          ? `${done.length} of ${roadmap.roadmap.weekly_breakdown.length} weeks complete · ${roadmap.roadmap.exam_name}`
          : "Pick your target exam — the plan is generated and saved to your account."
      }
    >
      {/* controls */}
      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-[14px] font-semibold text-ink">
          Target exam
          <select
            value={examId}
            onChange={(e) => setExamId(e.target.value)}
            className="h-11 max-w-[280px] rounded-lg border-2 border-line bg-white px-3 text-[13.5px] outline-none focus:border-saffron"
          >
            {exams === null && <option value="">Loading…</option>}
            {exams?.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title.length > 60 ? `${e.title.slice(0, 60)}…` : e.title}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-1.5" role="group" aria-label="Plan length">
          {[8, 12, 16, 24].map((w) => (
            <button
              key={w}
              onClick={() => setWeeks(w)}
              aria-pressed={weeks === w}
              className={`h-11 rounded-lg border-2 px-4 text-[14px] font-bold transition-colors ${
                weeks === w
                  ? "border-ink bg-ink text-white"
                  : "border-line bg-white hover:border-line-strong"
              }`}
            >
              {w}w
            </button>
          ))}
        </div>

        <button
          onClick={generate}
          disabled={generating || !examId}
          className="h-11 rounded-lg bg-saffron px-5 text-[14px] font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
        >
          {generating
            ? "Generating…"
            : roadmap
              ? `Regenerate ${weeks}-week plan`
              : `Generate ${weeks}-week plan`}
        </button>
      </div>

      {genError && (
        <p role="alert" className="mt-3 rounded-lg border border-alert/40 bg-alert/10 px-4 py-2 text-[13.5px] font-medium text-alert">
          {genError}
        </p>
      )}

      {/* saved roadmap */}
      {loadingRoadmap && (
        <div className="mt-5 animate-pulse space-y-3">
          <div className="h-16 rounded-lg bg-cream" />
          <div className="h-16 rounded-lg bg-cream" />
          <div className="h-16 rounded-lg bg-cream" />
        </div>
      )}

      {!loadingRoadmap && roadmap && (
        <>
          <div className="mt-5 flex flex-wrap items-center gap-4 border border-line bg-cream/50 px-4 py-3">
            <div className="flex-1">
              <div className="h-3 w-full max-w-xs overflow-hidden rounded-full bg-cream">
                <div
                  className="h-full rounded-full bg-govgreen transition-[width] duration-300"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
            <p className="font-ui text-[18px] font-extrabold tabular-nums text-ink">{pct}%</p>
            <p className="text-[12.5px] text-ink/55">
              {roadmap.completed_count ?? done.length} of {roadmap.target_weeks} weeks done
            </p>
          </div>

          {mastery.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">
                Mastery
              </span>
              {mastery.map((m) => (
                <span
                  key={m.topic}
                  title={`${Math.round(m.accuracy_ema * 100)}% EMA · ${m.attempts_count} attempts`}
                  className={`rounded px-2 py-1 text-[12px] font-semibold ${
                    m.status === "Mastered"
                      ? "bg-govgreen/15 text-govgreen"
                      : m.status === "Moderate"
                        ? "bg-saffron/20 text-saffron"
                        : "bg-alert/10 text-alert"
                  }`}
                >
                  {m.topic}
                </span>
              ))}
            </div>
          )}

          <div className="mt-4 space-y-2">
            {roadmap.roadmap.weekly_breakdown.map((week) => {
              const isDone = done.includes(week.week_number);
              return (
                <button
                  key={week.week_number}
                  onClick={() => toggleWeek(week.week_number)}
                  aria-pressed={isDone}
                  className={`flex w-full items-start gap-4 border px-4 py-3 text-left transition-colors ${
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
                    {isDone ? "✓" : week.week_number}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-3">
                      <p className="text-[15px] font-bold text-ink">Week {week.week_number}</p>
                      <p className="text-[12.5px] font-semibold text-saffron">{week.phase}</p>
                    </div>
                    <p className="mt-0.5 text-[14.5px] font-semibold text-ink">
                      {week.focus_subject}
                    </p>
                    {week.topics.length > 0 && (
                      <p className="mt-1 text-[13px] text-ink/65">
                        {week.topics.join(" · ")}
                      </p>
                    )}
                    {week.practice_goal && (
                      <p className="mt-0.5 text-[12.5px] text-ink/55">
                        Goal: {week.practice_goal}
                      </p>
                    )}
                  </div>
                  <span className="shrink-0 text-[11.5px] font-bold tabular-nums text-ink/45">
                    {isDone ? "DONE" : "PENDING"}
                  </span>
                </button>
              );
            })}
          </div>

          {roadmap.roadmap.revision_strategy && (
            <p className="mt-4 border-l-2 border-saffron bg-cream/60 px-4 py-3 text-[13px] text-ink/70">
              <span className="font-bold">Revision strategy: </span>
              {roadmap.roadmap.revision_strategy}
            </p>
          )}
        </>
      )}

      {!loadingRoadmap && !roadmap && !genError && (
        <div className="mt-6 border border-dashed border-line-strong px-4 py-8 text-center">
          <p className="text-[15px] font-bold text-ink">No plan yet for this exam</p>
          <p className="mt-1 text-[13.5px] text-ink/60">
            Pick a target exam and a length, then hit Generate. It's saved to your account.
          </p>
        </div>
      )}
    </PageShell>
  );
}
