import { useToasts } from "../../lib/toast";

const TONE: Record<string, string> = {
  info: "border-line bg-white text-ink",
  success: "border-govgreen bg-govgreen/8 text-ink",
  warn: "border-saffron bg-saffron/10 text-ink",
};

export function ToastHost() {
  const items = useToasts();
  if (items.length === 0) return null;

  return (
    <div className="pointer-events-none fixed bottom-20 right-4 z-[60] flex w-[340px] max-w-[calc(100vw-2rem)] flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto rounded-xl border-2 px-4 py-3 shadow-xl backdrop-blur ${TONE[t.kind] ?? TONE.info}`}
        >
          <p className="text-[14px] font-bold">{t.title}</p>
          {t.body && <p className="mt-0.5 text-[13px] text-ink/70">{t.body}</p>}
        </div>
      ))}
    </div>
  );
}
