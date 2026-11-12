// src/components/govjob/account-menu.tsx
import { FormEvent, useEffect, useState } from "react";
import {
  Loader2,
  LogIn,
  LogOut,
  Settings,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useGovJobStore } from "@/stores/govjob-store";

/** Header account control: avatar dropdown with account actions. */
export function AccountMenu() {
  const { user, isLoading, signOut, removeAccount } = useAuth();
  const requestSignIn = useGovJobStore((s) => s.requestSignIn);

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (deleteOpen) {
      setPassword("");
      setError(null);
      setBusy(false);
    }
  }, [deleteOpen]);

  if (isLoading) {
    return <Skeleton className="size-9 rounded-full" aria-label="Loading account" />;
  }

  if (!user) {
    return (
      <Button variant="outline" size="sm" className="gap-2 rounded-xl" onClick={requestSignIn}>
        <LogIn className="size-4 text-primary" />
        <span className="text-xs font-semibold">Sign in</span>
      </Button>
    );
  }

  const displayName = user.full_name?.trim() || user.email;
  const initial = (user.full_name?.trim()?.[0] ?? user.email[0] ?? "?").toUpperCase();

  const onLogout = async () => {
    try {
      await signOut();
      toast.success("Signed out.");
    } catch {
      toast.error("Could not sign out cleanly; local state was cleared.");
    }
  };

  const onDelete = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await removeAccount(password);
      setDeleteOpen(false);
      toast.success("Account deleted.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the account.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label={`Account menu for ${displayName}`}
            className="rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            <Avatar className="size-9 border border-primary/40">
              <AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">
                {initial}
              </AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold leading-tight">{displayName}</span>
            <span className="truncate text-xs font-normal text-muted-foreground">
              {user.email}
            </span>
            {user.phone ? (
              <span className="text-[11px] font-normal text-muted-foreground">{user.phone}</span>
            ) : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled title="Coming soon — the account page ships in the next phase">
            <Settings className="text-muted-foreground" />
            Account settings
            <span className="ml-auto text-[10px] uppercase text-muted-foreground">Soon</span>
          </DropdownMenuItem>
          <DropdownMenuItem onSelect={onLogout}>
            <LogOut />
            Log out
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive [&_svg]:text-destructive"
            onSelect={() => setDeleteOpen(true)}
          >
            <Trash2 />
            Delete account
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <div className="flex size-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
              <Trash2 className="size-5" />
            </div>
            <DialogTitle className="font-display">Delete account</DialogTitle>
            <DialogDescription>
              This permanently removes your account, profile, roadmaps, progress and drill
              history. There is no undo. Enter your password to confirm.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={onDelete} className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <Label htmlFor="delete-password">Current password</Label>
              <Input
                id="delete-password"
                type="password"
                autoComplete="current-password"
                required
                placeholder="Your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p
                role="alert"
                className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive"
              >
                {error}
              </p>
            )}
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setDeleteOpen(false)}
                className="rounded-xl"
              >
                Keep account
              </Button>
              <Button type="submit" variant="destructive" disabled={busy} className="rounded-xl">
                {busy ? <Loader2 className="size-4 animate-spin" /> : "Delete forever"}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
