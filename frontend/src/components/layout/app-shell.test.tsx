import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppShell } from "./app-shell";

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({ user: null, households: [], activeHousehold: null, logout: vi.fn() }),
}));
vi.mock("@/hooks/use-theme", () => ({
  THEME_META: { system: { label: "System", emoji: "" } },
  useTheme: () => ({ theme: "system", cycleTheme: vi.fn(), meta: {} }),
}));
vi.mock("@/hooks/use-ambient", () => ({ useAmbient: () => ({ level: 0 }) }));

function mobileMarkup(path = "/") {
  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={[path]}>
      <AppShell />
    </MemoryRouter>,
  );
  return html.match(/<nav[^>]*aria-label="Mobile"[^>]*>([\s\S]*?)<\/nav>/)?.[1] ?? "";
}

describe("navigation", () => {
  it("keeps four essentials visible and groups every other destination", () => {
    const html = mobileMarkup();
    expect(html).toContain("More tools and pages");
    const primary = html.split("<details")[0];
    expect((primary.match(/<a /g) ?? []).length).toBe(4);
    for (const path of ["/", "/finder", "/plants", "/tasks"]) {
      expect(primary).toContain(`href="${path}"`);
    }
    expect(html).toMatch(/<summary[^>]*>[\s\S]*?More[\s\S]*?<\/summary>/);
    for (const heading of ["Care", "Jobs", "Grow", "Home"]) {
      expect(html).toContain(heading);
    }
    const full = renderToStaticMarkup(
      <MemoryRouter>
        <AppShell />
      </MemoryRouter>,
    );
    const desktop = full.match(/<nav[^>]*aria-label="Main"[^>]*>([\s\S]*?)<\/nav>/)?.[1] ?? "";
    const desktopPrimary = desktop.split("<details")[0];
    expect((desktopPrimary.match(/<a /g) ?? []).length).toBe(4);
    expect(desktop).toContain("Care");
    expect(desktop).toContain("Jobs");
    const paths = (markup: string) => [...markup.matchAll(/href="([^"]+)"/g)].map((match) => match[1]).sort();
    expect(paths(html)).toEqual(paths(desktop));
    expect(new Set(paths(html)).size).toBe(paths(html).length);
    for (const path of ["/sensors", "/calendar", "/timeline", "/stats", "/household", "/settings", "/round", "/humidity"]) {
      expect(html).toContain(`href="${path}"`);
    }
  });
});
