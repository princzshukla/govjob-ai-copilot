/** A recruiter-paid placement. Shaped for the feed, not the organic notification. */
export interface SponsoredJob {
  id: string;
  title: string;
  department: string;
  state: string;
  qualification: string;
  salary: string;
  deadlineDays: number;
}

/**
 * Ad policy and layout for the job list.
 *
 * Verified against Google's own documentation (full quotes and URLs in
 * AD-MODEL.md). The rules this file encodes:
 *
 *  ALLOWED
 *   - a free-standing, clearly labelled display unit in a rail
 *   - in-feed sponsored listings, provided they are labelled and do not
 *     imitate the organic cards
 *   - anchor / sticky units (Google's own "anchor ad" format), provided they
 *     are dismissible and never cover navigation
 *
 *  NOT ALLOWED (Google AdSense "Ad placement policies")
 *   - an ad under a heading that implies the content below is content, e.g.
 *     "Important Links", "Resources", "Helpful Links"
 *   - content formatted to look like an ad, or an ad formatted to look like
 *     content
 *   - anything that encourages accidental clicks (ads that look like nav or
 *     download buttons)
 *   - flashy animation that pulls the eye to the ad, or arrows pointing at it
 *   - auto-refresh, interstitials, pop-ups, pop-unders, new windows
 *
 *  WHAT ACTUALLY EARNS
 *   AdSense pays an eCPM per impression, so impressions pay and clicks are
 *   optional. But only a VIEWABLE impression counts: 50% of the ad's pixels on
 *   screen for at least one continuous second. An ad nobody sees earns
 *   nothing, and chasing clicks risks invalid-traffic strikes.
 */

export const AD_FREQUENCY = 8; // 1 sponsored card per 8 organic cards

export type AdKind = "rail" | "feed" | "house";

export interface AdSlotSpec {
  id: string;
  kind: AdKind;
  /** reserved height in px, locked so nothing shifts when the ad loads */
  height: number;
  width: number;
  label: string;
  advertiser: string;
  headline: string;
  body: string;
  cta: string;
  tone: "saffron" | "ink" | "green";
}

/** Recruiter-paid placements. They look like notifications, and say so. */
export const SPONSORED_JOBS: SponsoredJob[] = [
  {
    id: "sponsored-hdfc",
    title: "HDFC Bank — Probationary Officer (via CampusHire)",
    department: "HDFC Bank · CampusHire",
    state: "All India",
    qualification: "Graduate",
    salary: "₹32,000 – ₹48,000",
    deadlineDays: 12,
  },
  {
    id: "sponsored-tcs",
    title: "Tata Consultancy Services — Graduate Engineer Trainee",
    department: "TCS · via FreshersWorld",
    state: "All India",
    qualification: "Graduate",
    salary: "₹29,000 – ₹41,000",
    deadlineDays: 20,
  },
];

/** The house display units. Each has a reserved height so nothing shifts. */
export const HOUSE_ADS: Record<string, AdSlotSpec> = {
  "prep-insta": {
    id: "prep-insta",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "PrepInsta",
    headline: "Free mock tests for SSC CHSL",
    body: "12 full-length mocks with sectional timing. No sign-up needed.",
    cta: "Start a mock",
    tone: "saffron",
  },
  "unacademy": {
    id: "unacademy",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "Unacademy",
    headline: "Crash courses for 2026 exams",
    body: "SSC · RRB · Banking. 40 hours, in Hindi & English.",
    cta: "See courses",
    tone: "ink",
  },
  "ambition-box": {
    id: "ambition-box",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "AmbitionBox",
    headline: "Never miss a notification again",
    body: "WhatsApp + Telegram alerts the minute a notification drops.",
    cta: "Turn on alerts",
    tone: "green",
  },
  "naukri-prime": {
    id: "naukri-prime",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "Naukri.com",
    headline: "Private sector jobs, 10 lakh+ openings",
    body: "Software, BFSI, sales — filtered by your profile.",
    cta: "Browse jobs",
    tone: "ink",
  },
  "testbook": {
    id: "testbook",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "Testbook",
    headline: "Free PYQ practice for every exam",
    body: "10 years of previous papers, chapter-wise.",
    cta: "Start free",
    tone: "green",
  },
  "adda247": {
    id: "adda247",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "Adda247",
    headline: "Daily current affairs for SSC & Banking",
    body: "The one page that saves you an hour a day.",
    cta: "Read today's CA",
    tone: "saffron",
  },
  "oliveboard": {
    id: "oliveboard",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "Oliveboard",
    headline: "Full-length tests in 15 languages",
    body: "SSC, RRB, Banking, Railways — one subscription.",
    cta: "See the plans",
    tone: "ink",
  },
  "sarkari-result": {
    id: "sarkari-result",
    kind: "rail",
    height: 250,
    width: 300,
    label: "Advertisement",
    advertiser: "RozgarApp",
    headline: "Get the app — alerts on WhatsApp",
    body: "Every new notification on your phone in 30 seconds.",
    cta: "Install",
    tone: "green",
  },
};

