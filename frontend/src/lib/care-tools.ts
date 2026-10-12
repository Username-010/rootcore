export const CARE_CATEGORIES = ["All", "Water & climate", "Leaves & health", "Soil & growth", "Planning & supplies"] as const;
export type CareCategory = (typeof CARE_CATEGORIES)[number];
export type CareTool = { path: string; title: string; category: Exclude<CareCategory, "All">; description: string; keywords: string };

// These are navigation aids, not diagnoses or automatic care recommendations.
export const CARE_TOOLS: CareTool[] = [
  { path: "/round", title: "Week round", category: "Water & climate", description: "Print a weekly watering walk.", keywords: "water schedule weekly" },
  { path: "/due", title: "Due can", category: "Water & climate", description: "See plants with overdue watering.", keywords: "water late thirsty" },
  { path: "/watch", title: "Garden watch", category: "Water & climate", description: "Check frost nights and rain before your round.", keywords: "weather rain forecast" },
  { path: "/mist", title: "Mist", category: "Water & climate", description: "Open the misting checklist.", keywords: "spray moisture" },
  { path: "/flush", title: "Flush", category: "Water & climate", description: "Plan a salt-leach and saucer-dump round.", keywords: "salt water drain" },
  { path: "/bottom", title: "Bottom water", category: "Water & climate", description: "Use the soak-from-below and drain checklist.", keywords: "saucer soak" },
  { path: "/air", title: "Airflow", category: "Water & climate", description: "Check gaps, drafts, and fan placement.", keywords: "ventilation breeze" },
  { path: "/humidity", title: "Humidity", category: "Water & climate", description: "Check pebble trays and room moisture.", keywords: "dry air humidifier tropical" },
  { path: "/frost", title: "Frost", category: "Water & climate", description: "Plan bring-in and cover checks for cold nights.", keywords: "winter freeze cold" },
  { path: "/dust", title: "Dust", category: "Leaves & health", description: "Plan a gentle leaf-wipe round.", keywords: "clean cloth leaves" },
  { path: "/rotate", title: "Rotate", category: "Leaves & health", description: "Check plant turns for even light.", keywords: "turn leaning window" },
  { path: "/pest", title: "Pest walk", category: "Leaves & health", description: "Inspect leaf undersides and isolation needs.", keywords: "sticky insects bug webbing" },
  { path: "/prune", title: "Prune", category: "Leaves & health", description: "Open the garden-cut checklist.", keywords: "trim cut branch" },
  { path: "/groom", title: "Groom", category: "Leaves & health", description: "Check yellow leaves and spent blooms.", keywords: "deadhead flower yellow" },
  { path: "/stake", title: "Stake", category: "Leaves & health", description: "Check supports and loose ties.", keywords: "cane moss support stem" },
  { path: "/light", title: "Light map", category: "Leaves & health", description: "Review shade, bright windows, and direct sun.", keywords: "scorch sunlight placement" },
  { path: "/repot", title: "Repot", category: "Soil & growth", description: "Plan the potting-on bench.", keywords: "pot roots container soil" },
  { path: "/feed", title: "Feed", category: "Soil & growth", description: "Open the fertiliser-mix round.", keywords: "fertilize fertilizer nutrients" },
  { path: "/cuttings", title: "Cuttings", category: "Soil & growth", description: "Prepare the propagation tray.", keywords: "propagate root cutting" },
  { path: "/split", title: "Split", category: "Soil & growth", description: "Plan clump division into separate pots.", keywords: "divide division" },
  { path: "/sow", title: "Sow", category: "Soil & growth", description: "Open the seed-start checklist.", keywords: "seed germinate" },
  { path: "/harden", title: "Harden off", category: "Soil & growth", description: "Plan seedlings moving gradually outdoors.", keywords: "seedling shade wind acclimatize" },
  { path: "/mulch", title: "Mulch", category: "Soil & growth", description: "Check soil cover and space around crowns.", keywords: "cover soil crown" },
  { path: "/topdress", title: "Topdress", category: "Soil & growth", description: "Plan fresh soil mix on the surface.", keywords: "surface compost" },
  { path: "/harvest", title: "Harvest", category: "Soil & growth", description: "Plan herb and edible snips.", keywords: "herbs edible pick" },
  { path: "/labels", title: "Labels", category: "Planning & supplies", description: "Print nickname and species stickers.", keywords: "identify name tag" },
  { path: "/away", title: "Away sheet", category: "Planning & supplies", description: "Prepare care notes for a house-sitter.", keywords: "holiday vacation sitter travel" },
  { path: "/shop", title: "Nursery run", category: "Planning & supplies", description: "Prepare the garden-centre shopping list.", keywords: "buy supplies shopping" },
];

export function searchCareTools(query: string, category: CareCategory): CareTool[] {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return CARE_TOOLS.filter((tool) => {
    const text = `${tool.title} ${tool.description} ${tool.keywords}`.toLowerCase();
    return (category === "All" || tool.category === category) && words.every((word) => text.includes(word));
  });
}
