/** Human-readable labels for stored enum/slug values. */

const SOIL: Record<string, string> = {
  standard: "Standard potting mix",
  free_draining: "Free-draining / chunky",
  aroid_mix: "Aroid mix (chunky bark)",
  cactus: "Cactus / succulent mix",
  moisture_retentive: "Moisture-retentive",
  garden_soil: "Garden soil / bed",
  other: "Other",
};

const ENV: Record<string, string> = {
  indoor: "Indoor",
  outdoor: "Outdoor / garden",
  greenhouse: "Greenhouse",
};

const POT_MATERIAL: Record<string, string> = {
  plastic: "Plastic",
  terracotta: "Terracotta / clay",
  ceramic: "Ceramic / glazed",
  fabric: "Fabric grow bag",
  concrete: "Concrete / stone",
  wood: "Wood",
  other: "Other",
};

const GROWTH: Record<string, string> = {
  seedling: "Seedling / cutting",
  juvenile: "Young plant",
  mature: "Mature",
  flowering: "Flowering / fruiting",
};

export function labelSoil(value: string | null | undefined): string {
  if (!value) return "—";
  return SOIL[value] ?? value.replaceAll("_", " ");
}

export function labelEnvironment(value: string | null | undefined): string {
  if (!value) return "—";
  return ENV[value] ?? value.replaceAll("_", " ");
}

export function labelPotMaterial(value: string | null | undefined): string {
  if (!value) return "—";
  return POT_MATERIAL[value] ?? value.replaceAll("_", " ");
}

export function labelGrowth(value: string | null | undefined): string {
  if (!value) return "—";
  return GROWTH[value] ?? value.replaceAll("_", " ");
}

export function labelSlug(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replaceAll("_", " ");
}
