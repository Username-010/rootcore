import { useCallback, useEffect, useState } from "react";

const KEY_ON = "plantpilot-ambient";
const KEY_INTENSITY = "plantpilot-ambient-intensity";

type AmbientState = { enabled: boolean; intensity: number };

function readEnabled(): boolean {
  try {
    const v = localStorage.getItem(KEY_ON);
    if (v === null) return true;
    return v === "1" || v === "true";
  } catch {
    return true;
  }
}

function readIntensity(): number {
  try {
    const raw = localStorage.getItem(KEY_INTENSITY);
    if (raw === null) return 40;
    const n = Number(raw);
    if (!Number.isFinite(n)) return 40;
    return Math.max(0, Math.min(100, Math.round(n)));
  } catch {
    return 40;
  }
}

function persist(s: AmbientState) {
  try {
    localStorage.setItem(KEY_ON, s.enabled ? "1" : "0");
    localStorage.setItem(KEY_INTENSITY, String(s.intensity));
  } catch {
    /* ignore */
  }
  if (typeof document !== "undefined") {
    document.documentElement.dataset.ambient =
      s.enabled && s.intensity > 0 ? "on" : "off";
    document.documentElement.style.setProperty("--pp-ambient", String(s.intensity));
  }
}

/** Shared module state so Settings slider + AppShell stay in sync */
let shared: AmbientState = {
  enabled: typeof window !== "undefined" ? readEnabled() : true,
  intensity: typeof window !== "undefined" ? readIntensity() : 40,
};

const listeners = new Set<() => void>();

function setShared(next: AmbientState) {
  shared = next;
  persist(shared);
  listeners.forEach((l) => l());
}

/**
 * Garden decorations: master on/off + continuous intensity 0–100
 * (how many bees/butterflies/leaves fly around).
 */
export function useAmbient() {
  const [, bump] = useState(0);

  useEffect(() => {
    const onChange = () => bump((n) => n + 1);
    listeners.add(onChange);
    // hydrate once on mount (SSR-safe)
    shared = { enabled: readEnabled(), intensity: readIntensity() };
    persist(shared);
    bump((n) => n + 1);
    return () => {
      listeners.delete(onChange);
    };
  }, []);

  const setEnabled = useCallback((on: boolean) => {
    setShared({ ...shared, enabled: on });
  }, []);

  const setIntensity = useCallback((value: number) => {
    const n = Math.max(0, Math.min(100, Math.round(value)));
    // Sliding above 0 turns master switch back on
    setShared({
      enabled: n > 0 ? true : shared.enabled,
      intensity: n,
    });
  }, []);

  const toggle = useCallback(() => {
    setShared({ ...shared, enabled: !shared.enabled });
  }, []);

  const { enabled, intensity } = shared;
  const level = enabled ? intensity : 0;

  return { enabled, setEnabled, intensity, setIntensity, level, toggle };
}
