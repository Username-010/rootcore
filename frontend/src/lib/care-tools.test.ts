import { describe, expect, it } from "vitest";
import { CARE_TOOLS, searchCareTools } from "./care-tools";

describe("care finder", () => {
  it("shows every tool once for an empty search", () => {
    const results = searchCareTools("  ", "All");
    expect(results.length).toBe(28);
    expect(new Set(results.map((tool) => tool.path)).size).toBe(results.length);
  });
  it("finds the pest walk by symptom without case sensitivity", () => {
    expect(searchCareTools("  STICKY  ", "All").map((tool) => tool.path)).toEqual(["/pest"]);
  });
  it("requires every search word and combines it with category", () => {
    expect(searchCareTools("soil fresh", "Soil & growth").map((tool) => tool.path)).toEqual(["/topdress"]);
    expect(searchCareTools("soil fresh", "Water & climate")).toEqual([]);
  });
  it("has an honest empty result for unknown terms", () => {
    expect(searchCareTools("spaceship", "All")).toEqual([]);
  });
  it("lists only the requested category without mutating the directory", () => {
    const original = [...CARE_TOOLS];
    const results = searchCareTools("", "Leaves & health");
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((tool) => tool.category === "Leaves & health")).toBe(true);
    expect(CARE_TOOLS).toEqual(original);
  });
});
