import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { toFeedExam, type FeedExam } from "../../lib/exams";
import { getExams } from "../../lib/api";
import { loadEligibilityResult, saveEligibilityResult } from "../../lib/draft";
import { useAuth } from "../../lib/auth";
import type { EligibilityCheckResponse } from "../../types";
import { ADS_ENABLED, AD_FREQUENCY, SPONSORED_JOBS, type AdLayout } from "../../lib/ads";
import { JobCard, SponsoredJobCard } from "../../components/rozgar/JobCard";
import { AdSlot } from "../../components/rozgar/AdSlot";
import { AccountModal } from "../../components/rozgar/AccountModal";
import { DocumentResizer } from "../../components/rozgar/DocumentResizer";
import { Footer } from "../../components/rozgar/Footer";
import { EligibilityPage, RoadmapPage } from "./rozgar-pages";

const NAV = [
  { label: "Latest Jobs" },
  { label: "My Eligibility" },
  { label: "My Roadmap" },
  { label: "Photo & Signature" },
] as const;

type Tab = (typeof NAV)[number]["label"];

/* ------------------------------------------------------------------ */

function Masthead({
  query,
  onQueryChange,
}: {
  query: string;
  onQueryChange: (v: string) => void;
}) {
  const { user, loading, promptSignIn } = useAuth();
  const [accountOpen, setAccountOpen] = useState(false);

  return (
    <header className="bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 py-3 sm:px-5 sm:py-3.5">
        <div className="flex items-center justify-between gap-3">
          {/* wordmark + tagline */}
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-1.5 flex-col overflow-hidden rounded-full sm:h-11" aria-hidden="true">
              <span className="flex-1 bg-saffron" />
              <span className="flex-1 bg-white" />
              <span className="flex-1 bg-govgreen" />
            </div>
            <div>
              <p className="flex items-center gap-2 text-[18px] leading-none font-extrabold tracking-tight text-ink sm:text-[22px]">
                Rozgar<span className="text-saffron">Board</span>
              </p>
              <p className="mt-1 text-[10.5px] font-semibold tracking-[.14em] text-ink/55 uppercase">
                sarkari naukri, structured
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {loading ? (
              <div className="h-9 w-28 animate-pulse rounded-lg bg-cream sm:h-11" aria-hidden="true" />
            ) : user ? (
              <button
                onClick={() => setAccountOpen(true)}
                className="h-9 rounded-lg bg-ink px-3 text-[13.5px] font-semibold text-white sm:h-11 sm:px-4 sm:text-[14.5px]"
              >
                {user.full_name ? `Hi, ${user.full_name.split(" ")[0]}` : "My account"}
              </button>
            ) : (
              <button
                onClick={() => promptSignIn("login")}
                className="h-9 rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white sm:h-11 sm:px-5 sm:text-[14.5px]"
              >
                Login
              </button>
            )}
          </div>
          {accountOpen && <AccountModal onClose={() => setAccountOpen(false)} />}
        </div>

        {/* Search — the one action every first-time visitor understands */}
        <form
          className="mt-2 flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            document
              .getElementById("job-results")
              ?.scrollIntoView({ behavior: "smooth", block: "start" });
          }}
        >
          <label htmlFor="job-search" className="sr-only">
            Search jobs
          </label>
          <div className="relative flex-1">
            <input
              id="job-search"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Search exam, post or department — e.g. SSC CHSL"
              className="h-11 w-full rounded-lg border-2 border-line bg-white px-4 text-[14.5px] text-ink outline-none placeholder:text-ink/45 focus:border-saffron sm:h-12 sm:text-[15px]"
            />
            {query && (
              <button
                type="button"
                onClick={() => onQueryChange("")}
                aria-label="Clear search"
                className="absolute right-[104px] top-1/2 grid size-7 -translate-y-1/2 place-items-center rounded-full text-ink/45 hover:bg-cream hover:text-ink"
              >
                ✕
              </button>
            )}
            <button
              type="submit"
              className="absolute right-1.5 top-1/2 h-8 -translate-y-1/2 rounded-md bg-ink px-3 text-[13px] font-semibold text-white hover:bg-saffron sm:h-9 sm:px-4 sm:text-[14px]"
            >
              Search
            </button>
          </div>
        </form>
      </div>
    </header>
  );
}

