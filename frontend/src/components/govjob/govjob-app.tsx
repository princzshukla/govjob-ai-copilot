import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import {
  Award,
  BookOpen,
  BrainCircuit,
  Crop,
  Loader2,
  Moon,
  Sparkles,
  Sun,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { AdaptiveQuizPanel } from "@/components/AdaptiveQuizPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import * as api from "@/lib/govjob/api";
import { useGovJobStore, getDraftProfile } from "@/stores/govjob-store";
import { useAuth } from "@/hooks/use-auth";
import { useRoadmapQuery, useToggleRoadmapWeek, roadmapKey } from "@/hooks/use-roadmap";
import { useEligibilityCheck } from "@/hooks/use-eligibility";
import type {
  CandidateProfile,
  DiagnosticItem,
  ExamMatchResult,
  MissingFieldPrompt,
  SavedRoadmap,
} from "@/types/govjob";
import { ResumeProfileStep } from "./resume-profile-step";
import { EligibilityResults } from "./eligibility-results";
import { RoadmapStep } from "./roadmap-step";
import { DocumentResizer } from "./document-resizer";
import { JobDetailDialog } from "./job-detail-dialog";
import { AccountMenu } from "./account-menu";

const TABS = [
  { id: "profile", label: "Resume & Profile", icon: Upload },
  { id: "eligibility", label: "Eligibility", icon: Award },
  { id: "roadmap", label: "Study Roadmap", icon: BookOpen },
  { id: "documents", label: "Photo & Signature", icon: Crop },
  { id: "adaptive", label: "Adaptive Drill", icon: BrainCircuit },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function GovJobApp() {
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: "/" });
  const { tab: activeTab, exam: examId, week } = useSearch({ from: "/" });

  const setTab = (tab: TabId) =>
    navigate({ search: (prev) => ({ ...prev, tab }), replace: true });
  const setExam = (exam: string) =>
    navigate({ search: (prev) => ({ ...prev, exam }), replace: true });
  const setWeek = (week: number) =>
    navigate({ search: (prev) => ({ ...prev, week }), replace: true });

  const setDraftProfile = useGovJobStore((s) => s.setDraftProfile);
  const requestSignIn = useGovJobStore((s) => s.requestSignIn);

  const [darkMode, setDarkMode] = useState(true);
  const [activeDrillTopic, setActiveDrillTopic] = useState("Percentage");
  const [activeDrillSubject, setActiveDrillSubject] = useState("Quantitative Aptitude");
  const [loading, setLoading] = useState(false);
  // Guests keep their draft across reloads (sessionStorage via the store).
  const [profile, setProfile] = useState<CandidateProfile | null>(() => getDraftProfile());
  const [missingFields, setMissingFields] = useState<MissingFieldPrompt[]>([]);
  const [statusMessage, setStatusMessage] = useState("");

  const [targetWeeks, setTargetWeeks] = useState(12);

  const { user: me } = useAuth();
  const ownerId = me?.id ?? "guest";
  const activeExamId = examId || "ssc-cgl-general";

  const eligibilityCheck = useEligibilityCheck();
  const eligibility = eligibilityCheck.data ?? null;
  const submitting = eligibilityCheck.isPending;

  const { data: savedRoadmap, isLoading: roadmapLoading } = useRoadmapQuery(activeExamId);
  const roadmapExamId = savedRoadmap?.exam_id ?? null;
  const roadmap = savedRoadmap?.roadmap ?? null;
  const roadmapProgressKey = roadmapKey(ownerId, activeExamId);

  const toggleWeekMutation = useToggleRoadmapWeek(activeExamId);
  const completedWeeks = useMemo(
    () =>
      Object.fromEntries(
        (savedRoadmap?.completed_weeks ?? []).map((weekNo) => [weekNo, true]),
      ) as Record<number, boolean>,
    [savedRoadmap?.completed_weeks],
  );

  const generateMutation = useMutation({
    mutationFn: (vars: { examId: string; targetWeeks: number }) =>
      api.generateRoadmap(vars.examId, vars.targetWeeks),
    onSuccess: (_data, vars) => {
      // Server already saved the roadmap atomically; just refresh the cache.
      queryClient.invalidateQueries({ queryKey: roadmapKey(ownerId, vars.examId) });
    },
  });

  const [selectedJob, setSelectedJob] = useState<ExamMatchResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const [telegramLinked, setTelegramLinked] = useState(false);
  const [telegramCode, setTelegramCode] = useState<string | null>(null);
  const [telegramBotUsername, setTelegramBotUsername] = useState("");
  const [telegramBusy, setTelegramBusy] = useState(false);
  const [alertLoading, setAlertLoading] = useState(false);
  const [alertStatus, setAlertStatus] = useState<string | null>(null);

  // Keep the persisted guest draft in sync with any profile edits.
  useEffect(() => {
    if (profile) setDraftProfile(profile);
  }, [profile, setDraftProfile]);

  // Theme: dark by default, persisted to localStorage after mount (SSR-safe).
  useEffect(() => {
    const saved =
      typeof window !== "undefined" ? window.localStorage.getItem("govjob_theme") : null;
    if (saved === "light") setDarkMode(false);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.classList.toggle("dark", darkMode);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("govjob_theme", darkMode ? "dark" : "light");
    }
  }, [darkMode]);

  // Telegram status is per session; guests have no session, so skip the call.
  useEffect(() => {
    if (!me) {
      setTelegramLinked(false);
      return;
    }
    let cancelled = false;
    api
      .getTelegramStatus()
      .then((status) => {
        if (!cancelled) setTelegramLinked(status.linked);
      })
      .catch(() => {
        if (!cancelled) setTelegramLinked(false);
      });
    return () => {
      cancelled = true;
    };
  }, [me]);

  // 1. Upload resume
  const handleFileUpload = async (file: File) => {
    setLoading(true);
    try {
      const data = await api.parseResume(file);
      setProfile(data.extracted_profile);
      setMissingFields(data.missing_fields || []);
      setStatusMessage(data.message);
      toast.success("Resume parsed — review the extracted profile below.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to parse resume");
    } finally {
      setLoading(false);
    }
  };

  // 2. Live field edits (supports both uploaded resume and manual entry)
  const handleFieldChange = (field: string, value: string) => {
    setProfile((prev) => {
      const base: CandidateProfile = prev ?? ({
        full_name: "Candidate",
        dob: "2004-06-10",
        category: "General",
        highest_degree: "12th",
        stream: "PCM (Physics, Chemistry, Maths)",
        percentage_cgpa: 75,
        graduation_status: "Completed",
        skills: [],
      } as unknown as CandidateProfile);

      return {
        ...base,
        [field]:
          field === "percentage_cgpa"
            ? value
              ? parseFloat(value)
              : null
            : value,
      };
    });
  };

  // 3. Eligibility check
  const handleCheckEligibility = async () => {
    if (!profile) return;
    try {
      await eligibilityCheck.mutateAsync({ profile, examId: activeExamId });
      setTab("eligibility");
      toast.success("Eligibility check complete.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Eligibility check failed");
    }
  };

  // Switch primary target exam and recalculate overlap
  const handleSwitchPrimaryExam = async (newPrimaryId: string) => {
    if (!profile) return;
    setExam(newPrimaryId);
    try {
      await eligibilityCheck.mutateAsync({ profile, examId: newPrimaryId });
      toast.success("Primary target updated — overlaps recalculated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not update primary exam");
    }
  };

  // 4. AI study roadmap (guests get 401, which this app handles globally)
  const handleGenerateRoadmap = async (exam: ExamMatchResult) => {
    if (!me) {
      requestSignIn();
      return;
    }
    setExam(exam.exam_id);
    try {
      await generateMutation.mutateAsync({ examId: exam.exam_id, targetWeeks });
      setTab("roadmap");
      toast.success(`Roadmap generated: ${targetWeeks} weeks for ${exam.title}.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not generate roadmap");
    }
  };

  const handleSyncLiveJobs = async () => {
    if (!me) {
      requestSignIn();
      return;
    }
    setSyncing(true);
    setSyncMessage(null);
    try {
      const data = await api.syncLiveJobs();
      if (data.status === "success") {
        setSyncMessage(
          `Successfully synced! Discovered ${data.new_jobs_discovered} new live jobs (${data.total_active_jobs} total active).`,
        );
      } else {
        setSyncMessage(data.message || "Sync completed: no new jobs added.");
      }
    } catch (err) {
      setSyncMessage(`Sync failed: ${err instanceof Error ? err.message : "unknown error"}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleSendTelegramAlert = async (exam: ExamMatchResult) => {
    if (!me) {
      requestSignIn();
      return;
    }
    if (!telegramLinked) {
      toast.error("Link your Telegram account first.");
      return;
    }
    setAlertLoading(true);
    setAlertStatus(null);
    try {
      const data = await api.sendTelegramAlert({
        exam_title: exam.title,
        application_deadline: exam.application_deadline,
        days_left: Math.ceil(
          (new Date(exam.application_deadline).getTime() - Date.now()) / 86400000,
        ),
      });
      setAlertStatus(
        data.status === "success"
          ? "Alert dispatched successfully! Check your Telegram."
          : data.detail || data.message || "Failed to send alert.",
      );
    } catch {
      setAlertStatus("Network error sending alert.");
    } finally {
      setAlertLoading(false);
    }
  };

  const handleStartTelegramLink = async () => {
    if (!me) {
      requestSignIn();
      return;
    }
    setTelegramBusy(true);
    setAlertStatus(null);
    try {
      const data = await api.createTelegramLink();
      setTelegramCode(data.code);
      setTelegramBotUsername(data.bot_username);
      setAlertStatus(
        `Send /start ${data.code} to @${data.bot_username || "the bot"} in Telegram, then check status.`,
      );
    } catch (err) {
      setAlertStatus(err instanceof Error ? err.message : "Could not create a Telegram link code.");
    } finally {
      setTelegramBusy(false);
    }
  };

  const handleRefreshTelegramStatus = async () => {
    if (!me) {
      requestSignIn();
      return;
    }
    setTelegramBusy(true);
    try {
      const status = await api.getTelegramStatus();
      setTelegramLinked(status.linked);
      if (status.linked) {
        setTelegramCode(null);
        setAlertStatus("Telegram linked! Deadline alerts can now be sent.");
      } else {
        setAlertStatus("Not linked yet. Send the code to the bot, then check again.");
      }
    } catch (err) {
      setAlertStatus(err instanceof Error ? err.message : "Could not check Telegram status.");
    } finally {
      setTelegramBusy(false);
    }
  };

  const handleUnlinkTelegram = async () => {
    if (!me) {
      requestSignIn();
      return;
    }
    setTelegramBusy(true);
    try {
      await api.unlinkTelegram();
      setTelegramLinked(false);
      setTelegramCode(null);
      setAlertStatus("Telegram unlinked.");
    } catch (err) {
      setAlertStatus(err instanceof Error ? err.message : "Could not unlink Telegram.");
    } finally {
      setTelegramBusy(false);
    }
  };

  const handlePracticeTopic = (topic: string, subject: string = "Quantitative Aptitude") => {
    if (!me) {
      requestSignIn();
      return;
    }
    setActiveDrillTopic(topic);
    setActiveDrillSubject(subject);
    setTab("adaptive");
  };

  const handleToggleWeek = (weekNumber: number) => {
    if (!savedRoadmap) return;
    toggleWeekMutation.mutate({
      roadmapId: savedRoadmap.roadmap_id,
      weekNo: weekNumber,
      done: !completedWeeks[weekNumber],
    });
  };

  const handleDrillEvaluated = ({
    topic,
    topicStatus,
    microRevisions,
  }: {
    topic: string;
    topicStatus: string;
    microRevisions: string[];
    diagnostics: DiagnosticItem[];
  }) => {
    if (topicStatus === "Needs Revision" || microRevisions.length > 0) {
      queryClient.setQueryData<SavedRoadmap | null | undefined>(
        roadmapProgressKey,
        (existing) => {
          if (!existing) return existing;

          const breakdown = [...existing.roadmap.weekly_breakdown];
          const activeIndex = breakdown.findIndex((w) => !completedWeeks[w.week_number]);
          const targetIdx = activeIndex !== -1 ? activeIndex : 0;
          const currentWeek = breakdown[targetIdx];
          if (!currentWeek) return existing;

          const newTopics =
            microRevisions.length > 0
              ? microRevisions.map((sub) => `[Micro-Revision] ${topic}: ${sub}`)
              : [`[High Priority] ${topic} Revision & Practice`];

          const existingSet = new Set(currentWeek.topics);
          const filteredNew = newTopics.filter((t) => !existingSet.has(t));
          if (filteredNew.length === 0) return existing;

          breakdown[targetIdx] = {
            ...currentWeek,
            topics: [...currentWeek.topics, ...filteredNew],
          };

          return {
            ...existing,
            roadmap: { ...existing.roadmap, weekly_breakdown: breakdown },
          };
        },
      );

      toast.warning(`Roadmap adapted! Micro-revision added for "${topic}".`, {
        description: "Scheduled into your current study week based on drill diagnostics.",
        action: {
          label: "View Roadmap",
          onClick: () => setTab("roadmap"),
        },
      });
    } else if (topicStatus === "Mastered") {
      toast.success(`"${topic}" is Mastered!`, {
        description: "Accuracy EMA updated across your active study plan.",
      });
    }
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="ambient-glow" />
      <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-6 md:px-8 md:pt-10">
        {/* Header */}
        <header className="flex flex-col gap-4 border-b pb-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="bg-gradient-to-r from-primary to-chart-2 bg-clip-text font-display text-3xl font-bold text-transparent">
              GovJob AI Copilot
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Resume-to-Statutory Eligibility Engine, Syllabus Overlap &amp; Adaptive Roadmaps
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setDarkMode(!darkMode)}
              className="gap-2 rounded-xl"
              title="Toggle Light/Dark Mode"
            >
              {darkMode ? (
                <Sun className="size-4 text-warning" />
              ) : (
                <Moon className="size-4 text-primary" />
              )}
              <span className="text-xs font-semibold">{darkMode ? "Light Mode" : "Dark Mode"}</span>
            </Button>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleSyncLiveJobs}
              disabled={syncing}
              className="gap-2 rounded-xl"
            >
              {syncing ? (
                <Loader2 className="size-4 animate-spin text-primary" />
              ) : (
                <Sparkles className="size-4 text-primary" />
              )}
              <span className="text-xs font-semibold">
                {syncing ? "Scraping Live Jobs..." : "Sync Live Jobs"}
              </span>
            </Button>

            <AccountMenu />
          </div>
        </header>

        {syncMessage && (
          <div className="mt-4 flex items-center justify-between rounded-xl border border-primary/40 bg-primary/10 px-4 py-3 text-xs text-foreground">
            <span>{syncMessage}</span>
            <button
              onClick={() => setSyncMessage(null)}
              className="font-bold text-muted-foreground hover:text-foreground"
            >
              <X className="size-4" />
            </button>
          </div>
        )}

        {/* Tabbed navigation with sliding pill (5 columns on desktop) */}
        <nav className="mt-8 grid w-full grid-cols-2 gap-2 rounded-2xl border bg-card/60 p-1.5 backdrop-blur sm:grid-cols-5">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setTab(tab.id as TabId)}
                className={cn(
                  "relative flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors duration-200",
                  isActive
                    ? "text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {isActive && (
                  <motion.span
                    layoutId="govjob-tab-pill"
                    className="absolute inset-0 rounded-xl bg-primary shadow-md shadow-primary/25"
                    transition={{ type: "spring", stiffness: 420, damping: 34 }}
                  />
                )}
                <span className="relative z-10 flex items-center justify-center gap-2">
                  <Icon className="size-4" />
                  {tab.label}
                </span>
              </button>
            );
          })}
        </nav>

        {/* Animated tab panels */}
        <div className="mt-6">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              {activeTab === "profile" && (
                <ResumeProfileStep
                  loading={loading}
                  submitting={submitting}
                  profile={profile}
                  missingFields={missingFields}
                  statusMessage={statusMessage}
                  onUpload={handleFileUpload}
                  onFieldChange={handleFieldChange}
                  onSubmit={handleCheckEligibility}
                />
              )}

              {activeTab === "eligibility" &&
                (eligibility ? (
                  <EligibilityResults
                    eligibility={eligibility}
                    primaryExamId={examId}
                    targetWeeks={targetWeeks}
                    roadmapExamId={generateMutation.isPending ? examId : roadmapExamId}
                    onTargetWeeksChange={setTargetWeeks}
                    onOpenJob={setSelectedJob}
                    onRoadmap={handleGenerateRoadmap}
                    onSwitchPrimary={handleSwitchPrimaryExam}
                  />
                ) : (
                  <EmptyTabState
                    icon={Award}
                    title="No eligibility results yet"
                    description="Upload your resume or enter your profile details manually to see your matched government exams."
                    actionLabel="Go to Resume & Profile"
                    onAction={() => setTab("profile")}
                  />
                ))}

              {activeTab === "roadmap" &&
                (generateMutation.isPending || roadmapLoading ? (
                  <RoadmapSkeleton />
                ) : roadmap ? (
                  <RoadmapStep
                    roadmap={roadmap}
                    completedWeeks={completedWeeks}
                    onToggleWeek={handleToggleWeek}
                    onPracticeTopic={handlePracticeTopic}
                    examId={activeExamId}
                    activeWeek={week}
                    onWeekSelect={setWeek}
                  />
                ) : (
                  <EmptyTabState
                    icon={BookOpen}
                    title={me ? "No study roadmap yet" : "Sign in to build your roadmap"}
                    description={
                      me
                        ? "Pick an eligible exam and hit Roadmap to generate an adaptive, week-by-week AI preparation plan."
                        : "Generate a week-by-week AI plan, saved to your account. Your guest resume draft is attached automatically on sign-in."
                    }
                    actionLabel={me ? "Go to Eligibility" : "Sign in to continue"}
                    onAction={me ? () => setTab("eligibility") : requestSignIn}
                  />
                ))}

              {activeTab === "documents" && <DocumentResizer />}

              {activeTab === "adaptive" &&
                (me ? (
                  <AdaptiveQuizPanel
                    initialExamId={roadmapExamId || examId}
                    initialTopic={activeDrillTopic}
                    initialSubject={activeDrillSubject}
                    onDrillEvaluated={handleDrillEvaluated}
                  />
                ) : (
                  <EmptyTabState
                    icon={BrainCircuit}
                    title="Adaptive drills need an account"
                    description="Sign in to start targeted drills; your mastery EMA and drill history are saved to your own account. Parsing a resume stays free for guests."
                    actionLabel="Sign in to start drilling"
                    onAction={requestSignIn}
                  />
                ))}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <JobDetailDialog
        exam={selectedJob}
        telegramLinked={telegramLinked}
        telegramCode={telegramCode}
        telegramBotUsername={telegramBotUsername}
        telegramBusy={telegramBusy}
        alertLoading={alertLoading}
        alertStatus={alertStatus}
        onStartTelegramLink={handleStartTelegramLink}
        onRefreshTelegramStatus={handleRefreshTelegramStatus}
        onUnlinkTelegram={handleUnlinkTelegram}
        onSendAlert={handleSendTelegramAlert}
        onRoadmap={handleGenerateRoadmap}
        onClose={() => setSelectedJob(null)}
      />
    </div>
  );
}

function RoadmapSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24 w-full rounded-xl" />
      {[...Array(4)].map((_, i) => (
        <Skeleton key={i} className="h-28 w-full rounded-xl" />
      ))}
    </div>
  );
}

function EmptyTabState({
  icon: Icon,
  title,
  description,
  actionLabel,
  onAction,
}: {
  icon: typeof Award;
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
        <span className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="size-6" />
        </span>
        <h3 className="font-display text-lg font-semibold">{title}</h3>
        <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
        <Button variant="outline" size="sm" onClick={onAction} className="mt-1 rounded-xl">
          {actionLabel}
        </Button>
      </CardContent>
    </Card>
  );
}
