/** Shared plant / pot emoji presets. */

export const PLANT_EMOJI_PRESETS = [
  "🪴",
  "🌱",
  "🌿",
  "🌵",
  "🌳",
  "🌲",
  "🌴",
  "🍃",
  "🌸",
  "🌺",
  "🌻",
  "🌼",
  "🌹",
  "🌷",
  "🍄",
  "🍋",
  "🍅",
  "🌶️",
  "🥬",
  "🫐",
];

export const POT_EMOJI_PRESETS = [
  "🪴",
  "🪣",
  "📦",
  "🪨",
  "🪵",
  "▢",
  "●",
  "▲",
  "🏞️",
  "🌾",
  "🏡",
  "🌳",
];

export function plantEmoji(plant: {
  emoji?: string | null;
  custom_attributes?: Record<string, unknown> | null;
}): string {
  if (plant.emoji) return plant.emoji;
  const e = plant.custom_attributes?.emoji;
  if (typeof e === "string" && e.trim()) return e.trim().slice(0, 8);
  return "🪴";
}
