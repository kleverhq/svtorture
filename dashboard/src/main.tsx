import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import { applyThemePreference, readThemePreference } from "./ThemeControl";

applyThemePreference(readThemePreference());

const root = document.querySelector<HTMLDivElement>("#root");
if (!root) throw new Error("dashboard root element is missing");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
