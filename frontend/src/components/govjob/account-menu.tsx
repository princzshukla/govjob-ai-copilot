// src/components/govjob/account-menu.tsx
import { useState } from "react";
import {
  LogIn,
  LogOut,
  Settings,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { splitPhone } from "@/lib/govjob/phone";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Link } from "@tanstack/react-router";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/use-auth";
import { useGovJobStore } from "@/stores/govjob-store";
import { DeleteAccountDialog } from "./delete-account-dialog";

/** Header account control: avatar dropdown with account actions. */
export function AccountMenu() {
  const { user, isLoading, signOut } = useAuth();
  const requestSignIn = useGovJobStore((s) => s.requestSignIn);

  const [deleteOpen, setDeleteOpen] = useState(false);

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
              <span className="text-[11px] font-normal text-muted-foreground">
                {splitPhone(user.phone)?.national
                  ? `+91 ${splitPhone(user.phone)!.national}`
                  : user.phone}
              </span>
            ) : null}
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link
              to="/account"
              className="flex w-full items-center gap-2"
            >
              <Settings className="text-muted-foreground" />
              Account settings
            </Link>
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

      <DeleteAccountDialog open={deleteOpen} onOpenChange={setDeleteOpen} />
    </>
  );
}
