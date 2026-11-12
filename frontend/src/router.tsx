import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

// In the browser we keep ONE QueryClient for the app's lifetime.
// On the server we create a fresh one per request: a shared client would
// leak one user's cached data into another user's rendered HTML.
let browserQueryClient: QueryClient | undefined;

export const getRouter = () => {
  const queryClient =
    typeof window === "undefined"
      ? new QueryClient()
      : (browserQueryClient ??= new QueryClient());

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
