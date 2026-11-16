import { useEffect, useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import { useAuth } from "../../lib/auth";
import * as api from "../../lib/api";
import { toast } from "../../lib/toast";
import type { TelegramLinkStatusResponse } from "../../types";

const input =
  "h-11 w-full rounded-lg border-2 border-line bg-white px-3 text-[14.5px] text-ink outline-none placeholder:text-ink/45 focus:border-saffron";
const label = "mb-1 text-[11px] font-bold tracking-[.12em] text-ink/55 uppercase";
const danger =
  "h-11 w-full rounded-lg border-2 border-alert bg-white px-4 text-[14px] font-bold text-alert transition-colors hover:bg-alert hover:text-white disabled:opacity-50";

export function AccountModal({ onClose }: { onClose: () => void }) {
  const { user, signOut, removeAccount, refresh } = useAuth();

  const [name, setName] = useState(user?.full_name ?? "");
  const [savingName, setSavingName] = useState(false);

  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [pwBusy, setPwBusy] = useState(false);
  const [pwError, setPwError] = useState<string | null>(null);

  const [telegram, setTelegram] = useState<TelegramLinkStatusResponse | null>(null);
  const [tgBusy, setTgBusy] = useState(false);
  const [tgCode, setTgCode] = useState<string | null>(null);
  const [tgBot, setTgBot] = useState("");

  const [deletePw, setDeletePw] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getTelegramStatus()
      .then(setTelegram)
      .catch(() => setTelegram(null));
  }, []);

  if (!user) return null;

  const saveName = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSavingName(true);
    try {
      await api.updateMyFullName(name.trim());
      await refresh();
      toast("success", "Saved", "Your name was updated.");
    } catch (err) {
      toast("warn", "Could not save", err instanceof Error ? err.message : "Try again.");
    } finally {
      setSavingName(false);
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPwError(null);
    if (newPw.length < 8) {
      setPwError("New password must be at least 8 characters.");
      return;
    }
    if (newPw !== confirmPw) {
      setPwError("New passwords do not match.");
      return;
    }
    setPwBusy(true);
    try {
      await api.changePassword(currentPw, newPw);
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
      toast("success", "Password changed", "Other sessions were signed out.");
    } catch (err) {
      setPwError(err instanceof Error ? err.message : "Could not change password.");
    } finally {
      setPwBusy(false);
    }
  };

  const linkTelegram = async () => {
    setTgBusy(true);
    try {
      const data = await api.createTelegramLink();
      setTgCode(data.code);
      setTgBot(data.bot_username);
      toast("info", "Link code generated", `Send /start ${data.code} to @${data.bot_username}`);
    } catch (err) {
      toast("warn", "Could not link Telegram", err instanceof Error ? err.message : "Try again.");
    } finally {
      setTgBusy(false);
    }
  };

  const refreshTelegram = async () => {
    setTgBusy(true);
    try {
      const s = await api.getTelegramStatus();
      setTelegram(s);
      if (s.linked) setTgCode(null);
    } catch {
      /* keep last known state */
    } finally {
      setTgBusy(false);
    }
  };

  const unlinkTelegram = async () => {
    setTgBusy(true);
    try {
      await api.unlinkTelegram();
      setTelegram({ linked: false });
      setTgCode(null);
      toast("info", "Telegram unlinked", "You will no longer receive alerts.");
    } catch (err) {
      toast("warn", "Could not unlink", err instanceof Error ? err.message : "Try again.");
    } finally {
      setTgBusy(false);
    }
  };

  const deleteAccount = async (e: FormEvent) => {
    e.preventDefault();
    setDeleteError(null);
    setDeleteBusy(true);
    try {
      await removeAccount(deletePw);
      onClose();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Could not delete account.");
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <Modal title="My account" onClose={onClose} wide>
      <div className="space-y-6">
        {/* profile */}
        <form onSubmit={saveName} className="space-y-2">
          <p className={label}>Display name</p>
          <div className="flex gap-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={input}
              aria-label="Display name"
            />
            <button
              type="submit"
              disabled={savingName || name.trim() === (user.full_name ?? "")}
              className="h-11 shrink-0 rounded-lg bg-ink px-4 text-[14px] font-bold text-white transition-colors hover:bg-saffron disabled:opacity-40"
            >
              {savingName ? "Saving…" : "Save"}
            </button>
          </div>
          <p className="text-[12px] text-ink/50">
            Signed in as <span className="font-semibold text-ink/70">{user.email}</span>
          </p>
        </form>

        {/* password */}
        <form onSubmit={changePassword} className="space-y-2 border-t border-line pt-5">
          <p className={label}>Change password</p>
          <input
            type="password"
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            placeholder="Current password"
            autoComplete="current-password"
            className={input}
            required
          />
          <div className="grid gap-2 sm:grid-cols-2">
            <input
              type="password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="New password (8+)"
              autoComplete="new-password"
              className={input}
              required
            />
            <input
              type="password"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              placeholder="Confirm new password"
              autoComplete="new-password"
              className={input}
              required
            />
          </div>
          {pwError && (
            <p role="alert" className="rounded-lg border border-alert/40 bg-alert/10 px-3 py-2 text-[13px] font-medium text-alert">
              {pwError}
            </p>
          )}
          <button
            type="submit"
            disabled={pwBusy}
            className="h-10 rounded-lg border-2 border-line bg-white px-4 text-[13px] font-bold text-ink transition-colors hover:border-line-strong disabled:opacity-50"
          >
            {pwBusy ? "Changing…" : "Change password"}
          </button>
        </form>

        {/* telegram */}
        <div className="space-y-2 border-t border-line pt-5">
          <p className={label}>Telegram deadline alerts</p>
          {telegram?.linked ? (
            <>
              <p className="text-[14px] font-semibold text-govgreen">
                ✓ Linked{telegram.chat_id ? ` · ${telegram.chat_id}` : ""}
              </p>
              <button
                onClick={unlinkTelegram}
                disabled={tgBusy}
                className="h-10 rounded-lg border-2 border-line bg-white px-4 text-[13px] font-bold text-ink transition-colors hover:border-line-strong disabled:opacity-50"
              >
                Unlink
              </button>
            </>
          ) : (
            <>
              <p className="text-[13.5px] text-ink/65">
                Get a Telegram message the moment a tracked deadline is close.
              </p>
              {tgCode ? (
                <div className="rounded-lg border border-line bg-cream px-4 py-3">
                  <p className="text-[12px] font-bold tracking-[.12em] text-ink/55 uppercase">
                    Your link code
                  </p>
                  <p className="mt-1 font-mono text-[20px] font-bold tracking-widest text-ink">
                    /start {tgCode}
                  </p>
                  <p className="mt-1 text-[12px] text-ink/60">
                    Send this to @{tgBot || "the bot"} in Telegram. Code expires shortly.
                  </p>
                  <button
                    onClick={refreshTelegram}
                    disabled={tgBusy}
                    className="mt-2 h-9 rounded-lg bg-ink px-3 text-[12.5px] font-bold text-white hover:bg-saffron disabled:opacity-50"
                  >
                    I sent it — check again
                  </button>
                </div>
              ) : (
                <button
                  onClick={linkTelegram}
                  disabled={tgBusy}
                  className="h-10 rounded-lg bg-ink px-4 text-[13px] font-bold text-white transition-colors hover:bg-saffron disabled:opacity-50"
                >
                  {tgBusy ? "Generating code…" : "Link Telegram"}
                </button>
              )}
            </>
          )}
        </div>

        {/* delete */}
        <form onSubmit={deleteAccount} className="space-y-2 border-t border-line pt-5">
          <p className={label}>Danger zone</p>
          <input
            type="password"
            value={deletePw}
            onChange={(e) => setDeletePw(e.target.value)}
            placeholder="Confirm with your password"
            autoComplete="current-password"
            className={input}
            required
          />
          {deleteError && (
            <p role="alert" className="rounded-lg border border-alert/40 bg-alert/10 px-3 py-2 text-[13px] font-medium text-alert">
              {deleteError}
            </p>
          )}
          <button type="submit" disabled={deleteBusy} className={danger}>
            {deleteBusy ? "Deleting…" : "Delete my account permanently"}
          </button>
        </form>

        <button
          onClick={signOut}
          className="h-11 w-full rounded-lg border-2 border-line bg-white text-[14px] font-bold text-ink transition-colors hover:border-saffron hover:text-saffron"
        >
          Sign out
        </button>
      </div>
    </Modal>
  );
}