/* ------------------------------------------------------------------ */
/* Layouts — the side-by-side comparison the team is looking at        */
/* ------------------------------------------------------------------ */

export interface AdLayout {
  id: string;
  label: string;
  blurb: string;
  /** trade-off the layout accepts, stated plainly */
  cost: string;
  /** ad slots pinned to the LEFT of the feed */
  left: AdSlotSpec[];
  /** ad slots pinned to the RIGHT of the feed */
  right: AdSlotSpec[];
  /** when the right-hand ads sit relative to the content panels */
  rightOrder: "ads-first" | "ads-last";
}

export const AD_LAYOUTS: AdLayout[] = [
  {
    id: "balanced",
    label: "A · Balanced",
    blurb:
      "One display unit per rail. Filters live in the bar above the feed, so both rails are free for inventory.",
    cost:
      "Two ad slots, both on screen at 100% viewability on arrival. The lightest layout that still uses both rails.",
    left: [HOUSE_ADS["prep-insta"]],
    right: [HOUSE_ADS["ambition-box"]],
    rightOrder: "ads-first",
  },
  {
    id: "both-rails-heavy",
    label: "B · Both rails, heavy",
    blurb:
      "Three units down the left rail, two on the right, plus the sponsored cards in the feed.",
    cost:
      "The maximum inventory this layout can carry without an interstitial or a sticky bar. Five display units plus 2 sponsored cards on a 21-card page. Every unit is 100% viewable at load, but the left rail is now pure advertising and users scroll past five blocks of it.",
    left: [
      HOUSE_ADS["prep-insta"],
      HOUSE_ADS["testbook"],
      HOUSE_ADS["adda247"],
    ],
    right: [HOUSE_ADS["ambition-box"], HOUSE_ADS["oliveboard"]],
    rightOrder: "ads-first",
  },
  {
    id: "right-heavy",
    label: "C · Right-heavy",
    blurb:
      "All inventory on the right — three units stacked above the content panels. Left rail carries a house panel, not ads.",
    cost:
      "Three viewable units on the right, and the attention zone on the left stays clean for the feed. The rail gets long, so the third unit sits below the fold on shorter screens.",
    left: [],
    right: [
      HOUSE_ADS["ambition-box"],
      HOUSE_ADS["prep-insta"],
      HOUSE_ADS["testbook"],
    ],
    rightOrder: "ads-first",
  },
  {
    id: "ads-last",
    label: "D · Ads last",
    blurb:
      "Left rail heavy, right rail puts its single unit BELOW Important Links and Closing Soon.",
    cost:
      "Textbook-compliant on headings — and the one that earns nothing. The right unit sits at y=909 on a 900px viewport, so it records 0% visible and banks no viewable impressions until the user scrolls the entire feed.",
    left: [HOUSE_ADS["prep-insta"], HOUSE_ADS["testbook"]],
    right: [HOUSE_ADS["ambition-box"]],
    rightOrder: "ads-last",
  },
];

export const DEFAULT_LAYOUT = AD_LAYOUTS[0];
