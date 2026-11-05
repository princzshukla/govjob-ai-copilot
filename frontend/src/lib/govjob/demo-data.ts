import type {
  CandidateProfile,
  EligibilityCheckResponse,
  MissingFieldPrompt,
  StudyRoadmapResponse,
  SyncLiveJobsResponse,
} from "@/types/govjob";

/**
 * Demo data used when the GovJob backend (http://localhost:8000/api/v1)
 * is unreachable, so the whole flow stays explorable end to end.
 */

export const DEMO_PROFILE: CandidateProfile = {
  full_name: "Aarav Sharma",
  email: "aarav.sharma@example.com",
  dob: "1999-06-14",
  highest_degree: "B.Tech Computer Science",
  stream: "Computer Science",
  percentage_cgpa: 78.5,
};

export const DEMO_MISSING_FIELDS: MissingFieldPrompt[] = [
  {
    field_name: "gender",
    label: "Gender",
    question: "Which gender is printed on your government ID?",
    input_type: "select",
    options: ["Male", "Female", "Other"],
  },
  {
    field_name: "category",
    label: "Category",
    question: "Select the reservation category applicable to you.",
    input_type: "select",
    options: ["General", "OBC-NCL", "EWS", "SC", "ST"],
  },
  {
    field_name: "domicile_state",
    label: "Domicile State",
    question: "Which state do you hold domicile in?",
    input_type: "select",
    options: [
      "Delhi",
      "Uttar Pradesh",
      "Maharashtra",
      "Bihar",
      "Karnataka",
      "Rajasthan",
      "West Bengal",
    ],
  },
  {
    field_name: "percentage_cgpa",
    label: "Percentage / CGPA",
    question: "Final aggregate marks as a percentage.",
    input_type: "number",
  },
];

export const DEMO_ELIGIBILITY: EligibilityCheckResponse = {
  eligible_now: [
    {
      exam_id: "ssc-cgl-general",
      title: "SSC Combined Graduate Level (CGL) 2026",
      organizing_body: "Staff Selection Commission",
      post_type: "Group B & C Posts",
      application_deadline: "2026-12-02",
      exam_date: "2027-02-18",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 32,
      syllabus_overlap_pct: 86,
      official_pdf_url: "https://ssc.gov.in/api/notice/cgl-2026",
    },
    {
      exam_id: "ibps-po-xxvi",
      title: "IBPS Probationary Officer (PO/MT) 2026",
      organizing_body: "Institute of Banking Personnel Selection",
      post_type: "Bank PO",
      application_deadline: "2026-11-24",
      exam_date: "2027-01-10",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 30,
      syllabus_overlap_pct: 71,
      official_pdf_url: "https://www.ibps.in/crp-po-mt/",
    },
    {
      exam_id: "rrb-ntpc-2026",
      title: "RRB Non-Technical Popular Categories (NTPC)",
      organizing_body: "Railway Recruitment Board",
      post_type: "Graduate Level Posts",
      application_deadline: "2026-12-15",
      exam_date: "2027-03-05",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 33,
      syllabus_overlap_pct: 64,
      official_pdf_url: "https://www.rrbcdg.gov.in/",
    },
    {
      exam_id: "lic-aao-2026",
      title: "LIC Assistant Administrative Officer (AAO)",
      organizing_body: "Life Insurance Corporation of India",
      post_type: "AAO (IT / Generalist)",
      application_deadline: "2026-12-08",
      exam_date: "2027-02-01",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 30,
      syllabus_overlap_pct: 58,
      official_pdf_url: "https://licindia.in/recruitment",
    },
  ],
  ineligible: [
    {
      exam_id: "upsc-cse-2027",
      title: "UPSC Civil Services Examination 2027",
      organizing_body: "Union Public Service Commission",
      post_type: "IAS / IPS / IFS",
      application_deadline: "2027-01-19",
      exam_date: "2027-05-30",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 32,
      syllabus_overlap_pct: null,
      official_pdf_url: "https://upsc.gov.in/examinations",
      reasons_failed: [
        "Attempt limit reached: 6 attempts already recorded for General category.",
        "Domicile proof for Jammu & Kashmir relaxation not provided.",
      ],
    },
    {
      exam_id: "sbi-so-2026",
      title: "SBI Specialist Officer (Scale II)",
      organizing_body: "State Bank of India",
      post_type: "Specialist Officer",
      application_deadline: "2026-11-30",
      exam_date: "2026-12-28",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 35,
      syllabus_overlap_pct: null,
      official_pdf_url: "https://sbi.co.in/web/careers",
      reasons_failed: [
        "Minimum 3 years of relevant work experience required — resume shows 1.5 years.",
        "Degree stream must be IT/Computer Science with certification — stream field missing.",
      ],
    },
    {
      exam_id: "isro-scientist-2026",
      title: "ISRO Scientist / Engineer (SC)",
      organizing_body: "Indian Space Research Organisation",
      post_type: "Scientist SC",
      application_deadline: "2026-12-10",
      exam_date: "2027-01-22",
      candidate_age_at_cutoff: 27,
      max_allowed_age: 28,
      syllabus_overlap_pct: null,
      official_pdf_url: "https://www.isro.gov.in/Careers.html",
      reasons_failed: [
        "Minimum CGPA 6.5 on a 10-point scale with first-class degree — CGPA field missing.",
        "Electronics / Mechanical / CS specialization with valid GATE score required.",
      ],
    },
  ],
};

