import { createFileRoute } from "@tanstack/react-router";
import { GovJobApp } from "@/components/govjob/govjob-app";
import { indexSearchSchema } from "@/lib/search";

export const Route = createFileRoute("/")({
  validateSearch: indexSearchSchema.parse,
  head: () => ({
    meta: [
      { title: "GovJob AI Copilot — Resume to Government Exam Eligibility" },
      {
        name: "description",
        content:
          "Upload your resume, complete your statutory eligibility profile, see matched government exams with syllabus overlap, and get an adaptive AI study roadmap.",
      },
      {
        property: "og:title",
        content: "GovJob AI Copilot — Resume to Government Exam Eligibility",
      },
      {
        property: "og:description",
        content:
          "Resume-to-statutory eligibility engine, syllabus overlap scoring and adaptive study roadmaps for Indian government exams.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: GovJobApp,
});
