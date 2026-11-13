import { createFileRoute } from "@tanstack/react-router";
import { queryOptions, useSuspenseQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle, Clock, ArrowRight } from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api/v1/adaptive";

// 1. TanStack Query QueryOptions for route prefetching
const quizQueryOptions = (examId: string, topic: string) =>
  queryOptions({
    queryKey: ["adaptive-quiz", examId, topic],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/quiz?exam_id=${encodeURIComponent(examId)}&subject=Quantitative%20Aptitude&topic=${encodeURIComponent(topic)}&count=3`,
        { credentials: "include" },
      );
      if (!res.ok) throw new Error("Failed to load adaptive quiz");
      return res.json();
    },
    staleTime: 1000 * 60 * 5,
  });

// 2. Define TanStack Route with loader
export const Route = createFileRoute("/quiz/")({
  loader: ({ context: { queryClient }, params: { examId, topic } }: any) => {
    // If your router context includes queryClient, prefetch on hover/navigation:
    if (queryClient) {
      return queryClient.ensureQueryData(quizQueryOptions(examId, topic));
    }
  },
  component: QuizPageComponent,
});

function QuizPageComponent() {
  const { examId, topic } = Route.useParams() as { examId: string; topic: string };

  const { data: quiz } = useSuspenseQuery(quizQueryOptions(examId, topic));

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, { option: string; time: number }>>({});
  const [secondsSpent, setSecondsSpent] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Timer tracking per question
  useEffect(() => {
    setSecondsSpent(0);
    timerRef.current = setInterval(() => {
      setSecondsSpent((s) => s + 1);
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [currentIndex]);

  const submitMutation = useMutation({
    mutationFn: async (payload: any) => {
      const res = await fetch(`${API_BASE}/submit-quiz`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Submission failed");
      return res.json();
    },
  });

  const currentQ = quiz.questions[currentIndex];
  const isLast = currentIndex === quiz.questions.length - 1;

  const handleSelect = (key: string) => {
    setAnswers((prev) => ({
      ...prev,
      [currentQ.id]: { option: key, time: secondsSpent },
    }));
  };

  const handleSubmit = () => {
    submitMutation.mutate({
      exam_id: examId,
      topic: topic,
      answers: Object.entries(answers).map(([qId, val]) => ({
        question_id: qId,
        selected_option: val.option,
        time_taken_sec: val.time || 1,
      })),
    });
  };

  // Evaluation Screen
  if (submitMutation.data) {
    const res = submitMutation.data;
    return (
      <div className="px-4 py-6 sm:py-10">
        <Card className="mx-auto max-w-2xl border-border shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500 sm:h-6 sm:w-6" />
              <span className="min-w-0">Evaluation Report: {topic}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 gap-3 text-center sm:grid-cols-3 sm:gap-4">
              <div className="p-4 rounded-lg bg-muted">
                <span className="text-xs text-muted-foreground uppercase font-medium">
                  Accuracy
                </span>
                <p className="text-2xl font-bold">{res.accuracy_pct}%</p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <span className="text-xs text-muted-foreground uppercase font-medium">Score</span>
                <p className="text-2xl font-bold">
                  {res.correct_count} / {res.total_attempted}
                </p>
              </div>
              <div className="p-4 rounded-lg bg-muted">
                <span className="text-xs text-muted-foreground uppercase font-medium">Mastery</span>
                <p className="text-2xl font-bold text-primary">{res.topic_status}</p>
              </div>
            </div>

            {res.diagnostics?.length > 0 && (
              <div className="space-y-3">
                <h4 className="font-semibold text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Adaptive Diagnostics
                </h4>
                <div className="space-y-2">
                  {res.diagnostics.map((diag: any, i: number) => (
                    <div
                      key={i}
                      className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-md text-sm"
                    >
                      <span className="font-semibold">{diag.sub_topic}:</span> {diag.mistake_type}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button className="w-full" onClick={() => window.location.reload()}>
              Practice Another Set
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Active Quiz View
  return (
    <div className="mx-auto max-w-2xl space-y-4 px-4 py-6 sm:py-10">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge variant="outline">{currentQ.difficulty}</Badge>
          <span className="text-muted-foreground">{currentQ.sub_topic}</span>
        </div>
        <div className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          <span>
            {secondsSpent}s / {currentQ.expected_time_sec}s
          </span>
        </div>
      </div>

      <Progress value={((currentIndex + 1) / quiz.total_questions) * 100} className="h-2" />

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium leading-relaxed">
            {currentIndex + 1}. {currentQ.question}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {Object.entries(currentQ.options).map(([optKey, optText]) => {
            const isSelected = answers[currentQ.id]?.option === optKey;
            return (
              <button
                key={optKey}
                onClick={() => handleSelect(optKey)}
                className={`w-full text-left p-3.5 rounded-lg border text-sm transition-all flex items-start gap-3 ${
                  isSelected
                    ? "border-primary bg-primary/10 font-medium"
                    : "border-border hover:bg-muted/50"
                }`}
              >
                <span className="font-semibold uppercase">{optKey}.</span>
                <span>{optText as string}</span>
              </button>
            );
          })}

          <div className="flex justify-between items-center pt-4">
            <Button
              variant="outline"
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
                className="gap-2"
              >
                Next <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
