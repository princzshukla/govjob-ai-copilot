import { useAuth } from "../../lib/auth";

export function Footer() {
  const { promptSignIn } = useAuth();

  return (
    <footer className="border-t-2 border-ink bg-cream">
      <div className="mx-auto max-w-[1280px] px-4 sm:px-5">
        {/* main slab */}
        <div className="grid gap-10 py-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr]">
          {/* brand */}
          <div>
            <p className="flex items-center gap-3">
              <span className="flex h-10 w-1.5 flex-col overflow-hidden rounded-full" aria-hidden="true">
                <span className="flex-1 bg-saffron" />
                <span className="flex-1 bg-white" />
                <span className="flex-1 bg-govgreen" />
              </span>
              <span className="text-[24px] font-extrabold tracking-tight text-ink">
                Rozgar<span className="text-saffron">Board</span>
              </span>
            </p>
            <p className="mt-3 max-w-sm text-[14.5px] leading-relaxed text-ink/75">
              Government jobs, without the noise — every notification linked to the
              official PDF, checked against you in seconds.
            </p>
            <p className="mt-4 flex items-center gap-2 text-[12.5px] text-ink/60">
              <span className="size-1.5 rounded-full bg-govgreen" aria-hidden="true" />
              Sourced from official notifications · Updated daily · Official PDF linked
              on every job
            </p>
          </div>

          {/* alerts */}
          <div>
            <p className="font-mono text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">
              Notifications
            </p>
            <p className="mt-3 text-[14.5px] leading-snug text-ink/80">
              Get a Telegram message the moment a deadline you care about is close.
            </p>
            <button
              onClick={() => promptSignIn("login")}
              className="mt-3 inline-flex h-11 items-center rounded-lg bg-saffron px-4 text-[13.5px] font-bold text-white transition-transform hover:-translate-y-0.5"
            >
              Get Telegram alerts →
            </button>
            <p className="mt-5 text-[12px] text-ink/55">
              You can unlink any time from <span className="font-semibold">My account</span>.
            </p>
          </div>
        </div>

        {/* bottom bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-4 text-[12px] text-ink/55">
          <p>© 2026 RozgarBoard · Government jobs in India</p>
          <p className="flex gap-4">
            <a href="https://ssc.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-ink">
              SSC
            </a>
            <a href="https://www.upsc.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-ink">
              UPSC
            </a>
            <a href="https://www.ibps.in" target="_blank" rel="noopener noreferrer" className="hover:text-ink">
              IBPS
            </a>
            <a href="https://www.rrb.gov.in" target="_blank" rel="noopener noreferrer" className="hover:text-ink">
              RRB
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
