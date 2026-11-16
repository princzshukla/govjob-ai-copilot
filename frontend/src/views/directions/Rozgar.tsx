import { useEffect, useMemo, useState, type ReactNode } from "react";
import { STATES, toFeedExam, type FeedExam } from "../../lib/exams";
import { getExams } from "../../lib/api";
import { loadEligibilityResult, saveEligibilityResult } from "../../lib/draft";
import { useAuth } from "../../lib/auth";
import type { EligibilityCheckResponse } from "../../types";
import { ADS_ENABLED, AD_FREQUENCY, SPONSORED_JOBS, type AdLayout } from "../../lib/ads";
import { JobCard, SponsoredJobCard } from "../../components/rozgar/JobCard";
import { AdSlot } from "../../components/rozgar/AdSlot";
import { AccountModal } from "../../components/rozgar/AccountModal";
import { DocumentResizer } from "../../components/rozgar/DocumentResizer";
import { EligibilityPage, RoadmapPage } from "./rozgar-pages";

const NAV = [
  { label: "Latest Jobs" },
  { label: "My Eligibility" },
  { label: "My Roadmap" },
  { label: "Photo & Signature" },
] as const;

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
    <header className="border-b border-line bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 py-4 sm:px-5">
        <div className="flex items-center justify-between gap-3">
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
              <p className="mt-1 text-[11px] text-ink/60 sm:text-[12px]">
                सरकारी नौकरी · Eligibility check · Free
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {loading ? (
              <div className="h-9 w-40 animate-pulse rounded-lg bg-cream sm:h-11" aria-hidden="true" />
            ) : user ? (
              <button
                onClick={() => setAccountOpen(true)}
                className="h-9 rounded-lg bg-ink px-3 text-[13.5px] font-semibold text-white sm:h-11 sm:px-4 sm:text-[14.5px]"
              >
                {user.full_name ? `Hi, ${user.full_name.split(" ")[0]}` : "My account"}
              </button>
            ) : (
              <>
                <button
                  onClick={() => promptSignIn("register")}
                  className="h-9 rounded-lg border-2 border-line bg-white px-3 text-[13.5px] font-semibold text-ink transition-colors hover:border-line-strong sm:h-11 sm:px-4 sm:text-[14.5px]"
                >
                  Register
                </button>
                <button
                  onClick={() => promptSignIn("login")}
                  className="h-9 rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white shadow-[0_2px_0_rgba(0,0,0,.12)] sm:h-11 sm:px-5 sm:text-[14.5px]"
                >
                  Login
                </button>
              </>
            )}
          </div>
          {accountOpen && <AccountModal onClose={() => setAccountOpen(false)} />}
        </div>

        {/* Search — the one action every first-time visitor understands */}
        <form
          className="mt-3 flex items-center gap-2 sm:mt-4"
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
  active: string;
  onSelect: (l: string) => void;
  jobCount: number | null;
}) {
  return (
    <nav className="border-b-2 border-ink bg-paper">
      <div className="mx-auto flex max-w-[1280px] items-stretch overflow-x-auto px-2">
        {NAV.map((item) => {
          const on = active === item.label;
          const count = item.label === "Latest Jobs" ? jobCount : null;
          return (
            <button
              key={item.label}
              onClick={() => onSelect(item.label)}
              aria-current={on ? "page" : undefined}
              className={`relative flex h-[52px] shrink-0 items-center gap-2 px-4 text-[15.5px] font-semibold whitespace-nowrap text-ink/65 transition-colors hover:text-ink sm:px-5 sm:text-[16.5px] ${
                on ? "text-ink" : ""
              }`}
            >
              {item.label}
              {count !== null && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[11.5px] font-bold tabular-nums ${
                    on ? "bg-saffron text-white" : "bg-cream text-ink/70"
                  }`}
                >
                  {count}
                </span>
              )}
              {on && (
                <span className="absolute inset-x-3 bottom-0 h-[3px] rounded-t bg-saffron" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/** One line of trust copy — the only “hero” this portal gets. */
function TrustLine() {
  return (
    <div className="border-b border-line bg-cream">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 text-[12px] text-ink/75 sm:px-5 sm:text-[12.5px]">
        <span className="flex items-center gap-1.5">
          <span className="size-1.5 rounded-full bg-govgreen" aria-hidden="true" />
          Sourced from official notifications
        </span>
        <span className="hidden text-line-strong sm:inline">|</span>
        <span>Updated daily</span>
        <span className="hidden text-line-strong sm:inline">|</span>
        <span>Official PDF linked on every job</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

const selectClass =
  "h-11 rounded-lg border-2 border-line bg-white px-3 text-[14px] font-medium text-ink outline-none focus:border-saffron";

function FilterBar({
  state,
  setState,
  resultCount,
  totalCount,
  onReset,
  dirty,
}: {
  state: string;
  setState: (s: string) => void;
  resultCount: number;
  totalCount: number;
  onReset: () => void;
  dirty: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2.5 sm:gap-3">
      <label className="flex items-center gap-2">
        <span className="font-mono text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">
          State
        </span>
        <select
          value={state}
          onChange={(e) => setState(e.target.value)}
          className={selectClass}
          aria-label="Filter by state"
        >
          {STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>

      <span className="ml-auto flex items-center gap-3">
        <p className="whitespace-nowrap text-[13.5px] tabular-nums text-ink/60">
          <span className="font-bold text-ink">{resultCount}</span> of{" "}
          <span>{totalCount}</span>
        </p>
        {dirty && (
          <button
            type="button"
            onClick={onReset}
            className="whitespace-nowrap text-[13px] font-bold text-saffron hover:underline"
          >
            Reset
          </button>
        )}
      </span>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading notifications">
      {[0, 1, 2].map((i) => (
        <div key={i} className="animate-pulse rounded-lg border border-line bg-white px-5 py-4">
          <div className="h-4 w-40 rounded bg-cream" />
          <div className="mt-3 h-5 w-3/4 rounded bg-cream" />
          <div className="mt-2 h-4 w-1/3 rounded bg-cream" />
          <div className="mt-3 flex gap-1.5">
            <div className="h-6 w-24 rounded bg-cream" />
            <div className="h-6 w-20 rounded bg-cream" />
            <div className="h-6 w-16 rounded bg-cream" />
          </div>
          <div className="mt-4 h-[5px] w-full rounded-full bg-cream" />
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */

export function Rozgar({ adLayout }: { adLayout: AdLayout }) {
  const [active, setActive] = useState<(typeof NAV)[number]["label"]>("Latest Jobs");
  const [state, setState] = useState("All India");
  const [query, setQuery] = useState("");

  const [exams, setExams] = useState<FeedExam[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Free once a profile is set — eligibility verdicts for every notification,
  // per the approved plan. Cached in sessionStorage so tab switches keep them.
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
        setLoadError(
          err instanceof Error ? err.message : "Could not load notifications.",
        );
        setExams(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [retryCount]);

  const filtered = useMemo(() => {
    if (!exams) return [];
    return exams.filter((e) => {
      // An "All India" notification survives a state filter; a state-specific one does not.
      if (state !== "All India" && e.state !== state && e.state !== "All India")
        return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        const hay =
          `${e.title} ${e.department} ${e.postType} ${e.degrees.join(" ")} ${e.topics.join(" ")}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [exams, state, query]);

  const dirty = state !== "All India" || query !== "";
  const resetFilters = () => {
    setState("All India");
    setQuery("");
  };

  const closingSoon = useMemo(
    () =>
      (exams ?? [])
        .filter((e) => e.deadlineDays > 0 && e.deadlineDays <= 10)
        .sort((a, b) => a.deadlineDays - b.deadlineDays)
        .slice(0, 3),
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

  if (active !== "Latest Jobs") {
    return (
      <div className="min-h-screen bg-paper text-ink">
        <Masthead query={query} onQueryChange={setQuery} />
        <MainNav active={active} onSelect={(l) => setActive(l as typeof active)} jobCount={exams?.length ?? null} />
        <TrustLine />
        <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
          {active === "My Eligibility" && (
            <EligibilityPage result={eligibility} onResultChange={setAndCacheEligibility} />
          )}
          {active === "My Roadmap" && <RoadmapPage />}
          {active === "Photo & Signature" && <DocumentResizer />}
        </div>
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper text-ink">
      <Masthead query={query} onQueryChange={setQuery} />
      <MainNav active={active} onSelect={(l) => setActive(l as typeof active)} jobCount={exams?.length ?? null} />
      <TrustLine />

      {/* Filters — state and search (search lives in the masthead), one dropdown */}
      <div className="sticky top-0 z-30 border-b border-line bg-paper">
        <div className="mx-auto max-w-[1280px] px-4 sm:px-5">
          <FilterBar
            state={state}
            setState={setState}
            resultCount={filtered.length}
            totalCount={exams?.length ?? 0}
            onReset={resetFilters}
            dirty={dirty}
          />
        </div>
      </div>

      <div
        className={`mx-auto grid max-w-[1280px] gap-6 px-4 py-6 sm:px-5 ${
          ADS_ENABLED ? "lg:grid-cols-[288px_1fr_288px]" : "lg:grid-cols-[1fr_320px]"
        }`}
      >
        {/* LEFT RAIL — ad inventory, nothing else. Only exists with the ad system on. */}
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

        {/* job list — first on mobile */}
        <main id="job-results" className="order-1 lg:order-none">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-[19px] font-extrabold text-ink">
              Latest Jobs
              {exams && (
                <span className="rounded-full bg-saffron px-2 py-0.5 text-[12.5px] font-bold tabular-nums text-white">
                  {filtered.length}
                </span>
              )}
            </h2>
          </div>

          <div className="space-y-2.5">
            {exams === null && !loadError ? (
              <LoadingSkeleton />
            ) : loadError ? (
              <div className="rounded-lg border border-line bg-white px-5 py-14 text-center">
                <p className="text-[17px] font-bold text-ink">
                  Couldn't load notifications
                </p>
                <p className="mt-1 text-[14.5px] text-ink/60">{loadError}</p>
                <button
                  onClick={() => setRetryCount((c) => c + 1)}
                  className="mt-4 h-10 rounded-lg bg-ink px-4 text-[14px] font-bold text-white hover:bg-saffron"
                >
                  Try again
                </button>
              </div>
            ) : filtered.length === 0 ? (
              <div className="rounded-lg border border-line bg-white px-5 py-14 text-center">
                <p className="text-[17px] font-bold text-ink">No matching notifications</p>
                <p className="mt-1 text-[14.5px] text-ink/60">
                  Try widening the state filter or clearing the search.
                </p>
              </div>
            ) : (
              feed
            )}
          </div>

          {exams && (
            <p className="mt-3 text-[13.5px] tabular-nums text-ink/60">
              Showing {filtered.length} of {exams.length} notifications
            </p>
          )}
        </main>

        {/* RIGHT RAIL — Closing Soon + ads above any content heading */}
        <aside className="order-3 space-y-4">
          {ADS_ENABLED &&
            adLayout.rightOrder === "ads-first" &&
            adLayout.right.map((ad) => (
              <div
                key={ad.id}
                className="mx-auto w-full max-w-[300px] overflow-hidden rounded-lg border border-dashed border-line-strong bg-white/60 sm:max-w-none"
              >
                <AdSlot {...ad} className="border-0" />
              </div>
            ))}

          <div className="overflow-hidden rounded-lg border border-line">
            <p className="border-b border-line bg-cream px-4 py-2.5 text-[13px] font-bold tracking-[.1em] text-ink uppercase">
              Closing Soon
            </p>
            <div className="space-y-3 bg-white px-4 py-3.5">
              {closingSoon.length === 0 && (
                <p className="text-[13.5px] text-ink/55">
                  Nothing closes in the next 10 days.
                </p>
              )}
              {closingSoon.map((e) => (
                <div key={e.id}>
                  <p className="text-[14px] font-semibold leading-snug text-ink">{e.title}</p>
                  <div className="mt-1.5 flex items-center gap-2">
                    <div className="h-[5px] flex-1 overflow-hidden rounded-full bg-cream">
                      <div
                        className={`h-full rounded-full ${
                          e.deadlineDays <= 7 ? "bg-alert" : "bg-saffron"
                        }`}
                        style={{ width: `${Math.max(8, (e.deadlineDays / 45) * 100)}%` }}
                      />
                    </div>
                    <span className="text-[13px] font-bold tabular-nums text-alert">
                      {e.deadlineDays}d
                    </span>
                  </div>
                </div>
              ))}
            </div>
            {closingSoon.length > 0 && (
              <p className="border-t border-line bg-cream px-4 py-2 text-[13px] text-ink/70">
                {closingSoon.length} notification{closingSoon.length === 1 ? "" : "s"} close
                within 10 days
              </p>
            )}
          </div>

          {ADS_ENABLED &&
            adLayout.rightOrder === "ads-last" &&
            adLayout.right.map((ad) => (
              <div
                key={ad.id}
                className="mx-auto w-full max-w-[300px] overflow-hidden rounded-lg border border-dashed border-line-strong bg-white/60 sm:max-w-none"
              >
                <AdSlot {...ad} className="border-0" />
              </div>
            ))}
        </aside>
      </div>

      <SiteFooter />
    </div>
  );
}

function SiteFooter() {
  return (
    <footer className="mt-10 border-t border-line bg-cream">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-[13px] text-ink/70 sm:px-5">
        <p>
          <span className="font-bold text-ink">RozgarBoard</span> · Government job
          notifications, structured daily
        </p>
        <p>Data sourced from official notifications</p>
      </div>
    </footer>
  );
}
