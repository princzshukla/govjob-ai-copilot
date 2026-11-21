import { Rozgar } from "./views/directions/Rozgar";
import { AD_LAYOUTS } from "./lib/ads";
import { AuthProvider } from "./lib/auth";
import { AuthModal } from "./components/rozgar/AuthModal";
import { PhoneSetupModal } from "./components/rozgar/PhoneSetupModal";
import { ToastHost } from "./components/rozgar/Toast";
import { PrivacyPage } from "./components/rozgar/PrivacyPage";

/** Rozgar — government job portal. Free tier: house ads + labelled sponsored placements. */
export default function App() {
  // Public, account-free route used by the OAuth consent screen / app verification.
  const isPrivacy =
    typeof window !== "undefined" && window.location.pathname === "/privacy";

  return (
    <AuthProvider>
      <div className="min-h-screen bg-paper">
        {isPrivacy ? <PrivacyPage /> : <Rozgar adLayout={AD_LAYOUTS[0]} />}
        <AuthModal />
        <PhoneSetupModal />
        <ToastHost />
      </div>
    </AuthProvider>
  );
}
