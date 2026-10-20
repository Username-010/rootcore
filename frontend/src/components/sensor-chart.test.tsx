import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { SensorChart, type SensorReading } from "./sensor-chart";

const reading = (value: number | null, timestamp: string): SensorReading => ({ entity_id: "sensor.test", name: "Test humidity", value, unit: "%", timestamp, metric: "humidity", status: value === null ? "unavailable" : "current" });

describe("SensorChart", () => {
  it("shows an honest empty state without a fabricated chart", () => {
    const html = renderToStaticMarkup(<SensorChart points={[]} />);
    expect(html).toContain("No recorded history");
    expect(html).not.toContain("<polyline");
  });
  it("keeps unavailable gaps and source units visible in an accessible table", () => {
    const html = renderToStaticMarkup(<SensorChart points={[reading(40, "2026-10-20T08:00:00Z"), reading(null, "2026-10-20T09:00:00Z"), reading(42, "2026-10-20T10:00:00Z")]} />);
    expect(html).toContain("Recorded values");
    expect(html).toContain("unavailable");
    expect(html).toContain("2026-10-20T08:00:00Z");
    expect(html).toContain("40 %");
    expect(html).not.toContain("<polyline");
  });
});
