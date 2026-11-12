import { motion } from "framer-motion";
import {
  BrainCircuit,
  CheckCircle2,
  Circle,
  Target,
  Flame,
  AlertCircle,
  Sparkles,
  TrendingUp,
} from "lucide-react";
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

  // Map topic name to mastery record for quick lookup
  const masteryMap = (masteryData?.topics || []).reduce(
    (acc, item) => {
      acc[item.topic.toLowerCase().trim()] = item;
      return acc;
    },
    {} as Record<string, TopicMasteryItem>,
  );

  // Calculate high-level preparation readiness metrics
  const allMasteryRecords = masteryData?.topics || [];
  const masteredCount = allMasteryRecords.filter((t) => t.status === "Mastered").length;
  const needsRevisionCount = allMasteryRecords.filter((t) => t.status === "Needs Revision").length;
  const moderateCount = allMasteryRecords.filter((t) => t.status === "Moderate").length;

  const averageAccuracy =
    allMasteryRecords.length > 0
      ? Math.round(
          (allMasteryRecords.reduce((sum, t) => sum + (t.accuracy_ema || 0), 0) /
            allMasteryRecords.length) *
            100,
        )
      : 0;

  // Find lowest EMA topic for the "Fix Weak Area" shortcut
  const weakestTopic = [...allMasteryRecords].sort(
    (a, b) => (a.accuracy_ema || 0) - (b.accuracy_ema || 0),
  )[0];

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
      className="space-y-6"
    >
      {/* 1. Preparation Readiness & Mastery Analytics Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <Card className="bg-card/60 border-primary/30 p-4 flex flex-col justify-between">
          <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
            <TrendingUp className="size-3.5 text-primary" /> Topic Readiness EMA
          </span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-display">{averageAccuracy}%</span>
            <span className="text-[11px] text-muted-foreground">
              {allMasteryRecords.length} topics tested
            </span>
          </div>
          <Progress value={averageAccuracy} className="h-1.5 mt-2" />
        </Card>

        <Card className="bg-card/60 border-border/60 p-4 flex flex-col justify-between">
          <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
            <Flame className="size-3.5 text-emerald-400" /> Mastered Topics
          </span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-display text-emerald-400">
              {masteredCount}
            </span>
            <span className="text-[11px] text-muted-foreground">High accuracy</span>
          </div>
          <span className="text-[10px] text-muted-foreground mt-1">Ready for exam speed</span>
        </Card>

        <Card className="bg-card/60 border-border/60 p-4 flex flex-col justify-between">
          <span className="text-xs text-muted-foreground font-medium flex items-center gap-1.5">
            <AlertCircle className="size-3.5 text-destructive" /> Needs Revision
          </span>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-display text-destructive">
              {needsRevisionCount}
            </span>
            <span className="text-[11px] text-muted-foreground">{moderateCount} moderate</span>
          </div>
          <span className="text-[10px] text-muted-foreground mt-1">Accuracy below target</span>
        </Card>

        <Card className="bg-primary/5 border-primary/40 p-4 flex flex-col justify-between">
          <span className="text-xs font-semibold text-primary flex items-center gap-1">
            <Sparkles className="size-3.5" /> Recommended Drill
          </span>
          {weakestTopic ? (
            <div className="mt-1">
              <p className="text-xs font-bold truncate text-foreground">{weakestTopic.topic}</p>
              <p className="text-[10px] text-muted-foreground">
                Accuracy: {Math.round((weakestTopic.accuracy_ema || 0) * 100)}%
              </p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">Start practicing drills</p>
          )}
          <Button
            size="sm"
            className="w-full h-7 mt-2 text-xs rounded-lg gap-1.5"
            disabled={!weakestTopic && allMasteryRecords.length === 0}
            onClick={() => {
              const target = weakestTopic || {
                topic: "Percentage",
                subject: "Quantitative Aptitude",
              };
              if (onPracticeTopic) {
                onPracticeTopic(target.topic, target.subject);
              }
            }}
          >
            <BrainCircuit className="size-3" />
            Fix Weak Area
          </Button>
        </Card>
      </div>

      {/* 2. Main Roadmap Card */}
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

                      {/* Interactive Topic Badges with Drill Action */}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {week.topics.map((topic, tIdx) => {
                          const isMicroRevision =
                            topic.startsWith("[Micro-Revision]") ||
                            topic.startsWith("[High Priority]");

                          return (
                            <div
                              key={tIdx}
                              className={cn(
                                "flex items-center gap-1.5 rounded-lg border py-1 pl-2.5 pr-1.5 text-xs shadow-sm transition-colors",
                                isMicroRevision
                                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300 font-medium"
                                  : "border-border/60 bg-background/80 text-muted-foreground",
                              )}
                            >
                              <span>{topic}</span>
                              {renderMasteryBadge(topic)}
                              {onPracticeTopic && (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  className={cn(
                                    "h-5 px-1.5 text-[11px] font-semibold rounded",
                                    isMicroRevision
                                      ? "text-amber-400 hover:bg-amber-500/20 hover:text-amber-300"
                                      : "text-primary hover:bg-primary/10 hover:text-primary",
                                  )}
                                  title={`Start drill for ${topic}`}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    const cleanTopic = topic.replace(/^\[.*?\]\s*/, "");
                                    onPracticeTopic(cleanTopic, week.focus_subject);
                                  }}
                                >
                                  <BrainCircuit className="mr-1 size-3" />
                                  Drill
                                </Button>
                              )}
                            </div>
                          );
                        })}
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