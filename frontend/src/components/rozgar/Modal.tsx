import { useEffect, type ReactNode } from "react";

/**
 * Tiny dependency-free modal: overlay click or Escape closes it,
 * the panel caps at max-w-md with an internal scroll.
 */
export function Modal({
  title,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/55 backdrop-blur-sm sm:items-center sm:p-8"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`flex max-h-[88dvh] w-full flex-col rounded-t-xl border border-line bg-white shadow-xl sm:max-h-[85dvh] sm:rounded-lg ${
          wide ? "sm:max-w-2xl" : "sm:max-w-md"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="text-[16px] font-extrabold text-ink">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="grid size-11 place-items-center rounded-lg text-ink/60 hover:bg-cream hover:text-ink"
          >
            ✕
          </button>
        </div>
        <div className="min-h-0 overflow-y-auto p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] sm:pb-5">
          {children}
        </div>
      </div>
    </div>
  );
}
