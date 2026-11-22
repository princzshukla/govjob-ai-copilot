import {
  Suspense,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import {
  Briefcase,
  FileText,
  ClipboardCheck,
  Map as MapIcon,
  Image as ImageIcon,
  Archive as ArchiveIcon,
  Search as SearchIcon,
} from "lucide-react";
import { toFeedExam, toFeedAdmitCard, type FeedExam, type FeedAdmitCard } from "../../lib/exams";
import { getExams, getAdmitCards } from "../../lib/api";
import { safeUrl } from "../../lib/safeUrl";
import { loadEligibilityResult, saveEligibilityResult } from "../../lib/draft";
import { useAuth } from "../../lib/auth";
import type { EligibilityCheckResponse } from "../../types";
import { PATH_FOR_TAB, type Tab } from "../../routes";
import { getPrerenderData } from "../../lib/prerender-data";
import { ADS_ENABLED, AD_FREQUENCY, SPONSORED_JOBS, type AdLayout } from "../../lib/ads";
import { JobCard, SponsoredJobCard } from "../../components/rozgar/JobCard";
import { AdmitCardCard } from "../../components/rozgar/AdmitCard";
import { AdSlot } from "../../components/rozgar/AdSlot";
import { Footer } from "../../components/rozgar/Footer";

// Eager imports: react-dom/server cannot wait for React.lazy, so these would
// render a "Loading…" fallback into the prerendered HTML. Rollup still splits
// them into separate chunks via manualChunks in vite.config.ts.
import { AccountModal } from "../../components/rozgar/AccountModal";
import { DocumentResizer } from "../../components/rozgar/DocumentResizer";
import { EligibilityPage, RoadmapPage } from "./rozgar-pages";
import { ClosedJobsPage } from "./closed-jobs";

const ChunkFallback = () => (
  <div className="mx-auto max-w-[1280px] px-4 py-10 text-center text-sm text-ink/50 sm:px-5">
    Loading…
  </div>
);

const NAV = [
  { label: "Latest Jobs", param: "jobs" },
  { label: "Admit Cards", param: "admit" },
  { label: "Closed Jobs", param: "closed" },
  { label: "My Eligibility", param: "eligibility" },
  { label: "My Roadmap", param: "roadmap" },
  { label: "Photo & Signature", param: "documents" },
] as const;

const BOTTOM_NAV = [
  { label: "Latest Jobs", short: "Jobs", icon: Briefcase, param: "jobs" },
  { label: "Admit Cards", short: "Admits", icon: FileText, param: "admit" },
  { label: "Closed Jobs", short: "Closed", icon: ArchiveIcon, param: "closed" },
  { label: "My Eligibility", short: "Eligibility", icon: ClipboardCheck, param: "eligibility" },
  { label: "My Roadmap", short: "Roadmap", icon: MapIcon, param: "roadmap" },
  { label: "Photo & Signature", short: "Documents", icon: ImageIcon, param: "documents" },
] as const;

type Chip = "all" | "closing" | "graduate" | "12th" | "10th";

const FILTER_CHIPS: { id: Chip; label: string }[] = [
  { id: "all", label: "All jobs" },
  { id: "closing", label: "Closing soon" },
  { id: "graduate", label: "Graduate" },
  { id: "12th", label: "12th pass" },
  { id: "10th", label: "10th pass" },
];

const MOBILE_PAGE_SIZE = 15;

/* ------------------------------------------------------------------ */

function useScrolled(threshold = 80): boolean {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [threshold]);
  return scrolled;
}

/* ------------------------------------------------------------------ */

