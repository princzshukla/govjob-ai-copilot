import { motion } from "framer-motion";
import { AlertCircle, BrainCircuit, CheckCircle2, Circle, Flame, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import type { StudyRoadmapResponse } from "@/types/govjob";
import { useTopicMastery, TopicMasteryItem } from "@/components/govjob/use-mastery";

interface RoadmapStepProps {
  roadmap: StudyRoadmapResponse | null;
  completedWeeks: Record<number, boolean>;
  onToggleWeek: (weekNumber: number) => void;
  onPracticeTopic?: (topic: string, subject: string) => void;
  examId?: string;
  userId?: string;
}

export function RoadmapStep({
  roadmap,
  completedWeeks,
  onToggleWeek,
  onPracticeTopic,
  examId = "ssc-cgl-tier1",
  userId = "usr_demo_001",
}: RoadmapStepProps) {
  if (!roadmap) return null;

  const { data: masteryData } = useTopicMastery(userId, examId);

  // Map topic name to mastery record for O(1) lookup
  const masteryMap = (masteryData?.topics || []).reduce<Record<string, TopicMasteryItem>>(
    (acc: Record<string, TopicMasteryItem>, item: TopicMasteryItem) => {
      acc[item.topic.toLowerCase().trim()] = item;
      return acc;
    },
    {},
  );

  const total = roadmap.weekly_breakdown.length;
  const done = roadmap.weekly_breakdown.filter((w) => completedWeeks[w.week_number]).length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  const renderMasteryBadge = (topic: string) => {
    const record = masteryMap[topic.toLowerCase().trim()];
    if (!record) return null;

    if (record.status === "Mastered") {
      return (
        <Badge
          variant="outline"
          className="border-emerald-500/40 bg-emerald-500/10 text-emerald-400 text-[10px] h-5 gap-1 font-mono"
        >
          <Flame className="size-2.5" />
          {Math.round(record.accuracy_ema * 100)}% Mastered
        </Badge>
      );
    }

    if (record.status === "Needs Revision") {
      return (
        <Badge
          variant="outline"
          className="border-destructive/40 bg-destructive/10 text-destructive text-[10px] h-5 gap-1 font-mono"
        >
          <AlertCircle className="size-2.5" />
          Needs Revision
        </Badge>
      );
    }

    return (
      <Badge
        variant="outline"
        className="border-primary/40 bg-primary/10 text-primary text-[10px] h-5 font-mono"
      >
        {Math.round(record.accuracy_ema * 100)}% Moderate
      </Badge>
    );
  };

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
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => onToggleWeek(week.week_number)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onToggleWeek(week.week_number);
                    }
                  }}
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
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-bold">Week {week.week_number}:</span>
                        <span className="font-medium text-primary">{week.focus_subject}</span>
                        <Badge variant="secondary" className="text-[10px] uppercase">
                          {week.phase}
                        </Badge>
                      </div>

                      {/* Topic List with Practice Drill Trigger and Real-Time Mastery Badges */}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {week.topics.map((topic, tIdx) => (
                          <div
                            key={tIdx}
                            className="flex items-center gap-1.5 rounded-lg border bg-background/80 py-1 pl-2.5 pr-1.5 text-xs text-muted-foreground shadow-sm"
                          >
                            <span>{topic}</span>
                            {renderMasteryBadge(topic)}
                            {onPracticeTopic && (
                              <Button
                                type="button"
                                size="sm"
                                variant="ghost"
                                className="h-5 px-1.5 text-[11px] font-semibold text-primary hover:bg-primary/10 hover:text-primary rounded"
                                title={`Start drill for ${topic}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onPracticeTopic(topic, week.focus_subject);
                                }}
                              >
                                <BrainCircuit className="mr-1 size-3" />
                                Drill
                              </Button>
                            )}
                          </div>
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
                </div>
              </motion.div>
            );
          })}
        </CardContent>
      </Card>
    </motion.div>
  );
}