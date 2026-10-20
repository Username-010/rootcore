import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { IntegrationGuide, ChannelInfo } from "./sensors-page";

describe("sensor setup and channel information", () => {
  it("distinguishes server-side HA configuration from unimplemented brand adapters", () => {
    const html = renderToStaticMarkup(<IntegrationGuide />);
    expect(html).toContain("Administrator-managed");
    expect(html).toContain("Tuya");
    expect(html).toContain("via Home Assistant");
    expect(html).toContain("No direct Tuya");
  });
  it("does not relabel humidity as calibrated soil moisture or invent light", () => {
    const html = renderToStaticMarkup(<ChannelInfo readings={[{entity_id:"sensor.test_humidity",name:"Test humidity",value:42,unit:"%",timestamp:"2026-10-20T08:00:00Z",metric:"humidity",status:"current"}]} />);
    expect(html).toContain("Light channel not exposed");
    expect(html).toContain("not calibrated soil moisture");
    expect(html).not.toContain("0 lux");
  });
});
