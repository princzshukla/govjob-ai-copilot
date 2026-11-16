import { useId } from "react";

/**
 * The eligibility seal — a rubber stamp, borrowed from direction A.
 *
 * In this category an official stamp is the emotional core ("is this real?"),
 * and SarkariResult itself uses a circular seal as its logo. This is the one
 * idea worth carrying out of the deleted directions.
 *
 * The stamp is decorative; the word next to it ("YOU QUALIFY") carries the
 * message. So the seal only has to read as a stamp at a glance — it must NOT
 * try to be the source of truth.
 */
export function Seal({
  label = "ELIGIBLE",
  size = 64,
  tone = "#a81c1c",
  glyph,
}: {
  label?: string;
  size?: number;
  tone?: string;
  /** the mark in the middle. Defaults to a tick for ELIGIBLE, a cross otherwise. */
  glyph?: string;
}) {
  const id = useId().replace(/:/g, "");
  const pathId = `seal-arc-${id}`;
  const mark = glyph ?? (label.startsWith("NOT") ? "✕" : "✓");

  // Arc that runs over the TOP of the circle, so the word is upright and
  // centred rather than sliding around the bottom.
  const arc = "M 9,36 A 27,27 0 0 1 63,36";

  return (
    <div
      className="relative shrink-0 select-none"
      style={{ width: size, height: size, color: tone }}
      aria-label={label}
      role="img"
    >
      <svg viewBox="0 0 72 72" className="absolute inset-0 size-full">
        <defs>
          <path id={pathId} d={arc} />
        </defs>

        <circle cx="36" cy="36" r="34" fill="none" stroke="currentColor" strokeWidth="2" />
        <circle cx="36" cy="36" r="25.5" fill="none" stroke="currentColor" strokeWidth="1" />
        <circle cx="36" cy="36" r="30" fill="none" stroke="currentColor" strokeWidth="0.75" strokeDasharray="2 3" />

        {/* radial ticks on the lower half only, so they never fight the word */}
        {Array.from({ length: 14 }).map((_, i) => {
          const a = (i / 14) * Math.PI * 2 + Math.PI * 0.06;
          return (
            <line
              key={i}
              x1={36 + Math.cos(a) * 31}
              y1={36 + Math.sin(a) * 31}
              x2={36 + Math.cos(a) * 33}
              y2={36 + Math.sin(a) * 33}
              stroke="currentColor"
              strokeWidth="1"
            />
          );
        })}

        <text
          fill="currentColor"
          fontSize="8"
          fontWeight="700"
          letterSpacing="0.9"
          fontFamily="'Space Mono', monospace"
        >
          <textPath href={`#${pathId}`} startOffset="50%" textAnchor="middle">
            {label}
          </textPath>
        </text>

        <text
          x="36"
          y="44"
          fill="currentColor"
          fontSize="22"
          fontWeight="700"
          textAnchor="middle"
          fontFamily="'Space Grotesk', 'Space Mono', monospace"
        >
          {mark}
        </text>
      </svg>
    </div>
  );
}
