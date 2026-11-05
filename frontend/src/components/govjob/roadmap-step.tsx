import { motion } from "framer-motion";
import { CheckCircle2, Circle, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { StudyRoadmapResponse } from "@/types/govjob";

interface RoadmapStepProps {
  roadmap: StudyRoadmapResponse | null;
  completedWeeks: Record<number, boolean>;
  onToggleWeek: (weekNumber: number) => void;
}

export function RoadmapStep({ roadmap, completedWeeks, onToggleWeek }: RoadmapStepProps) {
  if (!roadmap) return null;

  const total = roadmap.weekly_breakdown.length;
  const done = roadmap.weekly_breakdown.filter((w) => completedWeeks[w.week_number]).length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <Card className="border-primary/40">
        <CardHeader className="flex-col items-start gap-4 space-y-0 border-b pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">
              AI Personalized Preparation Plan
            </span>
            <CardTitle className="mt-1 font-display text-2xl font-bold">
              {roadmap.exam_name} ({roadmap.total_duration_weeks} Weeks)
            </CardTitle>
            <p className="mt-2 max-w-md rounded-xl border bg-muted/50 p-3 text-xs text-muted-foreground">
              <strong className="text-foreground">Strategy:</strong> {roadmap.revision_strategy}
            </p>
          </div>
          <div className="w-full md:w-64">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 font-medium text-muted-foreground">
                <Target className="size-3.5 text-primary" />
                Progress
              </span>
              <span className="font-semibold">
                {done}/{total} weeks · {pct}%
              </span>
            </div>
            <Progress value={pct} className="h-2" />
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-5">
          {roadmap.weekly_breakdown.map((week, idx) => {
            const isDone = !!completedWeeks[week.week_number];
            return (
              <motion.div
                key={week.week_number}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: Math.min(idx * 0.03, 0.4) }}
              >
                <button
                  type="button"
                  onClick={() => onToggleWeek(week.week_number)}
                  className={cn(
                    "w-full cursor-pointer rounded-xl border p-5 text-left transition-all duration-200",
                    isDone
                      ? "border-success/50 bg-success/10 opacity-80"
                      : "bg-muted/30 hover:border-primary/40 hover:bg-muted/50",
                  )}
                >
                  <div className="flex items-start gap-3">
                    {isDone ? (
                      <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" />
                    ) : (
                      <Circle className="mt-0.5 size-5 shrink-0 text-muted-foreground/50" />
                    )}
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold">Week {week.week_number}:</span>
                        <span className="font-medium text-primary">{week.focus_subject}</span>
                        <Badge variant="secondary" className="text-[10px] uppercase">
                          {week.phase}
                        </Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {week.topics.map((topic, tIdx) => (
                          <span
                            key={tIdx}
                            className="rounded-md border bg-background/60 px-2.5 py-1 text-xs text-muted-foreground"
                          >
                            {topic}
                          </span>
                        ))}
                      </div>
                      <p className="mt-3 text-xs text-success">
                        <strong>Goal:</strong> {week.practice_goal}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        <strong className="text-foreground/80">Resources:</strong>{" "}
                        {week.recommended_resources.join(", ")}
                      </p>
                    </div>
                  </div>
                </button>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    </motion.div>
  );
}
