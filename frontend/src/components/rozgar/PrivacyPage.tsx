/** Public privacy policy. Must be reachable without an account so Google can
 * review it during OAuth app verification (https://www.rozgarboard.in/privacy). */

const H2 = ({ children }: { children: React.ReactNode }) => (
  <h2 className="mt-9 border-b border-line pb-2 text-[17px] font-extrabold tracking-tight text-ink">
    {children}
  </h2>
);

const P = ({ children }: { children: React.ReactNode }) => (
  <p className="mt-3 text-[14.5px] leading-relaxed text-ink/80">{children}</p>
);

const Li = ({ children }: { children: React.ReactNode }) => (
  <li className="ml-5 mt-2 list-disc text-[14.5px] leading-relaxed text-ink/80">{children}</li>
);

export function PrivacyPage() {
  return (
    <main className="min-h-screen bg-paper">
      <header className="border-b-2 border-ink bg-cream">
        <div className="mx-auto flex max-w-[860px] items-center justify-between px-4 py-4 sm:px-5">
          <p className="text-[20px] font-extrabold tracking-tight text-ink">
            Rozgar<span className="text-saffron">Board</span>
          </p>
          <a
            href="/"
            className="inline-flex min-h-11 items-center rounded-lg border-2 border-line-strong bg-white px-4 text-[13.5px] font-bold text-ink hover:bg-paper"
          >
            ← Back to RozgarBoard
          </a>
        </div>
      </header>

      <div className="mx-auto max-w-[860px] px-4 py-10 sm:px-5">
        <h1 className="text-[30px] font-extrabold tracking-tight text-ink sm:text-[36px]">
          Privacy Policy
        </h1>
        <p className="mt-2 font-mono text-[11px] font-bold tracking-[.14em] text-ink/50 uppercase">
          Effective 21 November 2026 · RozgarBoard (govjob-ai-copilot)
        </p>

        <P>
          RozgarBoard helps you find Indian government job notifications, check your
          eligibility, and prepare a study plan. This policy explains what we collect,
          why we collect it, and the choices you have. By using the service you agree to
          this policy.
        </P>

        <H2>1. Information we collect</H2>
        <P>When you create an account or sign in we may collect:</P>
        <ul>
          <Li><strong>Account details:</strong> email address, full name, and (optionally) a mobile number.</Li>
          <Li><strong>Google sign-in:</strong> if you choose “Continue with Google”, Google sends us your name, email address, a verified-email flag, and a unique account identifier (<code className="font-mono text-[13px]">sub</code>). We do not receive your Google password. We do not link a Google sign-in to an existing password account automatically.</Li>
          <Li><strong>Profile data you choose to save:</strong> date of birth, gender, category, disability status, domicile, education, marks, skills, and similar details used to check eligibility.</Li>
          <Li><strong>Resume text:</strong> submitted for parsing. We do not store the raw resume text; we keep only the structured profile you choose to save.</Li>
          <Li><strong>Telegram link:</strong> if you opt in to alerts, we store your verified Telegram chat ID.</Li>
          <Li><strong>Technical data:</strong> IP address and request metadata used for rate limiting and security logging.</Li>
        </ul>

        <H2>2. How we use your information</H2>
        <ul>
          <Li>To create and maintain your account and session, and to remember your saved profile across devices.</Li>
          <Li>To check your eligibility against public job notifications and generate your study plan.</Li>
          <Li>To send deadline reminders you request through Telegram.</Li>
          <Li>To protect the service from abuse, including rate limiting and fraud prevention.</Li>
        </ul>
        <P>
          We do not sell your personal information. Sponsored placements are labelled and
          are not targeted using your saved profile.
        </P>

        <H2>3. Cookies and sessions</H2>
        <P>
          Signing in sets a session cookie (default name <code className="font-mono text-[13px]">session_id</code>)
          that keeps you logged in for up to seven days; it is HTTP-only and, on HTTPS
          deployments, Secure. During Google sign-in we also set a short-lived, signed
          state cookie used to protect the authorization flow against CSRF. You can sign
          out at any time, which clears your session.
        </P>

        <H2>4. Service providers</H2>
        <P>
          We use third-party providers to run the service: Groq (resume and notification
          processing), Supabase (database), Redis (rate limiting), Google (sign-in),
          Vercel and Render (hosting), and Telegram (alerts, only if you link it). These
          providers process data on our behalf and under their own terms. Google’s use
          of information is governed by its own privacy policy.
        </P>

        <H2>5. Your choices and deletion</H2>
        <P>
          You can update your name, mobile number, and saved profile from your account
          settings, unlink Telegram at any time, and delete your account from the account
          settings. Deleting your account removes your user record, sessions, saved
          profile, roadmaps, progress, and Telegram link.
        </P>

        <H2>6. Data security</H2>
        <P>
          Passwords are stored only as salted hashes; session tokens are stored as hashes,
          not in plain text. Access to personal data is restricted to the minimum needed
          to operate the service. No system is perfectly secure, and we cannot guarantee
          absolute security.
        </P>

        <H2>7. Children</H2>
        <P>
          RozgarBoard is intended for people preparing for government employment and is
          not directed at children under 13. We do not knowingly collect personal data
          from children.
        </P>

        <H2>8. Changes to this policy</H2>
        <P>
          We may update this policy as the service changes. The “Effective” date at the
          top will be updated when we do, and significant changes will be announced in
          the app.
        </P>

        <H2>9. Contact</H2>
        <P>
          Questions about this policy or your data can be sent to{" "}
          <a href="mailto:ayush24katiyar@gmail.com" className="font-semibold text-saffron underline underline-offset-2">
            ayush24katiyar@gmail.com
          </a>.
        </P>

        <footer className="mt-12 border-t border-line pt-5 text-[12.5px] text-ink/55">
          © 2026 RozgarBoard · Government jobs in India
        </footer>
      </div>
    </main>
  );
}