function MainNav({
  active,
  onSelect,
  jobCount,
}: {
  active: Tab;
  onSelect: (l: Tab) => void;
  jobCount: number | null;
}) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [indicator, setIndicator] = useState<{ left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    const el = trackRef.current?.querySelector<HTMLElement>('[data-active="true"]');
    setIndicator(el ? { left: el.offsetLeft, width: el.offsetWidth } : null);
  }, [active, jobCount]);

  return (
    <nav className="border-b-2 border-ink bg-paper" aria-label="Primary">
      <div
        ref={trackRef}
        className="relative mx-auto flex max-w-[1280px] items-stretch overflow-x-auto px-2"
      >
        {NAV.map((item) => {
          const on = active === item.label;
          const count = item.label === "Latest Jobs" ? jobCount : null;
          return (
            <button
              key={item.label}
              data-active={on ? "true" : undefined}
              onClick={() => onSelect(item.label)}
              aria-current={on ? "page" : undefined}
              className={`relative flex h-[52px] shrink-0 items-center gap-2 px-4 text-[15px] font-semibold whitespace-nowrap text-ink/65 transition-colors hover:text-ink sm:px-5 sm:text-[16px] ${
                on ? "text-ink" : ""
              }`}
            >
              {item.label}
              {count !== null && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-bold tabular-nums ${
                    on ? "bg-saffron text-white" : "bg-cream text-ink/70"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
        {/* one roving underline — animates between tabs with in/out slide */}
        {indicator && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 h-[3px] rounded-t bg-saffron transition-all duration-300 ease-out"
            style={{ left: indicator.left, width: indicator.width }}
          />
        )}
      </div>
    </nav>
  );
}

/** Editorial masthead block: kicker, one confident headline, muted sub, stat strip. */
function HeroBand({
  total,
  closingThisWeek,
}: {
  total: number | null;
  closingThisWeek: number | null;
}) {
  if (total === null) return null; // during load the skeleton handles the space
  return (
    <section className="border-b border-line bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 pt-8 pb-7 sm:px-5 sm:pt-10 sm:pb-8">
        <p className="font-mono text-[11px] font-bold tracking-[.18em] text-saffron uppercase">
          sarkari naukri · official notifications
        </p>
        <h1 className="mt-2 max-w-3xl text-[34px] font-extrabold leading-[1.08] tracking-tight text-ink sm:text-[46px]">
          Government jobs, <span className="text-saffron">without the noise.</span>
        </h1>
        <p className="mt-3 max-w-xl text-[15.5px] leading-relaxed text-ink/65">
          Every notification linked to its official PDF. Eligibility in seconds,
          one place to everything that's live.
        </p>
        <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-line pt-4 font-mono text-[12.5px] tabular-nums text-ink/70">
          <span>
            <span className="font-extrabold text-ink">{total}</span> notifications live
          </span>
          <span aria-hidden="true" className="hidden text-line-strong sm:inline">|</span>
          <span>
            <span className="font-extrabold text-ink">{closingThisWeek ?? 0}</span> closing this week
          </span>
          <span aria-hidden="true" className="hidden text-line-strong sm:inline">|</span>
          <span>
            <span className="font-extrabold text-govgreen">✓</span> updated today
          </span>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */

function LoadingSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading notifications">
      {[0, 1, 2].map((i) => (
        <div key={i} className="animate-pulse rounded-lg border border-line bg-[#fbfaf7] px-5 py-4">
          <div className="h-4 w-40 rounded bg-cream" />
          <div className="mt-3 h-5 w-3/4 rounded bg-cream" />
          <div className="mt-2 h-4 w-1/3 rounded bg-cream" />
          <div className="mt-3 flex gap-1.5">
            <div className="h-6 w-24 rounded bg-cream" />
            <div className="h-6 w-20 rounded bg-cream" />
            <div className="h-6 w-16 rounded bg-cream" />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */

export function Rozgar({ adLayout }: { adLayout: AdLayout }) {
  const [active, setActive] = useState<Tab>("Latest Jobs");
  const [query, setQuery] = useState("");

  const [exams, setExams] = useState<FeedExam[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Free once a profile is set — eligibility verdicts for every notification.
  // Cached in sessionStorage so tab switches keep them.
  const [eligibility, setEligibility] = useState<EligibilityCheckResponse | null>(
    () => loadEligibilityResult(),
  );
  const setAndCacheEligibility = (r: EligibilityCheckResponse | null) => {
    setEligibility(r);
    if (r) saveEligibilityResult(r);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadError(null);
      try {
        const res = await getExams();
        if (cancelled) return;
        setExams(res.exams.filter((e) => e.is_active).map(toFeedExam));
      } catch (err) {
        if (cancelled) return;
        setLoadError(err instanceof Error ? err.message : "Could not load notifications.");
        setExams(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [retryCount]);

  const filtered = useMemo(() => {
    if (!exams) return [];
    if (!query.trim()) return exams;
    const q = query.toLowerCase();
    return exams.filter((e) => {
      const hay =
        `${e.title} ${e.department} ${e.postType} ${e.degrees.join(" ")} ${e.topics.join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
  }, [exams, query]);

  const closingSoon = useMemo(
    () =>
      (exams ?? [])
        .filter((e) => e.deadlineDays > 0 && e.deadlineDays <= 10)
        .sort((a, b) => a.deadlineDays - b.deadlineDays)
        .slice(0, 5),
    [exams],
  );

  const closingThisWeek = useMemo(
    () => (exams ?? []).filter((e) => e.deadlineDays > 0 && e.deadlineDays <= 7).length,
    [exams],
  );

  // Verdict map for the feed: every exam evaluated by the eligibility check.
  const verdicts = useMemo(() => {
    const map = new Map<string, "eligible" | "borderline" | "check" | "ineligible">();
    if (!eligibility) return map;
    eligibility.eligible_now.forEach((r) => map.set(r.exam_id, "eligible"));
    eligibility.borderline_last_chance.forEach((r) => map.set(r.exam_id, "borderline"));
    eligibility.check_manually.forEach((r) => map.set(r.exam_id, "check"));
    eligibility.ineligible.forEach((r) => map.set(r.exam_id, "ineligible"));
    return map;
  }, [eligibility]);

  // Feed assembly: the only in-feed ad is a sponsored placement, injected by a
  // hard frequency cap — only when the ad system is enabled.
  const feed = useMemo(() => {
    const items: ReactNode[] = [];
    filtered.forEach((exam, i) => {
      if (ADS_ENABLED && i > 0 && i % AD_FREQUENCY === 0) {
        const sp = SPONSORED_JOBS[(i / AD_FREQUENCY - 1) % SPONSORED_JOBS.length];
        items.push(<SponsoredJobCard key={`sp-${sp.id}`} job={sp} />);
      }
      items.push(<JobCard key={exam.id} exam={exam} verdict={verdicts.get(exam.id) ?? null} />);
    });
    return items;
  }, [filtered, verdicts]);

  const goTab = (tab: Tab) => {
    setActive(tab);
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Masthead query={query} onQueryChange={setQuery} />
      <MainNav active={active} onSelect={goTab} jobCount={exams?.length ?? null} />
      {active === "Latest Jobs" && (
        <HeroBand total={exams?.length ?? null} closingThisWeek={closingThisWeek} />
      )}

      <div key={active} className="animate-[tab-in_.35s_ease-out]">
        {active === "Latest Jobs" && (
          <div className={`mx-auto grid max-w-[1280px] gap-6 px-4 py-6 sm:px-5 ${ADS_ENABLED ? "lg:grid-cols-[288px_1fr_288px]" : "lg:grid-cols-[1fr_340px]"}`}>
            {/* LEFT RAIL — ad inventory, only with the ad system on */}
            {ADS_ENABLED && (
              <div className="order-2 space-y-4 lg:order-none">
                {adLayout.left.map((ad) => (
                  <div
                    key={ad.id}
                    className="mx-auto w-full max-w-[300px] overflow-hidden rounded-lg border border-dashed border-line-strong bg-white/60 sm:max-w-none"
                  >
                    <AdSlot {...ad} className="border-0" />
                  </div>
                ))}
              </div>
            )}

            {/* job list */}
            <main id="job-results" className="order-1 lg:order-none">
              <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="flex items-baseline gap-2 text-[22px] font-extrabold tracking-tight text-ink">
                  Latest Jobs
                  {exams && (
                    <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-white">
                      {filtered.length}
                    </span>
                  )}
                </h2>
                <p className="text-[12px] font-semibold tracking-wide text-ink/55 uppercase">
                  Official sources only
                </p>
              </div>

              <div className="space-y-2.5">
                {exams === null && !loadError ? (
                  <LoadingSkeleton />
                ) : loadError ? (
                  <div className="rounded-lg border border-line bg-[#fbfaf7] px-5 py-14 text-center">
                    <p className="text-[17px] font-bold text-ink">Couldn't load notifications</p>
                    <p className="mt-1 text-[14px] text-ink/60">{loadError}</p>
                    <button
                      onClick={() => setRetryCount((c) => c + 1)}
                      className="mt-4 h-11 rounded-lg bg-ink px-4 text-[13.5px] font-bold text-white hover:bg-saffron"
                    >
                      Try again
                    </button>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="rounded-lg border border-line bg-[#fbfaf7] px-5 py-14 text-center">
                    <p className="text-[17px] font-bold text-ink">No matching notifications</p>
                    <p className="mt-1 text-[14px] text-ink/60">Try clearing the search.</p>
                  </div>
                ) : (
                  feed
                )}
              </div>
            </main>

            {/* RIGHT RAIL — Closing Soon, aligned with the feed */}
            <aside className="order-3 self-start lg:sticky lg:top-4">
              <div className="mb-4 flex items-baseline justify-between gap-3">
                <p className="flex items-baseline gap-2 text-[22px] font-extrabold tracking-tight text-ink">
                  Closing Soon
                  {closingSoon.length > 0 && (
                    <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-white">
                      {closingSoon.length}
                    </span>
                  )}
                </p>
                <p className="text-[12px] font-semibold tracking-wide text-ink/55 uppercase">Next 10 days</p>
              </div>

              <div className="space-y-2.5">
                {closingSoon.length === 0 && (
                  <div className="rounded-lg border border-line bg-[#fbfaf7] px-4 py-4 text-[13px] text-ink/55">
                    Nothing closes in the next 10 days.
                  </div>
                )}
                {closingSoon.map((e) => (
                  <a
                    key={e.id}
                    href={e.pdfUrl ?? undefined}
                    target={e.pdfUrl ? "_blank" : undefined}
                    rel="noopener noreferrer"
                    className={`block overflow-hidden rounded-lg border border-line bg-[#fbfaf7] px-4 py-3 transition-colors ${
                      e.pdfUrl ? "cursor-pointer hover:border-line-strong" : "cursor-default"
                    }`}
                    title={e.pdfUrl ? "Open the official notification (PDF)" : "Official PDF not linked yet"}
                  >
                    <p className="text-[14px] font-semibold leading-snug text-ink">{e.title}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <div className="h-[5px] flex-1 overflow-hidden rounded-full bg-cream">
                        <div
                          className={`h-full rounded-full ${e.deadlineDays <= 7 ? "bg-alert" : "bg-saffron"}`}
                          style={{ width: `${Math.max(8, (e.deadlineDays / 45) * 100)}%` }}
                        />
                      </div>
                      <span className="text-[12.5px] font-bold tabular-nums text-alert">{e.deadlineDays}d</span>
                      {e.pdfUrl && <span aria-hidden="true" className="text-[11px] text-ink/40">↗</span>}
                    </div>
                  </a>
                ))}
              </div>

              <p className="mt-4 text-[12px] text-ink/60">
                {closingSoon.length} notification{closingSoon.length === 1 ? "" : "s"} close within 10 days
              </p>
            </aside>
          </div>
        )}

        {active === "My Eligibility" && (
          <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
            <EligibilityPage result={eligibility} onResultChange={setAndCacheEligibility} />
          </div>
        )}
        {active === "My Roadmap" && (
          <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
            <RoadmapPage />
          </div>
        )}
        {active === "Photo & Signature" && (
          <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
            <DocumentResizer />
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
}
