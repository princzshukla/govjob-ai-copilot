import { useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import { useAuth } from "../../lib/auth";

const input =
  "h-11 w-full rounded-lg border-2 border-line bg-white px-3 text-base text-ink outline-none placeholder:text-ink/45 focus:border-saffron";

/** Shown once after a first Google sign-in; skippable, editable later in account. */
export function PhoneSetupModal() {
  const { phoneSetupOpen, closePhoneSetup, savePhone, user } = useAuth();
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!phoneSetupOpen || !user) return null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const digits = phone.replace(/\D/g, "");
    if (digits.length !== 10) {
      setError("Enter a 10-digit Indian mobile number.");
      return;
    }
    setBusy(true);
    try {
      await savePhone(digits);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your number.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Complete your profile" onClose={closePhoneSetup}>
      <form onSubmit={submit} className="space-y-3">
        <p className="text-[13.5px] leading-relaxed text-ink/70">
          Thanks for signing in with Google, {user.full_name?.split(" ")[0] || "there"}.
          Add a mobile number so you can use account recovery later. You can skip
          this and add it anytime in your account settings.
        </p>
        <div>
          <label htmlFor="setup-phone" className="mb-1 block text-[11px] font-bold tracking-[.12em] text-ink/55 uppercase">
            Mobile number
          </label>
          <input
            id="setup-phone"
            inputMode="numeric"
            autoComplete="tel-national"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="98765 43210"
            className={input}
          />
        </div>
        {error && (
          <p role="alert" className="rounded-lg border border-alert/40 bg-alert/10 px-3 py-2 text-[13px] font-medium text-alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="h-12 w-full rounded-lg bg-saffron text-[15px] font-bold text-white disabled:opacity-60"
        >
          {busy ? "Saving…" : "Save number"}
        </button>
        <button
          type="button"
          onClick={closePhoneSetup}
          className="h-10 w-full text-[13px] font-semibold text-ink/60 hover:text-ink"
        >
          Skip for now
        </button>
      </form>
    </Modal>
  );
}
