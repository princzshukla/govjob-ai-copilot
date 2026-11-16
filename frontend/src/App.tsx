import { Rozgar } from "./views/directions/Rozgar";
import { AD_LAYOUTS } from "./lib/ads";
import { AuthProvider } from "./lib/auth";
import { AuthModal } from "./components/rozgar/AuthModal";
import { ToastHost } from "./components/rozgar/Toast";

/** Rozgar — government job portal. Free tier: house ads + labelled sponsored placements. */
export default function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-paper">
        <Rozgar adLayout={AD_LAYOUTS[0]} />
        <AuthModal />
        <ToastHost />
      </div>
    </AuthProvider>
  );
}
