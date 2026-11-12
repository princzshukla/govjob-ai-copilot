import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Loader2, Sparkles, Upload } from "lucide-react";
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

const DOMICILE_STATES = [
  "Andhra Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Delhi",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Tamil Nadu",
  "Telangana",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
  "Other",
];

const DEGREE_OPTIONS = [
  { label: "10th Pass (Matriculation)", value: "10th" },
  { label: "12th Pass (Intermediate / HSC)", value: "12th" },
  { label: "BCA (Bachelor of Computer Applications)", value: "BCA" },
  { label: "B.Tech / B.E.", value: "B.Tech" },
  { label: "B.Sc", value: "B.Sc" },
  { label: "B.Com", value: "B.Com" },
  { label: "B.A.", value: "B.A." },
  { label: "BBA", value: "BBA" },
  { label: "MCA / M.Tech / M.Sc (Post Graduate)", value: "MCA" },
];

const STREAM_OPTIONS_12TH = [
  "PCM (Physics, Chemistry, Maths)",
  "PCB (Physics, Chemistry, Biology)",
  "Commerce",
  "Arts / Humanities",
  "General",
];

const GRADUATION_STATUS_OPTIONS = ["Completed", "Final Year / Appearing"];

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
  const [isManual, setIsManual] = useState(false);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setIsManual(false);
    onUpload(file);
  };

  const handleManualStart = () => {
    setIsManual(true);
    setFileName(null);
    onFieldChange("full_name", profile?.full_name || "Candidate");
    onFieldChange("highest_degree", profile?.highest_degree || "12th");
    onFieldChange("stream", profile?.stream || "PCM (Physics, Chemistry, Maths)");
    onFieldChange("dob", ((profile as Record<string, unknown>)?.["dob"] as string) || "2004-06-10");
    onFieldChange("category", profile?.category || "General");
    onFieldChange(
      "graduation_status",
      ((profile as Record<string, unknown>)?.["graduation_status"] as string) || "Completed",
    );
    onFieldChange(
      "percentage_cgpa",
      profile?.percentage_cgpa ? String(profile.percentage_cgpa) : "75",
    );
  };

  const stringValue = (field: string) => {
    const value = (profile as Record<string, unknown> | null)?.[field];
    return value === null || value === undefined ? "" : String(value);
  };

  const selectedDegree = stringValue("highest_degree");
  const isSchoolLevel = selectedDegree === "12th" || selectedDegree === "10th";

  const handleDegreeChange = (val: string) => {
    onFieldChange("highest_degree", val);
    if (val === "12th" || val === "10th") {
      onFieldChange("graduation_status", "Completed");
      if (!stringValue("stream")) {
        onFieldChange("stream", "PCM (Physics, Chemistry, Maths)");
      }
    }
  };

  const showProfileForm = Boolean(profile || isManual);

  return (
    <div className="space-y-6">
      {/* Step 1: Upload resume or Manual Entry */}
      <Card className="overflow-hidden border-dashed">
        <CardHeader className="py-4 px-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-3 max-w-xl">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Upload className="size-5" />
              </span>
              <div>
                <CardTitle className="text-lg">Upload Your Resume (PDF)</CardTitle>
                <CardDescription className="mt-1">
                  We extract your qualifications and only ask for missing government-specific
                  criteria, or you can enter details manually.
                </CardDescription>
              </div>
            </div>

            {/* Buttons pushed right with reduced padding */}
            <div className="flex flex-wrap items-center justify-end gap-2 shrink-0">
              <label
                className={cn(
                  "group relative inline-flex cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-xl bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground transition hover:bg-primary/90",
                  loading && "pointer-events-none opacity-80",
                )}
              >
                {loading && !profile ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Upload className="size-3.5" />
                )}
                <span>{profile && !isManual ? "Upload Another Resume" : "Select Resume PDF"}</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={handleFile}
                />
              </label>

              <Button
                type="button"
                variant="outline"
                onClick={handleManualStart}
                className="inline-flex h-auto items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold"
              >
                <FileText className="size-3.5" />
                <span>Enter Details Manually</span>
              </Button>
            </div>
          </div>

          {fileName && (
            <p className="mt-2 truncate text-xs text-muted-foreground">
              Selected file: <span className="font-medium text-foreground">{fileName}</span>
            </p>
          )}
        </CardHeader>
      </Card>

      {/* Step 2: Review extracted profile & fill missing fields */}
      {showProfileForm && (
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
                {stringValue("full_name") || (isManual ? "Manual Entry" : "Candidate Profile")}
              </Badge>
            </CardHeader>

            <CardContent className="space-y-6 pt-5">
              {!isManual && missingFields.length > 0 && (
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

              {isManual && (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Full Name *</Label>
                    <Input
                      type="text"
                      required
                      placeholder="e.g. Candidate Name"
                      value={stringValue("full_name")}
                      onChange={(e) => onFieldChange("full_name", e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">
                      {isSchoolLevel
                        ? "12th / 10th Percentage (%) *"
                        : "Graduation Percentage / CGPA *"}
                    </Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      required
                      placeholder="e.g. 75.0"
                      value={stringValue("percentage_cgpa")}
                      onChange={(e) => onFieldChange("percentage_cgpa", e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">
                      {isSchoolLevel ? "Qualification Status" : "Graduation Status *"}
                    </Label>
                    <Select
                      value={stringValue("graduation_status") || "Completed"}
                      onValueChange={(value) => onFieldChange("graduation_status", value)}
                      disabled={isSchoolLevel}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {GRADUATION_STATUS_OPTIONS.map((status) => (
                          <SelectItem key={status} value={status}>
                            {status}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs text-muted-foreground">Domicile State *</Label>
                    <Select
                      value={stringValue("domicile_state")}
                      onValueChange={(value) => onFieldChange("domicile_state", value)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select State" />
                      </SelectTrigger>
                      <SelectContent>
                        {DOMICILE_STATES.map((state) => (
                          <SelectItem key={state} value={state}>
                            {state}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Core qualification fields */}
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Highest Qualification *</Label>
                  {isManual ? (
                    <Select value={selectedDegree || "12th"} onValueChange={handleDegreeChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select Qualification" />
                      </SelectTrigger>
                      <SelectContent>
                        {DEGREE_OPTIONS.map((deg) => (
                          <SelectItem key={deg.value} value={deg.value}>
                            {deg.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      type="text"
                      required
                      value={selectedDegree}
                      onChange={(e) => onFieldChange("highest_degree", e.target.value)}
                    />
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">
                    {isSchoolLevel ? "12th Stream / Subjects *" : "Stream / Specialization *"}
                  </Label>
                  {isManual && isSchoolLevel ? (
                    <Select
                      value={stringValue("stream") || "PCM (Physics, Chemistry, Maths)"}
                      onValueChange={(val) => onFieldChange("stream", val)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select 12th Stream" />
                      </SelectTrigger>
                      <SelectContent>
                        {STREAM_OPTIONS_12TH.map((st) => (
                          <SelectItem key={st} value={st}>
                            {st}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      type="text"
                      required
                      placeholder="e.g. Computer Science"
                      value={stringValue("stream")}
                      onChange={(e) => onFieldChange("stream", e.target.value)}
                    />
                  )}
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Date of Birth *</Label>
                  <Input
                    type="date"
                    required
                    value={stringValue("dob")}
                    onChange={(e) => onFieldChange("dob", e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Category *</Label>
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