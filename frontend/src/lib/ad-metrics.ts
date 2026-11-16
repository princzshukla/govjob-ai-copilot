/**
 * Ad viewability tracking — the metric that actually decides whether a slot
 * earns money.
 *
 * Google AdSense, "Viewability and Active View":
 *   "We define a viewable impression as an ad that meets the following
 *    criteria: 50% of the ad's pixels need to be on screen for at least one
 *    continuous second."
 *
 * And from "Viewability best practices":
 *   "Scrolling past an ad too quickly won't count."
 *
 * So being *on the page* is worth nothing. An ad has to be genuinely on screen
 * and dwell there for a second. This module measures that live so the layout
 * decisions can be made on evidence instead of vibes.
 */

export interface AdSlotMetric {
  id: string;
  label: string;
  /** share of the slot's pixels currently inside the viewport, 0..1 */
  visibleRatio: number;
  /** currently satisfying the 50%-for-1s rule */
  viewable: boolean;
  /** how many viewable impressions this slot has served */
  viewableImpressions: number;
}

type Listener = (metrics: AdSlotMetric[]) => void;

const slots = new Map<string, AdSlotMetric>();
const listeners = new Set<Listener>();
const timers = new Map<string, number>();

function emit() {
  const snapshot = [...slots.values()];
  listeners.forEach((fn) => fn(snapshot));
}

export function registerAdSlot(id: string, label: string) {
  if (!slots.has(id)) {
    slots.set(id, {
      id,
      label,
      visibleRatio: 0,
      viewable: false,
      viewableImpressions: 0,
    });
    emit();
  }
}

export function unregisterAdSlot(id: string) {
  slots.delete(id);
  const t = timers.get(id);
  if (t) {
    window.clearTimeout(t);
    timers.delete(id);
  }
  emit();
}

/**
 * Feed a visibility ratio in. The slot becomes "viewable" once at least 50% of
 * its pixels are on screen, and it stays viewable for as long as it stays
 * there. If it drops below the threshold the one-second clock restarts, because
 * the rule is "one CONTINUOUS second".
 */
export function reportVisibility(id: string, ratio: number) {
  const slot = slots.get(id);
  if (!slot) return;

  const changed = slot.visibleRatio !== ratio || slot.viewable !== ratio >= 0.5;
  slot.visibleRatio = ratio;
  slot.viewable = ratio >= 0.5;

  if (slot.viewable) {
    if (!timers.has(id)) {
      timers.set(
        id,
        window.setTimeout(() => {
          timers.delete(id);
          const s = slots.get(id);
          if (s && s.viewable) {
            s.viewableImpressions += 1;
            emit();
          }
        }, 1000),
      );
    }
  } else if (timers.has(id)) {
    window.clearTimeout(timers.get(id)!);
    timers.delete(id);
  }

  if (changed) emit();
}

export function subscribeToAdMetrics(fn: Listener) {
  listeners.add(fn);
  fn([...slots.values()]);
  return () => {
    listeners.delete(fn);
  };
}

/** Test seam — resets the counters between lab runs. */
export function resetAdMetrics() {
  slots.clear();
  timers.forEach((t) => window.clearTimeout(t));
  timers.clear();
  emit();
}
