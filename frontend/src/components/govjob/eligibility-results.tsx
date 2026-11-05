import { motion } from "framer-motion";
import { BookOpen, ChevronRight, ExternalLink, Loader2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { ExamMatchResult, EligibilityCheckResponse } from "@/types/govjob";

interface EligibilityResultsProps {
  eligibility: EligibilityCheckResponse | null;
  primaryExamId: string;
  targetWeeks: number;
  roadmapExamId: string | null;
  onTargetWeeksChange: (weeks: number) => void;
  onOpenJob: (exam: ExamMatchResult) => void;
  onRoadmap: (exam: ExamMatchResult) => void;
  onSwitchPrimary: (examId: string) => void;
}

export function EligibilityResults({
  eligibility,
  primaryExamId,
  targetWeeks,
  roadmapExamId,
  onTargetWeeksChange,
  onOpenJob,
  onRoadmap,
  onSwitchPrimary,
}: EligibilityResultsProps) {
  if (!eligibility) return null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h2 className="flex items-center gap-2 font-display text-2xl font-bold">
          Matched Government Exams ({eligibility.eligible_now.length})
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Roadmap duration:</span>
          <Select value={String(targetWeeks)} onValueChange={(v) => onTargetWeeksChange(Number(v))}>
            <SelectTrigger className="w-[220px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="8">8 Weeks (Crash Course)</SelectItem>
              <SelectItem value="12">12 Weeks (Standard)</SelectItem>
              <SelectItem value="24">24 Weeks (Comprehensive)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
        {eligibility.eligible_now.map((exam, idx) => (
          <motion.div
            key={exam.exam_id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: idx * 0.06, ease: "easeOut" }}
          >
            <Card
              onClick={() => onOpenJob(exam)}
              className={cn(
                "flex h-full cursor-pointer flex-col justify-between gap-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-primary/10",
                primaryExamId === exam.exam_id
                  ? "border-warning/60 shadow-md shadow-warning/10"
                  : "hover:border-primary/50",
              )}
            >
              <CardContent className="flex h-full flex-col justify-between gap-4 p-5">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <Badge variant="secondary">{exam.post_type}</Badge>
                    {exam.syllabus_overlap_pct != null && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSwitchPrimary(exam.exam_id);
                        }}
                        className={cn(
                          "shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold transition",
                          primaryExamId === exam.exam_id
                            ? "border-warning/60 bg-warning/15 text-warning"
                            : "border-success/40 bg-success/10 text-success hover:border-success",
                        )}
                      >
                        {primaryExamId === exam.exam_id
                          ? "★ Primary Target"
                          : `${exam.syllabus_overlap_pct}% Overlap (Set Primary)`}
                      </button>
                    )}
                  </div>
                  <div>
                    <h3 className="font-display text-lg font-bold transition-colors hover:text-primary">
                      {exam.title}
                    </h3>
                    <p className="text-sm text-muted-foreground">{exam.organizing_body}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-2 rounded-xl border bg-muted/50 p-3 text-xs">
                    <div>
                      <span className="block text-muted-foreground">Your Age at Cutoff:</span>
                      <span className="font-medium">
                        {exam.candidate_age_at_cutoff} yrs (Max: {exam.max_allowed_age})
                      </span>
                    </div>
                    <div>
                      <span className="block text-muted-foreground">Form Deadline:</span>
                      <span className="font-semibold text-warning">
                        {exam.application_deadline}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-2 pt-1 sm:flex-row">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={roadmapExamId === exam.exam_id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onRoadmap(exam);
                    }}
                    className="flex-1 gap-2 rounded-xl"
                  >
                    {roadmapExamId === exam.exam_id ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <BookOpen className="size-4" />
                    )}
                    <span>Roadmap</span>
                    <ChevronRight className="size-4" />
                  </Button>

                  {exam.official_pdf_url && (
                    <Button
                      type="button"
                      variant="secondary"
                      asChild
                      className="flex-1 rounded-xl"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <a href={exam.official_pdf_url} target="_blank" rel="noopener noreferrer">
                        <span>Apply</span>
                        <ExternalLink className="size-4" />
                      </a>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Collapsible ineligible exams */}
      {eligibility.ineligible.length > 0 && (
        <Collapsible>
          <Card className="overflow-hidden">
            <CollapsibleTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 p-4 text-left transition hover:bg-accent/50"
              >
                <div className="flex items-center gap-2.5">
                  <span className="flex size-9 items-center justify-center rounded-lg border border-destructive/30 bg-destructive/10">
                    <XCircle className="size-4 text-destructive" />
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold">
                      Unmatched Examinations ({eligibility.ineligible.length})
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      Statutory criteria requirements that were not met
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className="shrink-0">
                  View Reasons
                </Badge>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="border-t p-4 pt-4">
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {eligibility.ineligible.map((ex) => (
                    <div
                      key={ex.exam_id}
                      className="flex flex-col justify-between gap-2.5 rounded-xl border bg-muted/40 p-4"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <h4 className="text-sm font-semibold">{ex.title}</h4>
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            {ex.organizing_body}
                          </p>
                        </div>
                        <Badge variant="outline" className="shrink-0 text-[10px] uppercase">
                          {ex.post_type}
                        </Badge>
                      </div>
                      <div className="space-y-1.5 pt-1">
                        {ex.reasons_failed.map((reason, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 rounded-lg border border-destructive/25 bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive"
                          >
                            <span className="shrink-0 font-bold">•</span>
                            <span>{reason}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}
    </div>
  );
}
