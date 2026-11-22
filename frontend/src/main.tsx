import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import "./fonts.css";
import "./index.css";
import App from "./App";

const container = document.getElementById("root")!;
const app = (
  <StrictMode>
    <App />
  </StrictMode>
);

// Prerendered pages already contain markup — hydrate them. The plain SPA shell
// (dev, or a route the build did not generate) still mounts normally.
if (container.childNodes.length > 0) {
  hydrateRoot(container, app);
} else {
  createRoot(container).render(app);
}
