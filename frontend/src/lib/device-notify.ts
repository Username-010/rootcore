export const NOTIFY_KEY = "rootcore.notify-due";
export const NOTIFY_DAY_KEY = "rootcore.notify-due-day";

export type NotifyEnableResult = "granted" | "denied" | "unsupported" | "needs-https";

export function notifySupported(): boolean {
  return typeof Notification !== "undefined";
}

export function notifyEnabled(): boolean {
  try {
    return localStorage.getItem(NOTIFY_KEY) === "1";
  } catch {
    return false;
  }
}

export async function enableDueNotify(): Promise<NotifyEnableResult> {
  if (typeof window === "undefined" || !notifySupported()) return "unsupported";
  if (!window.isSecureContext) return "needs-https";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";
  localStorage.setItem(NOTIFY_KEY, "1");
  return "granted";
}

export function disableDueNotify(): void {
  try {
    localStorage.removeItem(NOTIFY_KEY);
    localStorage.removeItem(NOTIFY_DAY_KEY);
  } catch {
    /* ignore quota */
  }
}

export function showDueNotification(count: number, now = new Date()): boolean {
  if (!notifyEnabled() || !notifySupported() || Notification.permission !== "granted") return false;
  if (count <= 0) return false;
  const day = now.toISOString().slice(0, 10);
  try {
    if (localStorage.getItem(NOTIFY_DAY_KEY) === day) return false;
    localStorage.setItem(NOTIFY_DAY_KEY, day);
  } catch {
    return false;
  }
  const body = count === 1 ? "1 plant needs water today." : `${count} plants need water today.`;
  new Notification("RootCore watering", { body, tag: "rootcore-due" });
  return true;
}
