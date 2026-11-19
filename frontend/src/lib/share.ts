/** Share a job using the platform sheet; fall back to copying the link. */
export async function shareLink(
  title: string,
  url: string,
): Promise<"shared" | "copied" | "cancelled" | "whatsapp"> {
  if (typeof navigator !== "undefined" && navigator.share) {
    try {
      await navigator.share({ title, url });
      return "shared";
    } catch (err) {
      // A user cancelling the native sheet is not a failure.
      if (err instanceof Error && err.name === "AbortError") return "cancelled";
    }
  }
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    await navigator.clipboard.writeText(url);
    return "copied";
  }
  // Last resort for older browsers: WhatsApp with the link prefilled.
  window.open(
    `https://wa.me/?text=${encodeURIComponent(`${title} — ${url}`)}`,
    "_blank",
    "noopener,noreferrer",
  );
  return "whatsapp";
}

export function whatsappShareUrl(title: string, url: string): string {
  return `https://wa.me/?text=${encodeURIComponent(`${title} — ${url}`)}`;
}
