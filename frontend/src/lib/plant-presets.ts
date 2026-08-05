/** Dropdown presets for plant create/edit. */

export const ENVIRONMENTS = [
  { value: "indoor", label: "Indoor" },
  { value: "outdoor", label: "Outdoor / garden" },
  { value: "greenhouse", label: "Greenhouse" },
] as const;

export const POT_SIZES = [
  { value: "none", label: "In ground / no pot" },
  { value: "0.5", label: "Tiny · 0.5 L" },
  { value: "1", label: "Small · 1 L" },
  { value: "2", label: "Medium · 2 L" },
  { value: "5", label: "Large · 5 L" },
  { value: "10", label: "XL · 10 L" },
  { value: "20", label: "Garden pot · 20 L" },
  { value: "custom", label: "Custom size…" },
] as const;

export const POT_MATERIALS = [
  { value: "plastic", label: "Plastic" },
  { value: "terracotta", label: "Terracotta / clay" },
  { value: "ceramic", label: "Ceramic / glazed" },
  { value: "fabric", label: "Fabric grow bag" },
  { value: "concrete", label: "Concrete / stone" },
  { value: "wood", label: "Wood" },
  { value: "other", label: "Other" },
] as const;

export const SOIL_TYPES = [
  { value: "standard", label: "Standard potting mix" },
  { value: "free_draining", label: "Free-draining / chunky" },
  { value: "aroid_mix", label: "Aroid mix (chunky bark)" },
  { value: "cactus", label: "Cactus / succulent mix" },
  { value: "moisture_retentive", label: "Moisture-retentive" },
  { value: "garden_soil", label: "Garden soil / bed" },
  { value: "other", label: "Other" },
] as const;

export const GROWTH_STAGES = [
  { value: "seedling", label: "Seedling / cutting" },
  { value: "juvenile", label: "Young plant" },
  { value: "mature", label: "Mature" },
  { value: "flowering", label: "Flowering / fruiting" },
] as const;

/** Map care profile moisture → default soil suggestion */
export function soilFromCare(moisture: string | null | undefined): string {
  if (!moisture) return "standard";
  if (moisture === "dry") return "cactus";
  if (moisture === "moist") return "moisture_retentive";
  return "standard";
}

export function todayISODate(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
