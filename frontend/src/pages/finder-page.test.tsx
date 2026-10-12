import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { FinderPage } from "./finder-page";
import { CARE_TOOLS } from "@/lib/care-tools";

describe("FinderPage", () => {
  it("renders accessible controls and every working care destination", () => {
    const html = renderToStaticMarkup(<MemoryRouter><FinderPage /></MemoryRouter>);
    expect(html).toContain("Find the right care tool");
    expect(html).toContain('for="care-search"');
    expect(html).toContain('for="care-category"');
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain("28 tools");
    const app = readFileSync(new URL("../App.tsx", import.meta.url), "utf8");
    for (const tool of CARE_TOOLS) {
      expect(html).toContain(`href="${tool.path}"`);
      expect(app).toContain(`path="${tool.path}"`);
    }
  });
});
