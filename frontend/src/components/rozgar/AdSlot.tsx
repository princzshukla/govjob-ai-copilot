import { useEffect, useRef } from "react";
import { registerAdSlot, reportVisibility, unregisterAdSlot } from "../../lib/ad-metrics";

/**
 * Ad primitives.
 *
 * Three rules encoded here so they cannot be forgotten:
 *  1. every ad is labelled — an unlabelled ad in a job feed is a lie
 *  2. the space is reserved before the creative loads — no layout shift
 *  3. the slot reports its own viewability, because an unseen ad earns nothing
 */

export function AdLabel({ kind = "Ad" }: { kind?: string }) {
  return (
    <span className="inline-flex items-center rounded border border-ink/25 bg-white/70 px-1.5 py-0.5 font-mono text-[10px] font-bold tracking-[.14em] text-ink/55 uppercase">
      {kind}
    </span>
  );
}

/**
 * Viewability via a single IntersectionObserver — no scroll listeners, no
 * per-second interval. Fires only when the fraction crosses 50%, which is the
 * threshold that matters for the active-view rule.
 */
function useViewability(id: string, enabled: boolean) {
  const ref = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!enabled) return;
    registerAdSlot(id, id);

    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      reportVisibility(id, 1);
      return () => unregisterAdSlot(id);
    }

    const io = new IntersectionObserver(
      (entries) => {
        const ratio = entries[0]?.intersectionRatio ?? 0;
        reportVisibility(id, ratio);
      },
      { threshold: [0, 0.5, 1] },
    );
    io.observe(el);

    return () => {
      io.disconnect();
      unregisterAdSlot(id);
    };
  }, [id, enabled]);

  return ref;
}

export function AdSlot({
  id,
  height,
  label,
  advertiser,
  headline,
  body,
  cta,
  tone = "ink",
  className = "",
  track = true,
}: {
  id: string;
  height: number;
  width?: number;
  label: string;
  advertiser: string;
  headline: string;
  body?: string;
  cta?: string;
  tone?: "saffron" | "ink" | "green";
  className?: string;
  track?: boolean;
}) {
  const ref = useViewability(id, track);

  const toneClass =
    tone === "saffron"
      ? "bg-saffron/12 border-saffron/40"
      : tone === "green"
        ? "bg-govgreen/10 border-govgreen/35"
        : "bg-cream/60 border-line";

  return (
    <aside
      ref={ref as React.RefObject<HTMLElement>}
      aria-label={label}
      // The height is locked BEFORE the creative paints, so nothing below it moves.
      style={{ minHeight: height }}
      className={`flex w-full flex-col justify-center border px-5 py-3 ${toneClass} ${className}`}
    >
      <div className="flex items-center gap-2">
        <AdLabel kind={label} />
        <span className="font-mono text-[10.5px] tracking-[.12em] text-ink/45 uppercase">
          {advertiser}
        </span>
      </div>
      <p className="mt-1.5 text-[15px] font-bold text-ink">{headline}</p>
      {body && <p className="mt-0.5 text-[13px] text-ink/65">{body}</p>}
      {cta && (
        <span className="mt-2 inline-block w-fit border-2 border-ink px-3 py-1 text-[12.5px] font-bold text-ink">
          {cta} →
        </span>
      )}
    </aside>
  );
}
