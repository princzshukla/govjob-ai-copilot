// src/components/govjob/account-page.tsx
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  BadgeCheck,
  CreditCard,
  KeyRound,
  Loader2,
  LogIn,
  Save,
  ShieldAlert,
  Trash2,
  UserRound,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import * as api from "@/lib/govjob/api";
import { splitPhone } from "@/lib/govjob/phone";
import { useAuth } from "@/hooks/use-auth";
import { useGovJobStore } from "@/stores/govjob-store";
import { DeleteAccountDialog } from "./delete-account-dialog";

export function AccountPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // TanStack Router keeps `__TSR_index` in history.state; > 0 means there is an
  // in-app entry to return to. Blindly linking to a hardcoded
  // /?tab=profile&exam=... wiped the user's exam/tab selection.
  const handleBackToApp = () => {
    const idx =
      (window.history.state as { __TSR_index?: number } | null | undefined)?.__TSR_index ?? 0;
    if (idx > 0) {
      router.history.back();
    } else {
      void router.navigate({
        to: "/",
        search: { tab: "profile", exam: "ssc-cgl-general", week: 1 },
      });
    }
  };

  if (isLoading) return <AccountPageSkeleton />;
  if (!user) return <GuestGate />;
  return <AccountContent user={user} onBack={handleBackToApp} />;
}

function GuestGate() {
  const requestSignIn = useGovJobStore((s) => s.requestSignIn);
  return (
    <div className="mx-auto flex min-h-[50vh] max-w-sm flex-col items-center justify-center gap-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <LogIn className="size-6" />
      </div>
      <h1 className="font-display text-xl font-semibold">Sign in to open your account</h1>
      <p className="text-sm text-muted-foreground">
        Your account page shows your profile, security settings and plan.
      </p>
      <Button onClick={requestSignIn} className="gap-2 rounded-xl">
        <LogIn className="size-4" />
        Sign in
      </Button>
    </div>
  );
}

