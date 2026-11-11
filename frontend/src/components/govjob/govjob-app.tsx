import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Award,
  BookOpen,
  Crop,
  Loader2,
  Moon,
  Sparkles,
  Sun,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import * as api from "@/lib/govjob/api";
import type {
  CandidateProfile,
  EligibilityCheckResponse,
  ExamMatchResult,
  MissingFieldPrompt,
  StudyRoadmapResponse,
} from "@/types/govjob";
import { ResumeProfileStep } from "./resume-profile-step";
import { EligibilityResults } from "./eligibility-results";
import { RoadmapStep } from "./roadmap-step";
import { DocumentResizer } from "./document-resizer";
import { JobDetailDialog } from "./job-detail-dialog";

const TABS = [
  { id: "profile", label: "Resume & Profile", icon: Upload },
  { id: "eligibility", label: "Eligibility", icon: Award },
  { id: "roadmap", label: "Study Roadmap", icon: BookOpen },
  { id: "documents", label: "Photo & Signature", icon: Crop },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function GovJobApp() {
  const [darkMode, setDarkMode] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("profile");

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [missingFields, setMissingFields] = useState<MissingFieldPrompt[]>([]);
  const [statusMessage, setStatusMessage] = useState("");

  const [eligibility, setEligibility] = useState<EligibilityCheckResponse | null>(null);
  const [primaryExamId, setPrimaryExamId] = useState("ssc-cgl-general");
  const [targetWeeks, setTargetWeeks] = useState(12);

  const [roadmap, setRoadmap] = useState<StudyRoadmapResponse | null>(null);
  const [roadmapExamId, setRoadmapExamId] = useState<string | null>(null);
  const [completedWeeks, setCompletedWeeks] = useState<Record<number, boolean>>({});

  const [selectedJob, setSelectedJob] = useState<ExamMatchResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const [telegramChatId, setTelegramChatId] = useState("");
  const [alertLoading, setAlertLoading] = useState(false);
  const [alertStatus, setAlertStatus] = useState<string | null>(null);

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
      const base: CandidateProfile = prev ?? {
        full_name: "Candidate",
        dob: "2004-06-10",
        category: "General",
        highest_degree: "12th",
        stream: "PCM (Physics, Chemistry, Maths)",
        percentage_cgpa: 75,
        graduation_status: "Completed",
        skills: [],
      } as unknown as CandidateProfile;

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
    setSubmitting(true);
    try {
      const data = await api.checkEligibility(profile, primaryExamId);
      setEligibility(data);
      setActiveTab("eligibility");
      toast.success(`Found ${data.eligible_now.length} eligible exams for you.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Eligibility check failed");
    } finally {
      setSubmitting(false);
    }
  };

  // Switch primary target exam and recalculate overlap
  const handleSwitchPrimaryExam = async (newPrimaryId: string) => {
    if (!profile) return;
    setPrimaryExamId(newPrimaryId);
    try {
      const data = await api.checkEligibility(profile, newPrimaryId);
      setEligibility(data);
      toast.success("Primary target updated — overlaps recalculated.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not update primary exam");
    }
  };

  // 4. AI study roadmap
  const handleGenerateRoadmap = async (exam: ExamMatchResult) => {
    setRoadmapExamId(exam.exam_id);
    try {
      const data = await api.generateRoadmap(exam.exam_id, targetWeeks);
      setRoadmap(data);
      setCompletedWeeks({});
      setActiveTab("roadmap");
      toast.success(`Roadmap generated: ${targetWeeks} weeks for ${exam.title}.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not generate roadmap");
    } finally {
      setRoadmapExamId(null);
    }
  };

  const handleSyncLiveJobs = async () => {
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
    if (!telegramChatId.trim()) {
      toast.error("Please enter your Telegram Chat ID first!");
      return;
    }
    setAlertLoading(true);
    setAlertStatus(null);
    try {
      const data = await api.sendTelegramAlert({
        chat_id: telegramChatId.trim(),
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

        {/* Tabbed navigation with sliding pill */}
        <nav className="mt-8 grid w-full grid-cols-2 gap-2 rounded-2xl border bg-card/60 p-1.5 backdrop-blur sm:grid-cols-4">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
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
                    primaryExamId={primaryExamId}
                    targetWeeks={targetWeeks}
                    roadmapExamId={roadmapExamId}
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
                    onAction={() => setActiveTab("profile")}
                  />
                ))}

              {activeTab === "roadmap" &&
                (roadmap ? (
                  <RoadmapStep
                    roadmap={roadmap}
                    completedWeeks={completedWeeks}
                    onToggleWeek={(week) =>
                      setCompletedWeeks((prev) => ({ ...prev, [week]: !prev[week] }))
                    }
                  />
                ) : (
                  <EmptyTabState
                    icon={BookOpen}
                    title="No study roadmap yet"
                    description="Pick an eligible exam and hit Roadmap to generate an adaptive, week-by-week AI preparation plan."
                    actionLabel="Go to Eligibility"
                    onAction={() => setActiveTab("eligibility")}
                  />
                ))}

              {activeTab === "documents" && <DocumentResizer />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      <JobDetailDialog
        exam={selectedJob}
        telegramChatId={telegramChatId}
        alertLoading={alertLoading}
        alertStatus={alertStatus}
        onTelegramChange={setTelegramChatId}
        onSendAlert={handleSendTelegramAlert}
        onRoadmap={handleGenerateRoadmap}
        onClose={() => setSelectedJob(null)}
      />
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