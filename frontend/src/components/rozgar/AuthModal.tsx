import { useEffect, useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import { useAuth } from "../../lib/auth";
import { startGoogleSignIn } from "../../lib/api";

function GoogleGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="size-[18px] shrink-0" aria-hidden="true">
      <path fill="#4285F4" d="M21.6 12.23c0-.68-.06-1.34-.18-1.97H12v3.73h5.38a4.6 4.6 0 0 1-2 3.02v2.5h3.24c1.9-1.75 2.98-4.33 2.98-7.28Z" />
      <path fill="#34A853" d="M12 22c2.7 0 4.97-.9 6.62-2.42l-3.24-2.5c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H3.07v2.58A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.41 13.92A6 6 0 0 1 6.09 12c0-.67.11-1.32.32-1.92V7.5H3.07a10 10 0 0 0 0 9l3.34-2.58Z" />
      <path fill="#EA4335" d="M12 5.98c1.47 0 2.79.5 3.83 1.5l2.87-2.87C16.96 2.98 14.7 2 12 2A10 10 0 0 0 3.07 7.5l3.34 2.58C7.2 7.74 9.4 5.98 12 5.98Z" />
    </svg>
  );
}

const input =
  "h-11 w-full rounded-lg border-2 border-line bg-white px-3 text-base text-ink outline-none placeholder:text-ink/45 focus:border-saffron sm:text-[14.5px]";
const label = "mb-1 text-[11px] font-bold tracking-[.12em] text-ink/55 uppercase";

function digitsOnly(v: string): string {
  return v.replace(/\D/g, "");
}

export function AuthModal() {
  const {
    authModalOpen,
    authModalMode,
    closeAuthModal,
    promptSignIn,
    signIn,
    signUp,
    googleEnabled,
  } = useAuth();
  const [mode, setMode] = useState(authModalMode);
  useEffect(() => setMode(authModalMode), [authModalMode]);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!authModalOpen) return null;

  const isRegister = mode === "register";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRegister) {
      const digits = digitsOnly(phone);
      if (phone.trim() && digits.length !== 10) {
        setError("Phone must be a 10-digit Indian mobile number (or leave it blank).");
        return;
      }
      if (password.length < 8) {
        setError("Password must be at least 8 characters.");
        return;
      }
      if (!name.trim()) {
        setError("Please tell us your name.");
        return;
      }
    }

    setBusy(true);
    try {
      if (isRegister) {
        await signUp(name.trim(), email.trim(), password, phone.trim() || undefined);
      } else {
        await signIn(email.trim(), password);
      }
      setPassword("");
      closeAuthModal();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      title={isRegister ? "Create your account" : "Sign in"}
      onClose={closeAuthModal}
    >
      <form onSubmit={submit} className="space-y-4">
        {googleEnabled && (
          <>
            <button
              type="button"
              onClick={() => {
                closeAuthModal();
                startGoogleSignIn();
              }}
              className="flex h-12 w-full items-center justify-center gap-2.5 rounded-lg border border-[#747775] bg-white px-3 text-[14px] font-medium text-[#1f1f1f] transition-colors hover:bg-[#f2f2f2] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-saffron"
            >
              <GoogleGlyph />
              {isRegister ? "Sign up with Google" : "Continue with Google"}
            </button>
            <div className="flex items-center gap-3" aria-hidden="true">
              <span className="h-px flex-1 bg-line" />
              <span className="text-[11px] font-semibold tracking-[.12em] text-ink/45 uppercase">or</span>
              <span className="h-px flex-1 bg-line" />
            </div>
          </>
        )}
        {isRegister && (
          <div>
            <label htmlFor="auth-name" className={label}>
              Full name
            </label>
            <input
              id="auth-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              placeholder="Aarav Kumar"
              className={input}
              required
            />
          </div>
        )}

        <div>
          <label htmlFor="auth-email" className={label}>
            Email
          </label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            placeholder="you@example.com"
            className={input}
            required
          />
        </div>

        {isRegister && (
          <div>
            <label htmlFor="auth-phone" className={label}>
              Phone (optional)
            </label>
            <input
              id="auth-phone"
              inputMode="numeric"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel-national"
              placeholder="98765 43210"
              className={input}
            />
          </div>
        )}

        <div>
          <label htmlFor="auth-password" className={label}>
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            placeholder={isRegister ? "At least 8 characters" : "Your password"}
            className={input}
            required
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
          className="h-12 w-full rounded-lg bg-saffron text-[15px] font-bold text-white shadow-[0_2px_0_rgba(0,0,0,.12)] transition-opacity disabled:opacity-60"
        >
          {busy
            ? isRegister
              ? "Creating account…"
              : "Signing in…"
            : isRegister
              ? "Create account"
              : "Sign in"}
        </button>

        <p className="text-center text-[13px] text-ink/60">
          {isRegister ? (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => promptSignIn("login")}
                className="font-bold text-saffron hover:underline"
              >
                Sign in
              </button>
            </>
          ) : (
            <>
              New here?{" "}
              <button
                type="button"
                onClick={() => promptSignIn("register")}
                className="font-bold text-saffron hover:underline"
              >
                Create an account
              </button>
            </>
          )}
        </p>
      </form>
    </Modal>
  );
}
