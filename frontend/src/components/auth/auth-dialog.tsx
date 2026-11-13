// src/components/auth/auth-dialog.tsx
import { FormEvent, useEffect, useState } from "react";
import { Loader2, LogIn, UserPlus } from "lucide-react";
import { toast } from "sonner";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useGovJobStore } from "@/stores/govjob-store";
import { useAuth } from "@/hooks/use-auth";

/**
 * One dialog, two tabs (Sign in / Create account). Renders from the store's
 * signInRequested flag, which any 401 or explicit save-point action raises.
 * A guest's parsed draft stays in memory while this dialog is open.
 */
export function AuthDialog() {
  const open = useGovJobStore((s) => s.signInRequested);
  const closeSignIn = useGovJobStore((s) => s.closeSignIn);
  const { signIn, signUp } = useAuth();

  const [tab, setTab] = useState<"signin" | "register">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Reset fields whenever the dialog opens; never keep stale passwords around.
  useEffect(() => {
    if (open) {
      setPassword("");
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const handleClose = () => {
    closeSignIn();
    setError(null);
    setPassword("");
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (tab === "signin") {
        await signIn(email, password);
        toast.success("Welcome back!");
      } else {
        await signUp(name, email, password, phone);
        toast.success("Account created — welcome!");
      }
      handleClose();
      setName("");
      setEmail("");
      setPassword("");
      setPhone("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && handleClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {tab === "signin" ? <LogIn className="size-5" /> : <UserPlus className="size-5" />}
          </div>
          <DialogTitle className="font-display">
            {tab === "signin" ? "Sign in to GovJob Copilot" : "Create your free account"}
          </DialogTitle>
          <DialogDescription>
            The exam matches and roadmap you build here stay saved to your account. Your guest
            draft is kept and attached automatically.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="mt-1 w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="signin">Sign in</TabsTrigger>
            <TabsTrigger value="register">Create account</TabsTrigger>
          </TabsList>

          <form onSubmit={onSubmit} autoComplete="on">
            <TabsContent value="signin" className="space-y-4 pt-4">
              <div className="space-y-1.5">
                <Label htmlFor="auth-email">Email</Label>
                <Input
                  id="auth-email"
                  type="email"
                  autoComplete="email"
                  required
                  pattern="[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
                  title="Use your full email, for example you@example.com"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="auth-password">Password</Label>
                <Input
                  id="auth-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="Your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </TabsContent>

            <TabsContent value="register" className="space-y-4 pt-4">
              <div className="space-y-1.5">
                <Label htmlFor="auth-full-name">Full name</Label>
                <Input
                  id="auth-full-name"
                  autoComplete="name"
                  required
                  placeholder="Ada Lovelace"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="auth-email-up">Email</Label>
                <Input
                  id="auth-email-up"
                  type="email"
                  autoComplete="email"
                  required
                  pattern="[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
                  title="Use your full email, for example you@example.com"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="auth-phone">
                  Phone <span className="text-muted-foreground">(optional)</span>
                </Label>
                <div className="flex">
                  <span
                    aria-hidden="true"
                    className="inline-flex items-center rounded-l-md border border-r-0 border-input bg-muted px-3 text-sm font-semibold text-muted-foreground"
                  >
                    +91
                  </span>
                  <Input
                    id="auth-phone"
                    type="tel"
                    autoComplete="tel-national"
                    inputMode="numeric"
                    pattern="[0-9]{10}"
                    maxLength={10}
                    placeholder="9876543210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))}
                    className="rounded-l-none"
                  />
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Stored as +91 number; we never ask for it again.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="auth-password-up">Password</Label>
                <Input
                  id="auth-password-up"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="At least 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <p className="text-[11px] text-muted-foreground">
                  Use 8+ characters. We only ever store a hash of it.
                </p>
              </div>
            </TabsContent>

            {error && (
              <p
                role="alert"
                className="mt-4 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs font-medium text-destructive"
              >
                {error}
              </p>
            )}

            <Button
              type="submit"
              disabled={busy}
              className={cn("mt-5 h-11 w-full rounded-xl font-semibold")}
            >
              {busy ? (
                <Loader2 className="size-4 animate-spin" />
              ) : tab === "signin" ? (
                "Sign in"
              ) : (
                "Create account"
              )}
            </Button>
          </form>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
