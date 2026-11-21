import { BrowserRouter, Navigate, Route, Routes, useSearchParams } from "react-router-dom";
import { Rozgar } from "./views/directions/Rozgar";
import { PATH_FOR_TAB, tabFromLegacyParam, type Tab } from "./routes";
import { AD_LAYOUTS } from "./lib/ads";
import { AuthProvider } from "./lib/auth";
import { AuthModal } from "./components/rozgar/AuthModal";
import { PhoneSetupModal } from "./components/rozgar/PhoneSetupModal";
import { ToastHost } from "./components/rozgar/Toast";
import { PrivacyPage } from "./components/rozgar/PrivacyPage";
import { NotFound } from "./components/rozgar/NotFound";

/** `/?tab=admit` and friends forward to the real path, without a reload. */
function HomeRoute() {
  const [params] = useSearchParams();
  const legacyTab = tabFromLegacyParam(params.get("tab"));
  if (legacyTab) return <Navigate to={PATH_FOR_TAB[legacyTab]} replace />;
  return <Rozgar adLayout={AD_LAYOUTS[0]} tab="Latest Jobs" />;
}

function TabRoute({ tab }: { tab: Tab }) {
  return <Rozgar adLayout={AD_LAYOUTS[0]} tab={tab} />;
}

/** Rozgar — government job portal. Free tier: house ads + labelled sponsored placements. */
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-paper">
          <Routes>
            <Route path="/" element={<HomeRoute />} />
            <Route path="/admit-cards" element={<TabRoute tab="Admit Cards" />} />
            <Route path="/eligibility" element={<TabRoute tab="My Eligibility" />} />
            <Route path="/roadmap" element={<TabRoute tab="My Roadmap" />} />
            <Route
              path="/tools/photo-signature-resizer"
              element={<TabRoute tab="Photo & Signature" />}
            />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
          <AuthModal />
          <PhoneSetupModal />
          <ToastHost />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
