import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <main className="mx-auto max-w-[720px] px-4 py-20 text-center">
      <p className="font-mono text-[12px] font-bold uppercase tracking-widest text-saffron">
        404
      </p>
      <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink">
        This page isn't here.
      </h1>
      <p className="mt-3 text-[15px] leading-relaxed text-ink/70">
        The link may be old, or the notification may have been archived.
      </p>
      <Link
        to="/"
        className="mt-7 inline-block rounded-full bg-ink px-5 py-2.5 text-sm font-bold text-white"
      >
        See latest jobs
      </Link>
    </main>
  );
}
