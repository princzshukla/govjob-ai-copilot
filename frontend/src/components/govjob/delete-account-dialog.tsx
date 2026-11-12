// src/components/govjob/delete-account-dialog.tsx
import { FormEvent, useEffect, useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";

import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/use-auth";

interface DeleteAccountDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Password-confirmed account deletion. After the server erases the account and
 * cascades, the local session/cache is cleared by useAuth and the user is
 * sent back to the app home as a guest.
 */
export function DeleteAccountDialog({ open, onOpenChange }: DeleteAccountDialogProps) {
  const { removeAccount } = useAuth();
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setPassword("");
      setError(null);
      setBusy(false);
    }
  }, [open]);

  const onDelete = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await removeAccount(password);
      onOpenChange(false);
      toast.success("Account deleted.");
      navigate({ to: "/", search: { tab: "profile", exam: "ssc-cgl-general", week: 1 } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the account.");
      setBusy(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-sm">
        <AlertDialogHeader>
          <div className="flex size-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
            <Trash2 className="size-5" />
          </div>
          <AlertDialogTitle className="font-display">Delete account</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently erases your account, profile, roadmap, week progress,
            mastery and drill history. There is no undo. Enter your current password
            to confirm.
          </AlertDialogDescription>
        </AlertDialogHeader>
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
              onClick={() => onOpenChange(false)}
              className="rounded-xl"
            >
              Keep account
            </Button>
            <Button type="submit" variant="destructive" disabled={busy} className="rounded-xl">
              {busy ? <Loader2 className="size-4 animate-spin" /> : "Delete forever"}
            </Button>
          </div>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  );
}
