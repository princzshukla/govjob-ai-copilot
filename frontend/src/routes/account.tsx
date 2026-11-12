import { Suspense, lazy } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";

// Code-split: the account page (forms, Radix dialogs) is only fetched when
// the user navigates to /account.
const AccountPage = lazy(() =>
  import("@/components/govjob/account-page").then((m) => ({ default: m.AccountPage })),
);

export const Route = createFileRoute("/account")({
  head: () => ({
    meta: [
      { title: "Account settings — GovJob AI Copilot" },
      {
        name: "description",
        content: "Manage your name, security and account for GovJob AI Copilot.",
      },
      { property: "og:title", content: "Account settings — GovJob AI Copilot" },
    ],
  }),
  component: () => (
    <div className="relative min-h-screen overflow-x-hidden">
      <div className="ambient-glow" />
      <div className="relative mx-auto max-w-2xl px-4 py-6 md:px-8">
        <Suspense
          fallback={
            <div className="space-y-6">
              <Skeleton className="h-8 w-40 rounded-lg" />
              <Skeleton className="h-40 w-full rounded-xl" />
              <Skeleton className="h-40 w-full rounded-xl" />
              <Skeleton className="h-40 w-full rounded-xl" />
            </div>
          }
        >
          <AccountPage />
        </Suspense>
      </div>
    </div>
  ),
});
