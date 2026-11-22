/** Must stay identical to backend/app/core/seo.py. */
export function slugFor(title: string, recordId: string): string {
  const base = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80)
    .replace(/-+$/, "");
  const suffix = recordId.toLowerCase().replace(/-/g, "").replace(/_/g, "");
  return base ? `${base}-${suffix}` : suffix;
}
