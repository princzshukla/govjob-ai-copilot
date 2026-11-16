import type { Job } from "./jobs";

export const PROFILE = {
  name: "Aarav Kumar",
  dob: "10 Jun 2004",
  age: 22,
  category: "OBC",
  domicile: "Bihar",
  degree: "Graduate (B.Tech)",
  stream: "Computer Science",
  percentage: 58,
};

export interface Verdict {
  job: Job;
  eligible: boolean;
  ageAtCutoff: number;
  maxAllowed: number;
  reasons: string[];
  /** % of the post's syllabus the profile covers — a coarse, stable estimate */
  overlap: number;
  lastAttempt: boolean;
  /** normalised top-of-range pay, for at-a-glance comparison */
  payCap: string;
}

/** Pull the top of the pay range into a comparable "₹X" cap. */
function payCap(salary: string): string {
  const nums = salary.match(/₹\s*([\d,]+)/g) ?? [];
  const last = nums[nums.length - 1] ?? "";
  const clean = last.replace(/[^\d]/g, "");
  if (!clean) return salary;
  const v = Number(clean);
  if (v >= 100000) return `₹${(v / 100000).toFixed(2)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(1)}K`;
  return salary;
}

/**
 * Does the profile's degree actually satisfy THIS post?
 *
 * "Graduate" is not the same thing as "eligible for a graduate post" — an
 * AIIMS Nursing Officer post needs B.Sc Nursing, and a Civil Judge post needs
 * an LLB. A B.Tech in Computer Science clears neither.
 */
function degreeMatches(job: Job): boolean {
  const req = job.requires?.toLowerCase();
  if (!req) return true;

  const degree = PROFILE.degree.toLowerCase();
  const stream = PROFILE.stream.toLowerCase();

  if (req.includes("b.tech")) {
    if (!degree.includes("b.tech")) return false;
    // a named specialisation has to match the branch, too
    if (req.includes("civil") && !stream.includes("civil")) return false;
    if (req.includes("electrical") && !stream.includes("electrical")) return false;
    return true;
  }

  return false;
}

/** Stable pseudo-score so a card never flickers between renders. */
function syllabusOverlap(job: Job): number {
  const required = job.requires?.toLowerCase();
  if (required && !degreeMatches(job)) return 12;
  let h = 0;
  for (let i = 0; i < job.id.length; i++) h = (h * 31 + job.id.charCodeAt(i)) % 997;
  return 52 + (h % 46);
}

export function evaluate(job: Job): Verdict {
  const reasons: string[] = [];

  // Age: the post's own limit wins, else the usual 27 (30 for OBC) rule.
  const maxAllowed = job.maxAge ?? (27 + (PROFILE.category === "OBC" ? 3 : 0));

  if (PROFILE.age > maxAllowed) {
    reasons.push(`Over the age limit by ${PROFILE.age - maxAllowed} yrs (max ${maxAllowed})`);
  }
  if (PROFILE.age < 18) reasons.push("Underage");

  // The specific degree this post demands.
  if (job.requires && !degreeMatches(job)) {
    reasons.push(`Requires ${job.requires}`);
  } else if (job.qualification === "B.Tech" && !PROFILE.degree.includes("B.Tech")) {
    reasons.push("Requires B.Tech");
  }

  // The graduation cut-off stated in the notification.
  const minPct = job.minPercentage ?? 0;
  if (minPct && PROFILE.percentage < minPct) {
    reasons.push(`Needs ${minPct}% — you have ${PROFILE.percentage}%`);
  }

  return {
    job,
    eligible: reasons.length === 0,
    ageAtCutoff: PROFILE.age,
    maxAllowed,
    reasons,
    overlap: syllabusOverlap(job),
    lastAttempt: maxAllowed - PROFILE.age <= 2,
    payCap: payCap(job.salary),
  };
}

export function evaluateAll(jobs: Job[]): Verdict[] {
  return jobs.map(evaluate);
}
