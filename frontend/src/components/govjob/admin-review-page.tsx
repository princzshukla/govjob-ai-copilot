import { useCallback, useEffect, useState } from "react";
import {
  Check,
  ExternalLink,
  Loader2,
  Pencil,
  ShieldAlert,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as api from "@/lib/govjob/api";
import type { AdminExtractionEdit, ReviewQueueItem } from "@/lib/govjob/api";

interface EditForm {
  total_vacancies: string;
  min_age: string;
  age_max_general: string;
  age_cutoff_date: string;
  required_qualification: string;
  application_last_date: string;
  pay_level: string;
}

function emptyForm(item: ReviewQueueItem): EditForm {
  const e = item.extracted as Record<string, unknown>;
  const str = (v: unknown) =>
    v === null || v === undefined ? "" : String(v);
  return {
    total_vacancies: str(e["total_vacancies"]),
    min_age: str(e["min_age"]),
    age_max_general: str(e["age_max_general"]),
    age_cutoff_date: str(e["age_cutoff_date"]),
    required_qualification: str(e["required_qualification"]),
    application_last_date: str(e["application_last_date"]),
    pay_level: str(e["pay_level"]),
  };
}

export function AdminReviewPage() {
  const [items, setItems] = useState<ReviewQueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionId, setActionId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<EditForm | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const rows = await api.fetchAdminReviewQueue();
      setItems(rows);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : "Could not load review queue");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const act = async (item: ReviewQueueItem, action: "approve" | "reject") => {
    setActionId(item.id);
    try {
      if (action === "approve") {
        const result = await api.adminApproveExtraction(item.id);
        toast.success(`Promoted: ${result.title}`);
      } else {
        await api.adminRejectExtraction(item.id);
        toast.success("Rejected — never shown to users.");
      }
      setEditingId(null);
      setItems((prev) => (prev ?? []).filter((row) => row.id !== item.id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionId(null);
    }
  };

  const saveEdit = async (item: ReviewQueueItem) => {
    if (!form) return;
    setActionId(item.id);
    const num = (v: string) => (v.trim() === "" ? null : Number(v));
    const strOrNull = (v: string) => (v.trim() === "" ? null : v.trim());
    const payload: AdminExtractionEdit = {
      total_vacancies: num(form.total_vacancies),
      min_age: num(form.min_age),
      age_max_general: num(form.age_max_general),
      age_cutoff_date: strOrNull(form.age_cutoff_date),
      required_qualification: strOrNull(form.required_qualification),
      application_last_date: strOrNull(form.application_last_date),
      pay_level: strOrNull(form.pay_level),
    };
    try {
      const result = await api.adminEditExtraction(item.id, payload);
      toast.success(`Promoted: ${result.title}`);
      setEditingId(null);
      setForm(null);
      setItems((prev) => (prev ?? []).filter((row) => row.id !== item.id));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not promote");
    } finally {
      setActionId(null);
    }
  };

  if (items === null) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-6 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" /> Loading review queue…
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldAlert className="size-5 text-warning" /> {error}
          </CardTitle>
          <CardDescription>
            The review queue is restricted to accounts on the admin allowlist.
            Sign in with an admin account, or ask the maintainer for access.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Review queue is empty</CardTitle>
          <CardDescription>
            Extractions the gate could not vouch for land here. When they start
            arriving from the worker, you will see them with their evidence
            quotes and the official PDF.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Review queue</h1>
        <Badge variant="secondary">{items.length} held</Badge>
      </div>
      {items.map((item) => (
        <Card key={item.id}>
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <CardTitle className="text-base leading-snug">
                  {item.title ?? `${item.organizing_body} — unnamed notice`}
                </CardTitle>
                <CardDescription className="mt-0.5">
                  {item.organizing_body} · {item.source_slug} · held{" "}
                  {new Date(item.created_at).toLocaleDateString()}
                </CardDescription>
              </div>
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 rounded-lg border p-1.5 text-muted-foreground transition hover:bg-muted"
                title="Open official PDF"
                aria-label="Open official PDF"
              >
                <ExternalLink className="size-4" />
              </a>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {item.review_note && (
              <p className="rounded-lg border border-warning/40 bg-warning/5 px-3 py-2 text-xs text-warning">
                {item.review_note}
              </p>
            )}
            {item.missing_fields.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-muted-foreground">missing:</span>
                {item.missing_fields.map((f) => (
                  <Badge key={f} variant="outline" className="text-[10px]">
                    {f}
                  </Badge>
                ))}
              </div>
            )}
            <details className="rounded-lg border px-3 py-2">
              <summary className="cursor-pointer text-xs text-muted-foreground">
                Evidence quotes ({Object.keys(item.evidence).length})
              </summary>
              <dl className="mt-2 space-y-1.5">
                {Object.entries(item.evidence).map(([field, quote]) => (
                  <div key={field}>
                    <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                      {field}
                    </dt>
                    <dd className="mt-0.5 font-mono text-[11px] leading-snug">
                      “{String(quote)}”
                    </dd>
                  </div>
                ))}
              </dl>
            </details>

            {editingId === item.id && form ? (
              <div className="space-y-3 rounded-lg border p-3">
                <p className="text-xs font-semibold text-muted-foreground">
                  Edit the fields, then Save & promote. The publish gate re-checks everything before it goes live.
                </p>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {(
                    [
                      ["total_vacancies", "Total vacancies"],
                      ["min_age", "Min age"],
                      ["age_max_general", "Max age (general)"],
                      ["age_cutoff_date", "Age cutoff date"],
                      ["application_last_date", "Last date"],
                      ["pay_level", "Pay level"],
                    ] as const
                  ).map(([key, label]) => (
                    <div key={key} className="space-y-1">
                      <Label className="text-[10px]">{label}</Label>
                      <Input
                        className="h-8 text-xs"
                        value={form[key as keyof EditForm]}
                        onChange={(e) =>
                          setForm({ ...form, [key]: e.target.value } as EditForm)
                        }
                      />
                    </div>
                  ))}
                  <div className="col-span-2 space-y-1 sm:col-span-4">
                    <Label className="text-[10px]">Qualification</Label>
                    <Input
                      className="h-8 text-xs"
                      value={form.required_qualification}
                      onChange={(e) => setForm({ ...form, required_qualification: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={() => void saveEdit(item)}
                    disabled={actionId === item.id}
                    className="gap-1.5"
                  >
                    {actionId === item.id ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Check className="size-3.5" />
                    )}
                    Save & promote
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setEditingId(null);
                      setForm(null);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => void act(item, "approve")}
                  disabled={actionId === item.id}
                  className="gap-1.5"
                >
                  {actionId === item.id ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Check className="size-3.5" />
                  )}
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditingId(item.id);
                    setForm(emptyForm(item));
                  }}
                  disabled={actionId === item.id}
                  className="gap-1.5"
                >
                  <Pencil className="size-3.5" /> Edit
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => void act(item, "reject")}
                  disabled={actionId === item.id}
                  className="gap-1.5 text-destructive"
                >
                  <X className="size-3.5" /> Reject
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