const SUBJECT_PLAN: Record<string, { focus: string; topics: string[] }> = {
  quant: {
    focus: "Quantitative Aptitude",
    topics: [
      "Number System",
      "Percentages",
      "Profit & Loss",
      "Time & Work",
      "Speed & Distance",
      "Algebra",
      "Geometry & Mensuration",
      "Data Interpretation",
      "Trigonometry",
      "Mixture & Alligation",
    ],
  },
  english: {
    focus: "English Language",
    topics: [
      "Reading Comprehension",
      "Cloze Test",
      "Para Jumbles",
      "Error Spotting",
      "Fill in the Blanks",
      "Idioms & Phrases",
      "Active/Passive Voice",
      "Vocabulary Boost",
    ],
  },
  reasoning: {
    focus: "Reasoning Ability",
    topics: [
      "Coding-Decoding",
      "Blood Relations",
      "Syllogism",
      "Seating Arrangement",
      "Puzzles",
      "Direction Sense",
      "Order & Ranking",
      "Inequalities",
    ],
  },
  gk: {
    focus: "General Awareness",
    topics: [
      "Static GK",
      "Indian Polity",
      "Economy Basics",
      "Science & Technology",
      "Current Affairs (last 9 months)",
      "History & Culture",
      "Geography",
    ],
  },
  computers: {
    focus: "Computer Aptitude",
    topics: [
      "Computer Fundamentals",
      "Networking Basics",
      "DBMS & SQL",
      "Operating Systems",
      "MS Office",
      "Cyber Security Awareness",
    ],
  },
};

const RESOURCES = [
  "NCERT 6–12 (selective chapters)",
  "Previous Year Question Papers (last 5 yrs)",
  "Wren & Martin",
  "R.S. Aggarwal",
  "Daily 30-min mock sectional tests",
  "PIB & The Hindu current-affairs digest",
];

/**
 * Builds a demo study roadmap for `weeks` duration, cycling the core subjects
 * through Foundation, Practice and Revision phases.
 */
export function buildDemoRoadmap(
  examId: string,
  examName: string,
  weeks: number,
): StudyRoadmapResponse {
  const pick = <T>(arr: T[], i: number): T => arr[i % arr.length] ?? arr[0]!;
  const cycle = ["quant", "english", "reasoning", "gk", "computers"];
  const phases = ["Foundation", "Advanced Practice", "Mock & Revision"];
  const weekly = Array.from({ length: weeks }, (_, i) => {
    const sub = SUBJECT_PLAN[pick(cycle, i)] ?? SUBJECT_PLAN["quant"]!;
    const phase = pick(
      phases,
      Math.min(Math.floor((i / weeks) * phases.length), phases.length - 1),
    );
    const topicSlice = sub.topics.slice(
      (i * 2) % sub.topics.length,
      ((i * 2) % sub.topics.length) + 2,
    );
    return {
      week_number: i + 1,
      focus_subject: sub.focus,
      phase,
      topics: topicSlice.length ? topicSlice : sub.topics.slice(0, 2),
      practice_goal:
        phase === "Foundation"
          ? `Cover both topics end-to-end and solve 40 practice questions.`
          : phase === "Advanced Practice"
            ? `Attempt 1 full-length sectional mock; target 65% accuracy.`
            : `Full mock + error-log review; target 80% accuracy.`,
      recommended_resources: [pick(RESOURCES, i), pick(RESOURCES, i + 2)],
    };
  });

  return {
    exam_id: examId,
    exam_name: examName,
    total_duration_weeks: weeks,
    revision_strategy: `Balanced ${weeks}-week plan: alternate core subjects so no two consecutive weeks repeat a paper, with the final quarter reserved exclusively for full-length mocks and error-log revision.`,
    weekly_breakdown: weekly,
  };
}

export function demoSyncLiveJobs(): SyncLiveJobsResponse {
  return { status: "success", new_jobs_discovered: 3, total_active_jobs: 42 };
}
