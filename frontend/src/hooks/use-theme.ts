import { useCallback, useEffect, useState } from "react";

export type Theme =
  | "system"
  | "light"
  | "dark"
  | "blossom" // pink / purple floral
  | "meadow" // soft green garden
  | "dusk"; // deep purple evening

const THEME_ORDER: Theme[] = ["system", "light", "dark", "blossom", "meadow", "dusk"];

export const THEME_META: Record<
  Theme,
  { label: string; emoji: string; description: string }
> = {
  system: { label: "System", emoji: "💻", description: "Follow device light/dark" },
  light: { label: "Light garden", emoji: "🌿", description: "Clean green daylight" },
  dark: { label: "Night garden", emoji: "🌙", description: "Low-light dark mode" },
  blossom: { label: "Blossom", emoji: "🌸", description: "Pink & purple florals" },
  meadow: { label: "Meadow", emoji: "🌼", description: "Warm sunny meadow" },
  dusk: { label: "Dusk", emoji: "🌺", description: "Deep violet evening" },
};

function getSystemTheme(): "light" | "dark" {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: Theme) {
  const root = document.documentElement;
  root.classList.remove("dark", "theme-blossom", "theme-meadow", "theme-dusk");

  if (theme === "system") {
    root.classList.toggle("dark", getSystemTheme() === "dark");
    return;
  }
  if (theme === "dark" || theme === "dusk") {
    root.classList.add("dark");
  }
  if (theme === "blossom") root.classList.add("theme-blossom");
  if (theme === "meadow") root.classList.add("theme-meadow");
  if (theme === "dusk") root.classList.add("theme-dusk");
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem("plantpilot-theme") as Theme | null;
    if (stored && THEME_ORDER.includes(stored)) return stored;
    return "blossom"; // friendly default
  });

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem("plantpilot-theme", theme);

    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => applyTheme("system");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
  }, []);

  const cycleTheme = useCallback(() => {
    setThemeState((current) => {
      const i = THEME_ORDER.indexOf(current);
      return THEME_ORDER[(i + 1) % THEME_ORDER.length];
    });
  }, []);

  return { theme, setTheme, cycleTheme, themes: THEME_ORDER, meta: THEME_META };
}