function Masthead({
  query,
  onQueryChange,
  compact,
  onExpand,
  onAccount,
}: {
  query: string;
  onQueryChange: (v: string) => void;
  compact: boolean;
  onExpand: () => void;
  onAccount: () => void;
}) {
  const { user, loading, promptSignIn } = useAuth();

  const focusSearch = () => {
    onExpand();
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.setTimeout(() => document.getElementById("job-search")?.focus(), 200);
  };

  return (
    <header className="bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 py-3 sm:px-5 sm:py-5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-1.5 flex-col overflow-hidden rounded-full sm:h-11" aria-hidden="true">
              <span className="flex-1 bg-saffron" />
              <span className="flex-1 bg-white" />
              <span className="flex-1 bg-govgreen" />
            </div>
            <div>
              <p className="flex items-center gap-2 text-[18px] leading-none font-extrabold tracking-tight text-ink sm:text-[22px]">
                Rozgar<span className="text-saffron">Board</span>
              </p>
              <p
                className={`mt-1 text-[10.5px] font-semibold tracking-[.14em] text-ink/55 uppercase ${
                  compact ? "hidden sm:block" : ""
                }`}
              >
                sarkari naukri, structured
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {compact && (
              <button
                onClick={focusSearch}
                aria-label="Search jobs"
                className="grid size-11 place-items-center rounded-lg border-2 border-line bg-white text-ink md:hidden"
              >
                <SearchIcon size={18} aria-hidden="true" />
              </button>
            )}
            {loading ? (
              <div className="h-11 w-28 animate-pulse rounded-lg bg-cream" aria-hidden="true" />
            ) : user ? (
              <button
                onClick={onAccount}
                className="h-11 rounded-lg bg-ink px-3 text-[13.5px] font-semibold text-white sm:px-4 sm:text-[14.5px]"
              >
                {user.full_name ? `Hi, ${user.full_name.split(" ")[0]}` : "My account"}
              </button>
            ) : (
              <button
                onClick={() => promptSignIn("login")}
                className="h-11 rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white sm:px-5 sm:text-[14.5px]"
              >
                Login
              </button>
            )}
          </div>
        </div>

        {/* Search — icon-only on mobile, full field on sm+ */}
        <form
          className={`mt-2 flex items-center gap-2 ${compact ? "hidden sm:flex" : "flex"}`}
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
              className="h-11 w-full rounded-lg border-2 border-line bg-white px-3 pr-12 text-base text-ink outline-none placeholder:text-ink/45 focus:border-saffron sm:h-12 sm:px-4 sm:text-[15px] sm:pr-24"
            />
            {query && (
              <button
                type="button"
                onClick={() => onQueryChange("")}
                aria-label="Clear search"
                className="absolute right-[60px] top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-full text-ink/45 hover:bg-cream hover:text-ink sm:right-[84px]"
              >
                <span aria-hidden="true">✕</span>
              </button>
            )}
            <button
              type="submit"
              aria-label="Search"
              className="absolute right-1.5 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-md bg-ink text-white hover:bg-saffron sm:h-9 sm:w-auto sm:px-4 sm:text-[14px]"
            >
              <SearchIcon size={16} aria-hidden="true" className="sm:hidden" />
              <span className="hidden sm:inline">Search</span>
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
  admitCount,
}: {
  active: Tab;
  onSelect: (l: Tab) => void;
  jobCount: number | null;
  admitCount: number | null;
}) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [indicator, setIndicator] = useState<{ left: number; width: number } | null>(null);

  useLayoutEffect(() => {
    const el = trackRef.current?.querySelector<HTMLElement>('[data-active="true"]');
    setIndicator(el ? { left: el.offsetLeft, width: el.offsetWidth } : null);
  }, [active, jobCount, admitCount]);

  return (
    <nav className="hidden border-t border-line bg-paper md:block" aria-label="Primary">
      <div
        ref={trackRef}
        className="relative mx-auto flex max-w-[1280px] items-stretch overflow-x-auto px-2"
      >
        {NAV.map((item) => {
          const on = active === item.label;
          const count =
            item.label === "Latest Jobs" ? jobCount : item.label === "Admit Cards" ? admitCount : null;
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

function BottomNav({
  active,
  onSelect,
}: {
  active: Tab;
  onSelect: (l: Tab) => void;
}) {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t-2 border-ink bg-paper/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      aria-label="Mobile navigation"
    >
      <div className="mx-auto grid max-w-[520px] grid-cols-5">
        {BOTTOM_NAV.map((item) => {
          const on = active === item.label;
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              onClick={() => onSelect(item.label)}
              aria-current={on ? "page" : undefined}
              aria-label={item.label}
              className={`flex min-h-[58px] flex-col items-center justify-center gap-0.5 px-1 text-[10.5px] font-semibold ${
                on ? "text-saffron" : "text-ink/55"
              }`}
            >
              <Icon size={20} strokeWidth={on ? 2.4 : 1.9} aria-hidden="true" />
              <span>{item.short}</span>
            </button>
          );
        })}
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
  if (total === null) {
    return (
      <div className="border-b border-line bg-paper px-4 py-6 sm:px-5 sm:py-10" aria-hidden="true">
        <div className="h-3 w-40 animate-pulse rounded bg-cream" />
        <div className="mt-3 h-8 w-3/4 animate-pulse rounded bg-cream" />
        <div className="mt-2 h-8 w-1/2 animate-pulse rounded bg-cream" />
        <div className="mt-4 h-3 w-56 animate-pulse rounded bg-cream" />
      </div>
    );
  }
  return (
    <section className="border-b border-line bg-paper">
      <div className="mx-auto max-w-[1280px] px-4 pt-6 pb-5 sm:px-5 sm:pt-10 sm:pb-8">
        <p className="font-mono text-[11px] font-bold tracking-[.18em] text-saffron uppercase">
          sarkari naukri · official notifications
        </p>
        <h1 className="mt-2 max-w-3xl text-[27px] font-extrabold leading-[1.1] tracking-tight text-ink sm:text-[46px] sm:leading-[1.08]">
          Government jobs, <span className="text-saffron">without the noise.</span>
        </h1>
        <p className="mt-2 text-[12px] font-mono font-bold tabular-nums text-ink/70 sm:hidden">
          {total} live · {closingThisWeek ?? 0} closing · updated today
        </p>
        <p className="mt-3 hidden max-w-xl text-[15.5px] leading-relaxed text-ink/65 sm:block">
          Every notification linked to its official PDF. Eligibility in seconds,
          one place to everything that's live.
        </p>
        <div className="mt-5 hidden flex-wrap items-center gap-x-5 gap-y-2 border-t border-line pt-4 font-mono text-[12.5px] tabular-nums text-ink/70 sm:flex">
          <span>
            <span className="font-extrabold text-ink">{total}</span> notifications live
          </span>
          <span aria-hidden="true" className="text-line-strong">|</span>
          <span>
            <span className="font-extrabold text-ink">{closingThisWeek ?? 0}</span> closing this week
          </span>
          <span aria-hidden="true" className="text-line-strong">|</span>
          <span>
            <span className="font-extrabold text-govgreen">✓</span> updated today
          </span>
        </div>
      </div>
    </section>
  );
}

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

function FilterChips({ active, onChange }: { active: Chip; onChange: (c: Chip) => void }) {
  return (
    <div
      className="no-scrollbar -mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1 md:hidden"
      aria-label="Filter notifications"
    >
      {FILTER_CHIPS.map((chip) => (
        <button
          key={chip.id}
          onClick={() => onChange(chip.id)}
          aria-pressed={active === chip.id}
          className={`min-h-11 shrink-0 rounded-full border-2 px-4 text-[13px] font-semibold ${
            active === chip.id
              ? "border-saffron bg-saffron text-white"
              : "border-line bg-white text-ink/70"
          }`}
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}

function MobileClosingSoon({ exams, loading }: { exams: FeedExam[]; loading: boolean }) {
  return (
    <section className="border-b border-line bg-paper px-4 py-5 md:hidden">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="flex items-baseline gap-2 text-[20px] font-extrabold tracking-tight text-ink">
          Closing Soon
          {exams.length > 0 && (
            <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-white">
              {exams.length}
            </span>
          )}
        </h2>
        <p className="text-[11px] font-semibold tracking-wide text-ink/55 uppercase">Next 10 days</p>
      </div>
      <div className="no-scrollbar -mx-4 mt-3 flex snap-x snap-mandatory gap-2 overflow-x-auto px-4 pb-2">
        {loading ? (
          <div className="h-20 w-[240px] shrink-0 animate-pulse rounded-lg bg-cream" />
        ) : exams.length === 0 ? (
          <div className="rounded-lg border border-line bg-[#fbfaf7] px-4 py-3 text-[13px] text-ink/55">
            Nothing closes in the next 10 days.
          </div>
        ) : (
          exams.map((e) => (
            <a
              key={e.id}
              href={safeUrl(e.pdfUrl)}
              target={e.pdfUrl ? "_blank" : undefined}
              rel="noopener noreferrer"
              className="w-[240px] shrink-0 snap-start rounded-lg border border-line bg-[#fbfaf7] px-4 py-3"
            >
              <p className="line-clamp-2 text-[13.5px] font-semibold leading-snug text-ink">{e.title}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-[5px] flex-1 overflow-hidden rounded-full bg-cream">
                  <div
                    className={`h-full rounded-full ${e.deadlineDays <= 7 ? "bg-alert" : "bg-saffron"}`}
                    style={{ width: `${Math.max(8, (e.deadlineDays / 45) * 100)}%` }}
                  />
                </div>
                <span className="text-[12.5px] font-bold tabular-nums text-alert">{e.deadlineDays}d</span>
              </div>
            </a>
          ))
        )}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */

export function Rozgar({ adLayout, tab }: { adLayout: AdLayout; tab: Tab }) {
  const navigate = useNavigate();
  const active = tab;
  const [query, setQuery] = useState("");
  const [chip, setChip] = useState<Chip>("all");
  const [accountOpen, setAccountOpen] = useState(false);

  const [exams, setExams] = useState<FeedExam[] | null>(() => {
    const data = getPrerenderData();
    return data?.exams ? data.exams.filter((e) => e.is_active).map(toFeedExam) : null;
  });
  const [loadError, setLoadError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const [admitCards, setAdmitCards] = useState<FeedAdmitCard[] | null>(() => {
    const data = getPrerenderData();
    return data?.admitCards
      ? data.admitCards.filter((c) => c.is_active).map(toFeedAdmitCard)
      : null;
  });
  const [admitError, setAdmitError] = useState<string | null>(null);

  const [eligibility, setEligibility] = useState<EligibilityCheckResponse | null>(null);
  const setAndCacheEligibility = (r: EligibilityCheckResponse | null) => {
    setEligibility(r);
    if (r) saveEligibilityResult(r);
  };

  // Loaded after mount so the first render matches the prerendered HTML.
  useEffect(() => {
    const saved = loadEligibilityResult();
    if (saved) setEligibility(saved);
  }, []);

  const scrolled = useScrolled(80);
  const [forceExpanded, setForceExpanded] = useState(false);
  const [loadMore, setLoadMore] = useState(false);

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
        // Keep the prerendered list if the refresh fails - it is better than
        // replacing real content with an error state.
        if (!getPrerenderData()?.exams) setExams(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [retryCount]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setAdmitError(null);
      try {
        const res = await getAdmitCards();
        if (cancelled) return;
        setAdmitCards(res.admit_cards.filter((c) => c.is_active).map(toFeedAdmitCard));
      } catch (err) {
        if (cancelled) return;
        setAdmitError(err instanceof Error ? err.message : "Could not load admit cards.");
        if (!getPrerenderData()?.admitCards) setAdmitCards(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [retryCount]);

  const filteredAdmitCards = useMemo(() => {
    if (!admitCards) return [];
    if (!query.trim()) return admitCards;
    const q = query.toLowerCase();
    return admitCards.filter((c) =>
      `${c.title} ${c.department} ${c.examName ?? ""}`.toLowerCase().includes(q),
    );
  }, [admitCards, query]);

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

  const chipped = useMemo(() => {
    switch (chip) {
      case "closing":
        return filtered.filter((e) => e.deadlineDays > 0 && e.deadlineDays <= 10);
      case "graduate":
        return filtered.filter((e) => e.degrees.some((d) => /graduat|b\.?tech|b\.?e\b|bca|bsc|b\.?sc|mca|mba|m\.?tech/i.test(d)));
      case "12th":
        return filtered.filter((e) => /12th|intermediate|senior secondary|hsc/i.test(e.degrees.join(" ")));
      case "10th":
        return filtered.filter((e) => /10th|matric|high school/i.test(e.degrees.join(" ")));
      default:
        return filtered;
    }
  }, [filtered, chip]);

  // Every job stays in the DOM so crawlers can follow all links. On small
  // screens the tail is hidden with CSS until "Load more" is tapped.
  const visible = chipped;

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

  const verdicts = useMemo(() => {
    const map = new Map<string, "eligible" | "borderline" | "check" | "ineligible">();
    if (!eligibility) return map;
    eligibility.eligible_now.forEach((r) => map.set(r.exam_id, "eligible"));
    eligibility.borderline_last_chance.forEach((r) => map.set(r.exam_id, "borderline"));
    eligibility.check_manually.forEach((r) => map.set(r.exam_id, "check"));
    eligibility.ineligible.forEach((r) => map.set(r.exam_id, "ineligible"));
    return map;
  }, [eligibility]);

  const feed = useMemo(() => {
    const items: ReactNode[] = [];
    visible.forEach((exam, i) => {
      if (ADS_ENABLED && i > 0 && i % AD_FREQUENCY === 0) {
        const sp = SPONSORED_JOBS[(i / AD_FREQUENCY - 1) % SPONSORED_JOBS.length];
        items.push(<SponsoredJobCard key={`sp-${sp.id}`} job={sp} />);
      }
      items.push(
        <div
          key={exam.id}
          className={!loadMore && i >= MOBILE_PAGE_SIZE ? "hidden md:block" : ""}
        >
          <JobCard exam={exam} verdict={verdicts.get(exam.id) ?? null} />
        </div>,
      );
    });
    return items;
  }, [visible, verdicts, loadMore]);

  const goTab = (next: Tab) => {
    setForceExpanded(false);
    setChip("all");
    setLoadMore(false);
    navigate(PATH_FOR_TAB[next]);
    window.scrollTo({ top: 0 });
  };

  const openAccount = () => {
    setAccountOpen(true);
  };

  return (
    <div className="min-h-screen bg-paper pb-[calc(58px+env(safe-area-inset-bottom))] text-ink md:pb-0">
      <div
        className={`sticky top-0 z-40 border-b-2 border-ink ${
          scrolled ? "shadow-[0_2px_10px_rgba(0,0,0,.08)]" : ""
        }`}
      >
        <Masthead
          query={query}
          onQueryChange={setQuery}
          compact={scrolled && !forceExpanded}
          onExpand={() => setForceExpanded(true)}
          onAccount={openAccount}
        />
        <div className={scrolled && !forceExpanded ? "hidden md:block" : ""}>
          <MainNav active={active} onSelect={goTab} jobCount={exams?.length ?? null} admitCount={admitCards?.length ?? null} />
        </div>
      </div>

      <BottomNav active={active} onSelect={goTab} />
      {accountOpen && (
        <Suspense fallback={null}>
          <AccountModal onClose={() => setAccountOpen(false)} />
        </Suspense>
      )}

      {active === "Latest Jobs" && (
        <HeroBand total={exams?.length ?? null} closingThisWeek={closingThisWeek} />
      )}

      <div key={active} className="animate-[tab-in_.35s_ease-out]">
        {active === "Latest Jobs" && (
          <>
            <MobileClosingSoon exams={closingSoon} loading={exams === null && !loadError} />
            <div className={`mx-auto grid max-w-[1280px] gap-6 px-4 py-6 sm:px-5 ${ADS_ENABLED ? "lg:grid-cols-[288px_1fr_288px]" : "lg:grid-cols-[1fr_340px]"}`}>
              {ADS_ENABLED && (
                <div className="hidden space-y-4 lg:block">
                  {adLayout.left.map((ad) => (
                    <div
                      key={ad.id}
                      className="mx-auto w-full max-w-[300px] overflow-hidden rounded-lg border border-dashed border-line-strong bg-white/60"
                    >
                      <AdSlot {...ad} className="border-0" />
                    </div>
                  ))}
                </div>
              )}

              <main id="job-results" className="min-w-0">
                <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
                  <h2 className="flex items-baseline gap-2 text-[22px] font-extrabold tracking-tight text-ink">
                    Latest Jobs
                    {exams && (
                      <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-white">
                        {chipped.length}
                      </span>
                    )}
                  </h2>
                  <p className="text-[12px] font-semibold tracking-wide text-ink/55 uppercase">
                    Official sources only
                  </p>
                </div>

                <FilterChips active={chip} onChange={(c) => { setChip(c); setLoadMore(false); }} />

                <div className="space-y-2.5">
                  {exams === null && !loadError ? (
                    <LoadingSkeleton />
                  ) : loadError && exams === null ? (
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
                  ) : chipped.length === 0 ? (
                    <div className="rounded-lg border border-line bg-[#fbfaf7] px-5 py-14 text-center">
                      <p className="text-[17px] font-bold text-ink">No matching notifications</p>
                      <p className="mt-1 text-[14px] text-ink/60">Try clearing the search or filter.</p>
                    </div>
                  ) : (
                    feed
                  )}
                </div>

                {!loadMore && chipped.length > MOBILE_PAGE_SIZE && (
                  <div className="mt-4 md:hidden">
                    <button
                      onClick={() => setLoadMore(true)}
                      className="min-h-11 w-full rounded-lg border-2 border-line bg-white text-[14px] font-bold text-ink hover:border-line-strong"
                    >
                      Load {chipped.length - MOBILE_PAGE_SIZE} more jobs
                    </button>
                  </div>
                )}
              </main>

              <aside className="hidden self-start lg:sticky lg:top-4 lg:block">
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
                  {exams === null && !loadError && (
                    <div className="h-16 animate-pulse rounded-lg bg-cream" aria-hidden="true" />
                  )}
                  {exams !== null && closingSoon.length === 0 && (
                    <div className="rounded-lg border border-line bg-[#fbfaf7] px-4 py-4 text-[13px] text-ink/55">
                      Nothing closes in the next 10 days.
                    </div>
                  )}
                  {closingSoon.map((e) => (
                    <a
                      key={e.id}
                      href={safeUrl(e.pdfUrl)}
                      target={e.pdfUrl ? "_blank" : undefined}
                      rel="noopener noreferrer"
                      className="block overflow-hidden rounded-lg border border-line bg-[#fbfaf7] px-4 py-3 transition-colors hover:border-line-strong"
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
                      </div>
                    </a>
                  ))}
                </div>
                {exams !== null && (
                  <p className="mt-4 text-[12px] text-ink/60">
                    {closingSoon.length} notification{closingSoon.length === 1 ? "" : "s"} close within 10 days
                  </p>
                )}
              </aside>
            </div>
          </>
        )}

        {active === "Admit Cards" && (
          <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
            <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
              <h1 className="flex items-baseline gap-2 text-[22px] font-extrabold tracking-tight text-ink">
                Admit Cards
                {admitCards && (
                  <span className="rounded-full bg-ink px-2 py-0.5 font-mono text-[12px] font-bold tabular-nums text-white">
                    {filteredAdmitCards.length}
                  </span>
                )}
              </h1>
              <p className="text-[12px] font-semibold tracking-wide text-ink/55 uppercase">
                Official download links only
              </p>
            </div>
            <p className="mb-4 max-w-2xl text-[13.5px] leading-relaxed text-ink/60">
              e-Admit cards and exam-city intimations, straight from the boards. Exams usually 2–14
              days away — carry a valid photo ID to the centre.
            </p>
            <div className="space-y-2.5">
              {admitCards === null && !admitError ? (
                <LoadingSkeleton />
              ) : admitError && admitCards === null ? (
                <div className="rounded-lg border border-line bg-[#fbfaf7] px-5 py-14 text-center">
                  <p className="text-[17px] font-bold text-ink">Couldn't load admit cards</p>
                  <p className="mt-1 text-[14px] text-ink/60">{admitError}</p>
                  <button
                    onClick={() => setRetryCount((c) => c + 1)}
                    className="mt-4 h-11 rounded-lg bg-ink px-4 text-[13.5px] font-bold text-white hover:bg-saffron"
                  >
                    Try again
                  </button>
                </div>
              ) : filteredAdmitCards.length === 0 ? (
                <div className="rounded-lg border border-line bg-[#fbfaf7] px-5 py-14 text-center">
                  <p className="text-[17px] font-bold text-ink">No admit cards right now</p>
                  <p className="mt-1 text-[14px] text-ink/60">
                    When a board releases an admit card, it will appear here. Check the official
                    portal in the meantime.
                  </p>
                </div>
              ) : (
                filteredAdmitCards.map((c) => <AdmitCardCard key={c.id} card={c} />)
              )}
            </div>
          </div>
        )}

        {active === "Closed Jobs" && (
          <Suspense fallback={<ChunkFallback />}>
            <ClosedJobsPage />
          </Suspense>
        )}
        {active === "My Eligibility" && (
          <Suspense fallback={<ChunkFallback />}>
            <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
              <EligibilityPage result={eligibility} onResultChange={setAndCacheEligibility} />
            </div>
          </Suspense>
        )}
        {active === "My Roadmap" && (
          <Suspense fallback={<ChunkFallback />}>
            <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
              <RoadmapPage />
            </div>
          </Suspense>
        )}
        {active === "Photo & Signature" && (
          <Suspense fallback={<ChunkFallback />}>
            <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-5">
              <DocumentResizer />
            </div>
          </Suspense>
        )}
      </div>

      <Footer />
    </div>
  );
}
