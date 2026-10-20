import { describe, expect, it, vi } from "vitest";
import { apiRequest } from "./api";
import { loadSensorPlants } from "./sensor-plants";
vi.mock("./api", () => ({ apiRequest: vi.fn() }));

describe("sensor plant selector", () => {
  it("uses valid page sizes and disables unrelated cover writes", async () => {
    vi.mocked(apiRequest).mockResolvedValueOnce({ items: [{id:"a",nickname:"A"}], total:201 }).mockResolvedValueOnce({ items: [{id:"b",nickname:"B"}], total:201 });
    const result = await loadSensorPlants("test-home");
    expect(apiRequest).toHaveBeenNthCalledWith(1, "/api/v1/households/test-home/plants?limit=200&offset=0&backfill_covers=false");
    expect(apiRequest).toHaveBeenNthCalledWith(2, "/api/v1/households/test-home/plants?limit=200&offset=200&backfill_covers=false");
    expect(result.map(p => p.id)).toEqual(["a", "b"]);
  });
});
