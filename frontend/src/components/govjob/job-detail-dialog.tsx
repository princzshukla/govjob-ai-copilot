import { useEffect, useState } from "react";
import { BookOpen, ExternalLink, Loader2, MailCheck, Smartphone, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ExamMatchResult } from "@/types/govjob";

interface JobDetailDialogProps {
  exam: ExamMatchResult | null;
  telegramLinked: boolean;
  telegramCode: string | null;
  telegramBotUsername: string;
  telegramBusy: boolean;
  alertLoading: boolean;
  alertStatus: string | null;
  onStartTelegramLink: () => void;
  onRefreshTelegramStatus: () => void;
  onUnlinkTelegram: () => void;
  onSendAlert: (exam: ExamMatchResult) => void;
  onRoadmap: (exam: ExamMatchResult) => void;
  onClose: () => void;
}

function getDaysLeft(deadlineStr: string) {
  return Math.ceil((new Date(deadlineStr).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

export function JobDetailDialog({
  exam,
  telegramLinked,
  telegramCode,
  telegramBotUsername,
  telegramBusy,
  alertLoading,
  alertStatus,
  onStartTelegramLink,
  onRefreshTelegramStatus,
  onUnlinkTelegram,
  onSendAlert,
  onRoadmap,
  onClose,
}: JobDetailDialogProps) {
  const [animState, setAnimState] = useState<"closed" | "entering" | "open" | "leaving">("closed");
  const [displayExam, setDisplayExam] = useState<ExamMatchResult | null>(exam);

  useEffect(() => {
    if (exam) {
      setDisplayExam(exam);
      requestAnimationFrame(() => setAnimState("open"));
      return undefined;
    } else {
      setAnimState("leaving");
      const t = setTimeout(() => {
        setAnimState("closed");
        setDisplayExam(null);
      }, 180);
      return () => clearTimeout(t);
    }
  }, [exam]);

  if (animState === "closed" || !displayExam) return null;

  const days = getDaysLeft(displayExam.application_deadline);
  const visible = animState === "open";

  return (
    <div
      onClick={() => onClose()}
      className="fixed inset-0 z-50 overflow-y-auto p-3 transition-colors duration-200 sm:p-4"
      style={{
        backgroundColor: visible ? "rgba(0,0,0,0.75)" : "rgba(0,0,0,0)",
        backdropFilter: visible ? "blur(4px)" : "blur(0px)",
      }}
    >
      <div className="flex min-h-full flex-col items-center justify-center gap-3">
        {/* Telegram reminder panel */}
        <div
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-md space-y-3 rounded-xl border bg-card p-4 transition-all duration-200"
          style={{
            transform: visible ? "translateY(0)" : "translateY(-12px)",
            opacity: visible ? 1 : 0,
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="flex min-w-0 items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Smartphone className="size-4 shrink-0" />
              <span className="min-w-0">Get Telegram Deadline Reminders</span>
            </span>
            <button
              type="button"
              onClick={() => onClose()}
              className="shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Close"
            >
              <X className="size-4" />
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {telegramLinked ? (
              <>
                <Button
                  type="button"
                  size="sm"
                  disabled={alertLoading}
                  onClick={() => onSendAlert(displayExam)}
                  className="gap-1.5 text-xs"
                >
                  {alertLoading ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <MailCheck className="size-3.5" />
                  )}
                  <span>Test Alert</span>
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={telegramBusy}
                  onClick={onUnlinkTelegram}
                  className="text-xs"
                >
                  Unlink
                </Button>
              </>
            ) : telegramCode ? (
              <>
                <code className="rounded-md border bg-muted px-2.5 py-1.5 font-mono text-xs">
                  {telegramCode}
                </code>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={telegramBusy}
                  onClick={onRefreshTelegramStatus}
                  className="text-xs"
                >
                  {telegramBusy ? <Loader2 className="size-3.5 animate-spin" /> : null}
                  Check status
                </Button>
              </>
            ) : (
              <Button
                type="button"
                size="sm"
                disabled={telegramBusy}
                onClick={onStartTelegramLink}
                className="gap-1.5 text-xs"
              >
                {telegramBusy ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Smartphone className="size-3.5" />
                )}
                Get link code
              </Button>
            )}
          </div>
          {!telegramLinked && telegramCode && (
            <p className="text-[11px] text-muted-foreground">
              Send <code className="font-mono">/start {telegramCode}</code> to @
              {telegramBotUsername || "the bot"} in Telegram, then press Check status.
            </p>
          )}
          {alertStatus && <p className="text-[11px] text-success">{alertStatus}</p>}
        </div>

        <Card
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-lg shadow-2xl transition-all duration-200"
          style={{
            transform: visible ? "translateY(0) scale(1)" : "translateY(16px) scale(0.97)",
            opacity: visible ? 1 : 0,
          }}
        >
          <CardHeader className="flex-row items-start justify-between gap-3 space-y-0 border-b pb-4">
            <div className="min-w-0">
              <Badge variant="secondary">{displayExam.post_type}</Badge>
              <CardTitle className="mt-2 font-display text-lg font-bold sm:text-xl">
                {displayExam.title}
              </CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">{displayExam.organizing_body}</p>
            </div>
            <button
              type="button"
              onClick={() => onClose()}
              className="shrink-0 p-1 text-muted-foreground transition hover:text-foreground"
              aria-label="Close"
            >
              <X className="size-5" />
            </button>
          </CardHeader>

          <CardContent className="space-y-5 pt-5">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-warning/50 bg-warning/10 p-3 sm:p-4">
              <div className="min-w-0">
                <span className="block text-xs font-semibold uppercase tracking-wider text-warning">
                  Application Form Deadline
                </span>
                <span className="text-lg font-bold">{displayExam.application_deadline}</span>
              </div>
              <Badge className="shrink-0 border border-warning/40 bg-warning/20 text-warning">
                {days > 0 ? `${days} Days Left` : "Deadline Passed"}
              </Badge>
            </div>

            <div className="grid grid-cols-1 gap-3 rounded-xl border bg-muted/40 p-4 text-sm min-[380px]:grid-cols-2">
              <div>
                <span className="block text-xs text-muted-foreground">Tentative Exam Date</span>
                <span className="font-medium">{displayExam.exam_date || "To be notified"}</span>
              </div>
              <div>
                <span className="block text-xs text-muted-foreground">Your Age vs Max Allowed</span>
                <span className="font-medium">
                  {displayExam.candidate_age_at_cutoff} yrs / {displayExam.max_allowed_age} yrs
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-3 pt-1 sm:flex-row">
              {displayExam.official_pdf_url && (
                <Button asChild className="flex-1 gap-2 rounded-xl">
                  <a href={displayExam.official_pdf_url} target="_blank" rel="noopener noreferrer">
                    <span>Open Official Portal &amp; Form</span>
                    <ExternalLink />
                  </a>
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  onRoadmap(displayExam);
                  onClose();
                }}
                className="flex-1 gap-2 rounded-xl"
              >
                <BookOpen className="size-4" />
                <span>View Study Roadmap</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
