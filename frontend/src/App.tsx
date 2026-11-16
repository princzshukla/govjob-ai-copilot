import { Rozgar } from "./views/directions/Rozgar";
import { AD_LAYOUTS } from "./lib/ads";
import { ToastHost } from "./components/rozgar/Toast";

/** Rozgar — government job portal. Free tier: house ads + labelled sponsored placements. */
export default function App() {
  return (
    <div className="min-h-screen bg-paper">
      <Rozgar adLayout={AD_LAYOUTS[0]} />
      <ToastHost />
    </div>
  );
}
