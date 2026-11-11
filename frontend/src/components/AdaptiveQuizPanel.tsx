import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  BrainCircuit,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  RotateCcw,
  HelpCircle,
  XCircle,
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api/v1/adaptive";

const TOPICS = [
  { subject: "Quantitative Aptitude", topic: "Percentage" },
  { subject: "Quantitative Aptitude", topic: "Profit and Loss" },
  { subject: "Quantitative Aptitude", topic: "Time and Work" },
  { subject: "General Intelligence & Reasoning", topic: "Coding-Decoding" },
  { subject: "General Intelligence & Reasoning", topic: "Syllogism" },
];

export function AdaptiveQuizPanel({
  initialExamId = "ssc-cgl-tier1",
  initialTopic = "Percentage",
  initialSubject = "Quantitative Aptitude",
}: {
  initialExamId?: string;
  initialTopic?: string;
  initialSubject?: string;
}) {
  const [selectedTopic, setSelectedTopic] = useState(initialTopic);
  const [selectedSubject, setSelectedSubject] = useState(initialSubject);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, { option: string; time: number }>>({});
  const [secondsSpent, setSecondsSpent] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sync state if props change (e.g. from clicking Drill in Roadmap)
  useEffect(() => {
    setSelectedTopic(initialTopic);
    setSelectedSubject(initialSubject);
    setCurrentIndex(0);
    setAnswers({});
  }, [initialTopic, initialSubject]);

  const { data: quiz, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["adaptive-quiz", initialExamId, selectedTopic],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/quiz?exam_id=${encodeURIComponent(initialExamId)}&subject=${encodeURIComponent(selectedSubject)}&topic=${encodeURIComponent(selectedTopic)}&count=3`
      );
      if (!res.ok) throw new Error("Failed to load quiz");
      return res.json();
    },
    staleTime: 1000 * 60 * 5,
  });

  const submitMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await fetch(`${API_BASE}/submit-quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Submission failed");
      return res.json();
    },
  });

  useEffect(() => {
    setSecondsSpent(0);
    timerRef.current = setInterval(() => {
      setSecondsSpent((s) => s + 1);
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [currentIndex, selectedTopic]);

  const handleTopicChange = (topicObj: { subject: string; topic: string }) => {
    setSelectedTopic(topicObj.topic);
    setSelectedSubject(topicObj.subject);
    setCurrentIndex(0);
    setAnswers({});
    submitMutation.reset();
  };

  const handleReset = () => {
    setCurrentIndex(0);
    setAnswers({});
    submitMutation.reset();
    refetch();
  };

  if (isLoading || isFetching) {
    return (
      <Card className="border-border/50 bg-card/60 backdrop-blur">
        <CardContent className="flex flex-col items-center justify-center py-16 gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <p className="text-sm text-muted-foreground">Generating adaptive drill for {selectedTopic}...</p>
        </CardContent>
      </Card>
    );
  }

  if (error || !quiz?.questions?.length) {
    return (
      <Card className="border-border/50 bg-card/60">
        <CardContent className="p-8 text-center space-y-4">
          <p className="text-destructive text-sm">Failed to load quiz from backend. Ensure FastAPI is running on port 8000.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>Try Again</Button>
        </CardContent>
      </Card>
    );
  }

  const currentQ = quiz.questions[currentIndex];
  const isLast = currentIndex === quiz.questions.length - 1;

  const handleSelectOption = (key: string) => {
    setAnswers((prev) => ({
      ...prev,
      [currentQ.id]: { option: key, time: secondsSpent },
    }));
  };

  const handleSubmit = () => {
    submitMutation.mutate({
      user_id: "usr_demo_001",
      exam_id: initialExamId,
      topic: selectedTopic,
      answers: Object.entries(answers).map(([qId, val]) => ({
        question_id: qId,
        selected_option: val.option,
        time_taken_sec: val.time || 1,
      })),
    });
  };

  return (
    <Card className="border-border/50 bg-card/60 backdrop-blur">
      <CardHeader className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg">AI Adaptive Topic Drill</CardTitle>
              <p className="text-xs text-muted-foreground">
                Targeted practice with real-time diagnostic evaluation
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {TOPICS.map((t) => (
              <Button
                key={t.topic}
                variant={selectedTopic === t.topic ? "default" : "outline"}
                size="sm"
                className="text-xs h-7 px-2.5"
                onClick={() => handleTopicChange(t)}
              >
                {t.topic}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {submitMutation.data ? (
          /* Comprehensive Evaluation & Solutions Breakdown */
          <div className="space-y-6 py-2">
            <div className="flex items-center gap-2 text-emerald-400 font-semibold">
              <CheckCircle2 className="h-5 w-5" />
              <span>Drill Evaluated — {selectedTopic}</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
              <div className="p-4 rounded-xl bg-muted/40 border border-border/50">
                <span className="text-xs text-muted-foreground uppercase">Accuracy</span>
                <p className="text-2xl font-bold mt-1">{submitMutation.data.accuracy_pct}%</p>
              </div>
              <div className="p-4 rounded-xl bg-muted/40 border border-border/50">
                <span className="text-xs text-muted-foreground uppercase">Score</span>
                <p className="text-2xl font-bold mt-1">
                  {submitMutation.data.correct_count} / {submitMutation.data.total_attempted}
                </p>
              </div>
              <div className="p-4 rounded-xl bg-muted/40 border border-border/50">
                <span className="text-xs text-muted-foreground uppercase">Mastery Status</span>
                <p className="text-2xl font-bold text-primary mt-1">{submitMutation.data.topic_status}</p>
              </div>
            </div>

            {submitMutation.data.diagnostics?.length > 0 && (
              <div className="space-y-2.5">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4" />
                  Diagnostic Insights
                </h4>
                {submitMutation.data.diagnostics.map((d: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-sm">
                    <span className="font-semibold">{d.sub_topic}:</span> {d.mistake_type}
                  </div>
                ))}
              </div>
            )}

            {/* Step-by-Step Question Solutions */}
            <div className="space-y-4 pt-2">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-primary" />
                Detailed Question Explanations
              </h4>
              <div className="space-y-3">
                {quiz.questions.map((q: any, idx: number) => {
                  const userAnswer = answers[q.id]?.option;
                  const isCorrect = userAnswer === q.correct_option;
                  const timeSpent = answers[q.id]?.time || 0;

                  return (
                    <div
                      key={q.id}
                      className="p-4 rounded-xl border border-border/60 bg-muted/20 space-y-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2 font-medium">
                          {isCorrect ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                          ) : (
                            <XCircle className="h-4 w-4 text-destructive shrink-0" />
                          )}
                          <span>Q{idx + 1}. {q.question}</span>
                        </div>
                        <Badge variant="outline" className="text-[10px] shrink-0 font-mono">
                          {timeSpent}s / {q.expected_time_sec}s
                        </Badge>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        {Object.entries(q.options).map(([k, text]) => {
                          const isUserChoice = userAnswer === k;
                          const isRightChoice = q.correct_option === k;

                          let badgeStyle = "border-border/60 text-muted-foreground";
                          if (isRightChoice) {
                            badgeStyle = "border-emerald-500/50 bg-emerald-500/10 text-emerald-400 font-semibold";
                          } else if (isUserChoice && !isRightChoice) {
                            badgeStyle = "border-destructive/50 bg-destructive/10 text-destructive";
                          }

                          return (
                            <div key={k} className={`p-2 rounded-lg border flex items-center gap-2 ${badgeStyle}`}>
                              <span className="font-bold">{k}.</span>
                              <span>{text as string}</span>
                            </div>
                          );
                        })}
                      </div>

                      {q.explanation && (
                        <div className="p-3 rounded-lg bg-background/60 border border-border/40 text-xs text-muted-foreground space-y-1">
                          <strong className="text-foreground">Solution:</strong>
                          <p>{q.explanation}</p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <Button onClick={handleReset} className="w-full gap-2">
              <RotateCcw className="h-4 w-4" /> Practice Another Drill
            </Button>
          </div>
        ) : (
          /* Active Question View */
          <div className="space-y-5">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{currentQ.difficulty}</Badge>
                <span className="text-muted-foreground">{currentQ.sub_topic}</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />
                <span>{secondsSpent}s (Expected: {currentQ.expected_time_sec}s)</span>
              </div>
            </div>

            <Progress value={((currentIndex + 1) / quiz.total_questions) * 100} className="h-1.5" />

            <p className="text-base font-medium leading-relaxed pt-1">
              Q{currentIndex + 1}. {currentQ.question}
            </p>

            <div className="grid grid-cols-1 gap-2.5">
              {Object.entries(currentQ.options).map(([key, text]) => {
                const isSelected = answers[currentQ.id]?.option === key;
                return (
                  <button
                    key={key}
                    onClick={() => handleSelectOption(key)}
                    className={`w-full text-left p-3.5 rounded-xl border text-sm transition-all flex items-start gap-3 ${
                      isSelected
                        ? "border-primary bg-primary/15 font-medium"
                        : "border-border/60 hover:bg-muted/40"
                    }`}
                  >
                    <span className="font-semibold">{key}.</span>
                    <span>{text as string}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex justify-between items-center pt-3">
              <Button
                variant="ghost"
                disabled={currentIndex === 0}
                onClick={() => setCurrentIndex((i) => i - 1)}
              >
                Previous
              </Button>

              {isLast ? (
                <Button
                  onClick={handleSubmit}
                  disabled={!answers[currentQ.id] || submitMutation.isPending}
                >
                  {submitMutation.isPending ? "Evaluating..." : "Submit Drill"}
                </Button>
              ) : (
                <Button
                  disabled={!answers[currentQ.id]}
                  onClick={() => setCurrentIndex((i) => i + 1)}
                  className="gap-1.5"
                >
                  Next <ArrowRight className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}