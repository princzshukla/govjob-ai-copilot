/**
 * Backend/scrape data is untrusted: React does not sanitize URL schemes in
 * href, so a poisoned `javascript:` value would execute in our origin.
 * Allow http(s) only and return undefined for everything else, which makes
 * React omit the href attribute entirely.
 */
export function safeUrl(value: string | null | undefined): string | undefined {
  if (!value || !value.trim()) return undefined;
  try {
    const base = typeof window === "undefined" ? "http://localhost/" : window.location.href;
    const url = new URL(value, base);
    if (url.protocol !== "https:" && url.protocol !== "http:") return undefined;
    return url.href;
  } catch {
    return undefined;
  }
}
