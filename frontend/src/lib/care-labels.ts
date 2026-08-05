/** Human-readable care labels, flair icons, and glossary. */

export const LIGHT_LABELS: Record<string, { label: string; emoji: string; hint: string }> = {
  low: {
    label: "Low light",
    emoji: "🌑",
    hint: "North window or a few metres from a bright window. Avoid harsh sun.",
  },
  medium: {
    label: "Medium light",
    emoji: "🌤",
    hint: "Bright room, not always direct sun. East window is ideal for many houseplants.",
  },
  bright_indirect: {
    label: "Bright, indirect",
    emoji: "☀️",
    hint: "Near a bright window but not in full midday sun. Soft sheer curtains help.",
  },
  full_sun: {
    label: "Full sun",
    emoji: "🌞",
    hint: "6+ hours of direct sun. Typical for many outdoor / garden plants.",
  },
  partial_shade: {
    label: "Partial shade",
    emoji: "🌥",
    hint: "Morning sun or dappled light under trees / taller plants.",
  },
  shade: {
    label: "Shade",
    emoji: "🌲",
    hint: "Little direct sun — understory or deep shade spots.",
  },
};

export const MOISTURE_LABELS: Record<string, { label: string; drops: number; hint: string }> = {
  dry: {
    label: "Likes to dry out",
    drops: 1,
    hint: "Let soil dry thoroughly between waterings. Succulents, many cacti, snake plant.",
  },
  medium: {
    label: "Medium moisture",
    drops: 3,
    hint: "Water when the top few cm feel dry. Most common houseplants.",
  },
  moist: {
    label: "Prefers moist",
    drops: 4,
    hint: "Keep evenly moist — not soggy. Ferns, peace lily, many bog-edge plants.",
  },
  wet: {
    label: "Wet / aquatic",
    drops: 5,
    hint: "Consistently wet feet. Rare for pots — more for pond margins.",
  },
};

export const DROUGHT_LABELS: Record<string, string> = {
  low: "Low — don't let it dry hard",
  medium: "Medium — recovers from short dry spells",
  high: "High — tolerates dry periods well",
};

export const HUMIDITY_LABELS: Record<string, string> = {
  low: "Low humidity OK (arid / average home)",
  medium: "Average home humidity",
  high: "Prefers higher humidity (bathroom / pebble tray / humidifier)",
};

export const MONTHS_SHORT = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"] as const;
export const MONTHS_FULL = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

export function lightDisplay(code: string | null | undefined) {
  if (!code) return { label: "—", emoji: "", hint: "No light preference set." };
  return (
    LIGHT_LABELS[code] ?? {
      label: code.replaceAll("_", " "),
      emoji: "💡",
      hint: "Species light preference from the care profile.",
    }
  );
}

export function moistureDisplay(code: string | null | undefined) {
  if (!code) return { label: "—", drops: 0, hint: "No moisture preference set." };
  return (
    MOISTURE_LABELS[code] ?? {
      label: code.replaceAll("_", " "),
      drops: 3,
      hint: "How wet the plant likes its soil between waterings.",
    }
  );
}

/** 💧 emoji bar, e.g. medium → 💧💧💧○○ */
export function moistureDrops(code: string | null | undefined, max = 5): string {
  const d = moistureDisplay(code).drops;
  return "💧".repeat(d) + "○".repeat(Math.max(0, max - d));
}

export function weatherCodeEmoji(code: number | null | undefined): string {
  if (code == null) return "🌤";
  if (code === 0) return "☀️";
  if (code <= 3) return "⛅";
  if (code <= 48) return "🌫";
  if (code <= 67) return "🌧";
  if (code <= 77) return "❄️";
  if (code <= 82) return "🌦";
  if (code <= 99) return "⛈";
  return "🌤";
}

export const CARE_GLOSSARY: Array<{ term: string; body: string }> = [
  {
    term: "Light",
    body: "How much sun / brightness the species prefers. Bright-indirect is the most common indoor setting — near a window without harsh midday rays.",
  },
  {
    term: "Moisture",
    body: "How wet the soil should stay. One drop = drought-tolerant; three = water when the top dries; four+ = keep more consistently moist.",
  },
  {
    term: "Baseline water interval",
    body: "Starting guess for days between waterings. RootCore adjusts this from pot size, weather, and your feedback.",
  },
  {
    term: "Bloom months",
    body: "Typical months this species flowers outdoors (climate-dependent). Used to suggest pruning windows after bloom.",
  },
  {
    term: "Fertilize / prune / repot",
    body: "Engine tasks generated from the species profile and your last care logs. Complete them from Tasks or the calendar.",
  },
  {
    term: "Urgency",
    body: "Overdue = past due date. Due = today-ish. Soon = coming up. OK = not needed yet.",
  },
];
