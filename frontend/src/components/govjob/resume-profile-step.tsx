import { useState } from "react";
import { motion } from "framer-motion";
import { Loader2, Sparkles, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { CandidateProfile, MissingFieldPrompt } from "@/types/govjob";

interface ResumeProfileStepProps {
  loading: boolean;
  submitting: boolean;
  profile: CandidateProfile | null;
  missingFields: MissingFieldPrompt[];
  statusMessage: string;
  onUpload: (file: File) => void;
  onFieldChange: (field: string, value: string) => void;
  onSubmit: () => void;
}

const CATEGORY_OPTIONS = ["General", "OBC-NCL", "EWS", "SC", "ST"];

export function ResumeProfileStep({
  loading,
  submitting,
  profile,
  missingFields,
  statusMessage,
  onUpload,
  onFieldChange,
  onSubmit,
}: ResumeProfileStepProps) {
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    onUpload(file);
  };

  const stringValue = (field: string) => {
    const value = profile?.[field];
    return value === null || value === undefined ? "" : String(value);
  };

  return (
    <div className="space-y-6">
      {/* Step 1: Upload resume */}
      <Card className="overflow-hidden border-dashed">
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-3">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Upload className="size-5" />
              </span>
              <div>
                <CardTitle className="text-lg">Upload Your Resume (PDF)</CardTitle>
                <CardDescription className="mt-1">
                  We extract your qualifications and only ask for missing government-specific
                  criteria.
                </CardDescription>
              </div>
            </div>
            <label
              className={cn(
                "group relative inline-flex cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90",
                loading && "pointer-events-none opacity-80",
              )}
            >
              {loading && !profile ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Upload className="size-4" />
              )}
              <span>{profile ? "Upload Another Resume" : "Select Resume PDF"}</span>
              <input
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleFile}
              />
            </label>
          </div>
          {fileName && (
            <p className="mt-3 truncate text-xs text-muted-foreground">
              Selected file: <span className="font-medium text-foreground">{fileName}</span>
            </p>
          )}
        </CardHeader>
      </Card>

      {/* Step 2: Review extracted profile & fill missing fields */}
      {profile && (
        <motion.form
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          onSubmit={(e) => {
            e.preventDefault();
            onSubmit();
          }}
        >
          <Card>
            <CardHeader className="flex-row items-start justify-between gap-3 space-y-0 border-b pb-4">
              <div>
                <CardTitle className="text-lg">Complete Statutory Eligibility Profile</CardTitle>
                {statusMessage && (
                  <CardDescription className="mt-1 text-warning">{statusMessage}</CardDescription>
                )}
              </div>
              <Badge variant="secondary" className="shrink-0">
                {profile.full_name || "Candidate Profile"}
              </Badge>
            </CardHeader>

            <CardContent className="space-y-6 pt-5">
              {missingFields.length > 0 && (
                <div className="space-y-4 rounded-xl border border-warning/40 bg-warning/10 p-5">
                  <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-warning">
                    <Sparkles className="size-4" />
                    Missing details required for government exams
                  </h3>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {missingFields.map((item) => (
                      <div key={item.field_name} className="space-y-1.5">
                        <Label className="text-sm font-medium">{item.label} *</Label>
                        <p className="text-xs text-muted-foreground">{item.question}</p>
                        {item.input_type === "select" && item.options ? (
                          <Select
                            required
                            value={stringValue(item.field_name)}
                            onValueChange={(value) => onFieldChange(item.field_name, value)}
                          >
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder={`Select ${item.label}`} />
                            </SelectTrigger>
                            <SelectContent>
                              {item.options.map((opt) => (
                                <SelectItem key={opt} value={opt}>
                                  {opt}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Input
                            required
                            type={item.input_type}
                            step={item.input_type === "number" ? "0.01" : undefined}
                            value={stringValue(item.field_name)}
                            onChange={(e) => onFieldChange(item.field_name, e.target.value)}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted fields summary (editable) */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Highest Degree</Label>
                  <Input
                    type="text"
                    value={stringValue("highest_degree")}
                    onChange={(e) => onFieldChange("highest_degree", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Stream / Specialization</Label>
                  <Input
                    type="text"
                    value={stringValue("stream")}
                    onChange={(e) => onFieldChange("stream", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Date of Birth</Label>
                  <Input
                    type="date"
                    required
                    value={stringValue("dob")}
                    onChange={(e) => onFieldChange("dob", e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Category</Label>
                  <Select
                    value={stringValue("category") || "General"}
                    onValueChange={(value) => onFieldChange("category", value)}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORY_OPTIONS.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <Button
                  type="submit"
                  size="lg"
                  disabled={submitting}
                  className="gap-2 rounded-xl font-semibold"
                >
                  {submitting ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  Find Eligible Government Jobs
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.form>
      )}
    </div>
  );
}
