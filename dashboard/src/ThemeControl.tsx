import { useEffect, useState } from "react";

export type ThemePreference = "auto" | "light" | "dark";

const STORAGE_KEY = "svtorture-theme";
const THEMES: ThemePreference[] = ["auto", "light", "dark"];

function isThemePreference(value: string | null): value is ThemePreference {
  return THEMES.some((theme) => theme === value);
}

export function readThemePreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isThemePreference(stored) ? stored : "auto";
  } catch {
    return "auto";
  }
}

export function applyThemePreference(theme: ThemePreference): void {
  document.documentElement.dataset.theme = theme;
}

function storeThemePreference(theme: ThemePreference): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // The selected theme still applies for this page when storage is unavailable.
  }
}

export function ThemeControl() {
  const [theme, setTheme] = useState<ThemePreference>(readThemePreference);

  useEffect(() => {
    applyThemePreference(theme);
    storeThemePreference(theme);
  }, [theme]);

  return (
    <label className="theme-control">
      <span>Theme</span>
      <select
        aria-label="Theme"
        value={theme}
        onChange={(event) => setTheme(event.target.value as ThemePreference)}
      >
        <option value="auto">Auto</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );
}
