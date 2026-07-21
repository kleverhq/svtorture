import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  applyThemePreference,
  readThemePreference,
  ThemeControl,
} from "./ThemeControl";

const stored = new Map<string, string>();
const storage: Storage = {
  get length() {
    return stored.size;
  },
  clear: () => stored.clear(),
  getItem: (key) => stored.get(key) ?? null,
  key: (index) => [...stored.keys()][index] ?? null,
  removeItem: (key) => stored.delete(key),
  setItem: (key, value) => stored.set(key, value),
};

beforeEach(() => {
  stored.clear();
  Object.defineProperty(window, "localStorage", { configurable: true, value: storage });
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
});

describe("ThemeControl", () => {
  it("defaults to the user theme through Auto", () => {
    render(<ThemeControl />);

    const select = screen.getByLabelText("Theme") as HTMLSelectElement;
    expect(select.value).toBe("auto");
    expect(document.documentElement.dataset.theme).toBe("auto");
  });

  it("applies and persists an explicit theme", () => {
    render(<ThemeControl />);

    fireEvent.change(screen.getByLabelText("Theme"), { target: { value: "light" } });
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("svtorture-theme")).toBe("light");

    fireEvent.change(screen.getByLabelText("Theme"), { target: { value: "dark" } });
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("svtorture-theme")).toBe("dark");
  });

  it("rejects an invalid stored value", () => {
    window.localStorage.setItem("svtorture-theme", "sepia");

    expect(readThemePreference()).toBe("auto");
    applyThemePreference(readThemePreference());
    expect(document.documentElement.dataset.theme).toBe("auto");
  });
});
