import { Suspense, lazy } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";

// Admin-only review queue for held PDF extractions.
const AdminReviewPage = lazy(() =>
  import("@/components/govjob/admin-review-page").then((m) => ({
    default: m.AdminReviewPage,
  })),
);

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "Review queue — GovJob AI Copilot" },
      {
        name: "description",
        content: "Admin review queue for PDF extractions awaiting a human verdict.",
      },
    ],
  }),
  component: () => (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="ambient-glow" />
      <div className="relative mx-auto max-w-2xl px-4 py-6 md:px-8">
        <Suspense
          fallback={
            <div className="space-y-4">
              <Skeleton className="h-8 w-48 rounded-lg" />
              <Skeleton className="h-40 w-full rounded-xl" />
              <Skeleton className="h-40 w-full rounded-xl" />
            </div>
          }
        >
          <AdminReviewPage />
        </Suspense>
      </div>
    </div>
  ),
});
