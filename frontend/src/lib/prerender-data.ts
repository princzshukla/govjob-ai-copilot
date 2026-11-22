/**
 * Data handoff between the build-time renderer and the browser.
 *
 * The build writes `window.__DATA__` into the HTML. The first client render
 * reads the same object, so React hydrates matching markup instead of
 * rendering an empty loading state and patching it afterwards.
 */
import type { ExamNotification, AdmitCard } from "../types";

export interface PrerenderData {
  path?: string;
  exams?: ExamNotification[];
  admitCards?: AdmitCard[];
  /** Present on detail pages so the HTML stays small. */
  exam?: ExamNotification;
  admitCard?: AdmitCard;
}

declare global {
  interface Window {
    __DATA__?: PrerenderData;
  }
}

export function getPrerenderData(): PrerenderData | null {
  if (typeof window !== "undefined") return window.__DATA__ ?? null;
  return (globalThis as { __SSR_DATA__?: PrerenderData }).__SSR_DATA__ ?? null;
}

/** Safely serialise data for inline <script> (prevents </script> breakout). */
export function serialisePrerenderData(data: PrerenderData): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}
