/** Must stay identical to backend/app/core/seo.py::slug_for. */
export function slugFor(title: string, recordId: string): string {
  const base = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80)
    .replace(/-+$/, "");
  const suffix = recordId.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 8);
  return base ? `${base}-${suffix}` : suffix;
}