function AccountContent({ user, onBack }: { user: api.UserOut; onBack: () => void }) {
  const queryClient = useQueryClient();
  const { user: liveUser } = useAuth(); // kept fresh after a name update

  const [name, setName] = useState(liveUser?.full_name ?? "");
  useEffect(() => setName(liveUser?.full_name ?? ""), [liveUser?.full_name]);

  const nameDirty = (liveUser?.full_name ?? "").trim() !== name.trim();

  const saveName = useMutation({
    mutationFn: (fullName: string) => api.updateMyFullName(fullName.trim()),
    onSuccess: (updated) => {
      queryClient.setQueryData(["me"], updated);
      toast.success("Name updated.");
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : "Could not save your name.");
    },
  });

  const onSaveName = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || !nameDirty) return;
    saveName.mutate(trimmed);
  };

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const changePassword = useMutation({
    mutationFn: () => api.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      toast.success("Password changed. Other sessions signed out; this one stays in.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordError(null);
    },
    onError: (err) => {
      setPasswordError(err instanceof Error ? err.message : "Could not change the password.");
    },
  });

  const onChangePassword = (event: FormEvent) => {
    event.preventDefault();
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("Use at least 8 characters.");
      return;
    }
    changePassword.mutate();
  };

  const [deleteOpen, setDeleteOpen] = useState(false);

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-1 py-2">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold">Account settings</h1>
          <p className="text-sm text-muted-foreground">
            Profile, security and plan — saved to your GovJob Copilot account.
          </p>
        </div>
        <Button variant="ghost" size="sm" className="gap-2 rounded-xl" onClick={onBack}>
          <ArrowLeft className="size-4" />
          Back to app
        </Button>
      </div>

      {/* Section 1: Profile */}
      <Card className="bg-card/60">
        <CardHeader className="flex flex-row items-start gap-3 space-y-0 pb-3">
          <span className="mt-0.5 flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <UserRound className="size-5" />
          </span>
          <div>
            <CardTitle className="text-base">Profile</CardTitle>
            <CardDescription>Only your name is editable; email and phone stay read-only.</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSaveName} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="account-name">Full name</Label>
              <Input
                id="account-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
                placeholder="Ada Lovelace"
                maxLength={120}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="account-email">Email</Label>
                <Input id="account-email" value={user.email} disabled readOnly />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="account-phone">Phone</Label>
                <div className="flex">
                  <span
                    aria-hidden="true"
                    className="inline-flex items-center rounded-l-md border border-r-0 border-input bg-muted px-3 text-sm text-muted-foreground"
                  >
                    +91
                  </span>
                  <Input
                    id="account-phone"
                    value={splitPhone(user.phone)?.national ?? ""}
                    placeholder="Not set"
                    disabled
                    readOnly
                    className="rounded-l-none"
                  />
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={!nameDirty || name.trim().length === 0 || saveName.isPending}
                className="gap-2 rounded-xl"
              >
                {saveName.isPending ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
                Save name
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Section 2: Security */}
      <Card className="bg-card/60">
        <CardHeader className="flex flex-row items-start gap-3 space-y-0 pb-3">
          <span className="mt-0.5 flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <KeyRound className="size-5" />
          </span>
          <div>
            <CardTitle className="text-base">Security</CardTitle>
            <CardDescription>
              Changing your password signs out every other session; this one stays in.
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={onChangePassword} className="space-y-4">
            {/* Password managers need a username field alongside the passwords. */}
            <input
              type="text"
              name="username"
              autoComplete="username"
              value={user.email}
              readOnly
              hidden
              aria-hidden="true"
              tabIndex={-1}
            />
            <div className="space-y-1.5">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                required
                placeholder="Your current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="new-password">New password</Label>
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="8+ characters"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm-password">Confirm new password</Label>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="Repeat it"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </div>
            {passwordError && (
              <p
                role="alert"
                className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive"
              >
                {passwordError}
              </p>
            )}
            <div className="flex justify-end">
              <Button
                type="submit"
                disabled={changePassword.isPending || !currentPassword || !newPassword}
                className="gap-2 rounded-xl"
              >
                {changePassword.isPending ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <BadgeCheck className="size-4" />
                )}
                Change password
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Section 3: Subscription */}
      <Card className="bg-card/60">
        <CardHeader className="flex flex-row items-start gap-3 space-y-0 pb-3">
          <span className="mt-0.5 flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <CreditCard className="size-5" />
          </span>
          <div>
            <CardTitle className="text-base">Subscription</CardTitle>
            <CardDescription>Your plan and billing will live here.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="rounded-md px-2 py-1 text-xs">
              Free
            </Badge>
            <p className="text-sm text-muted-foreground">
              Everything is free during the beta. Paid plans will be announced here.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Section 4: Danger zone */}
      <Card className="border-destructive/40 bg-destructive/5">
        <CardHeader className="flex flex-row items-start gap-3 space-y-0 pb-3">
          <span className="mt-0.5 flex size-9 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
            <ShieldAlert className="size-5" />
          </span>
          <div>
            <CardTitle className="text-base text-destructive">Danger zone</CardTitle>
            <CardDescription>Irreversible actions — think twice.</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="flex items-center justify-between gap-4">
          <p className="max-w-sm text-xs text-muted-foreground">
            Deletes your profile, resume draft, roadmap, progress, mastery and drill
            history. You will be signed out immediately, and this email can be used to
            register again.
          </p>
          <Button variant="destructive" size="sm" className="gap-2 rounded-xl" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="size-4" />
            Delete account
          </Button>
        </CardContent>
      </Card>

      <DeleteAccountDialog open={deleteOpen} onOpenChange={setDeleteOpen} />
    </div>
  );
}

function AccountPageSkeleton() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 px-1 py-2">
      <Skeleton className="h-8 w-40 rounded-lg" />
      {[...Array(4)].map((_, i) => (
        <Skeleton key={i} className="h-40 w-full rounded-xl" />
      ))}
    </div>
  );
}
