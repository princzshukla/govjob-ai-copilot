import { useEffect, useState, type FormEvent } from "react";
import { Modal } from "./Modal";
import { useAuth } from "../../lib/auth";

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
