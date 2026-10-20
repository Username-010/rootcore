import { afterEach, describe, expect, it, vi } from "vitest";
import {
  NOTIFY_DAY_KEY,
  NOTIFY_KEY,
  disableDueNotify,
  enableDueNotify,
  notifyEnabled,
  showDueNotification,
} from "./device-notify";

function mockStorage() {
  const data = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => {
      data.set(k, v);
    },
    removeItem: (k: string) => {
      data.delete(k);
    },
    clear: () => data.clear(),
  });
  vi.stubGlobal("window", { isSecureContext: true });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("device notify", () => {
  it("stores an enabled flag only after permission is granted", async () => {
    mockStorage();
    vi.stubGlobal("Notification", {
      permission: "default",
      requestPermission: vi.fn().mockResolvedValue("granted"),
    });
    await expect(enableDueNotify()).resolves.toBe("granted");
    expect(notifyEnabled()).toBe(true);
  });

  it("shows one due reminder per calendar day", () => {
    mockStorage();
    const constructed: unknown[] = [];
    class FakeNotification {
      static permission = "granted";
      constructor(title: string, opts?: NotificationOptions) {
        constructed.push([title, opts]);
      }
    }
    vi.stubGlobal("Notification", FakeNotification);
    localStorage.setItem(NOTIFY_KEY, "1");
    const day = new Date("2026-10-20T08:00:00Z");
    expect(showDueNotification(3, day)).toBe(true);
    expect(constructed).toHaveLength(1);
    expect(showDueNotification(3, day)).toBe(false);
    expect(localStorage.getItem(NOTIFY_DAY_KEY)).toBe("2026-10-20");
    disableDueNotify();
    expect(notifyEnabled()).toBe(false);
  });
});
