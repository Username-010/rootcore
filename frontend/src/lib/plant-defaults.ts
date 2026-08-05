/** Infer sensible plant form defaults from a taxon. */

import type { Taxon } from "@/lib/types";
import { soilFromCare } from "@/lib/plant-presets";

export function suggestedEnvironment(taxon: Taxon | null | undefined): string {
  if (!taxon?.care_profile) return "indoor";
  const extra = taxon.care_profile.extra || {};
  const preferred = extra.default_environment;
  if (preferred === "indoor" || preferred === "outdoor" || preferred === "greenhouse") {
    return preferred;
  }
  const light = (taxon.care_profile.light || "").toLowerCase();
  if (light === "full_sun") return "outdoor";
  const soil = (taxon.care_profile.soil_notes || "").toLowerCase();
  if (
    (light === "partial_shade" || light === "shade") &&
    (soil.includes("garden") || soil.includes("bed"))
  ) {
    return "outdoor";
  }
  return "indoor";
}

/**
 * Suggest pot size in litres (as string for form presets), or "" for in-ground / no pot.
 */
export function suggestedPotLiters(
  taxon: Taxon | null | undefined,
  environment: string,
  growthStage = "mature",
): string {
  const extra = taxon?.care_profile?.extra || {};
  if (typeof extra.typical_pot_liters === "number") {
    return matchPotPreset(Number(extra.typical_pot_liters));
  }

  const sci = (taxon?.scientific_name || "").toLowerCase();
  const common = (taxon?.common_names || []).join(" ").toLowerCase();
  const text = sci + " " + common;
  const moisture = taxon?.care_profile?.moisture_preference;

  // Outdoor garden beds — many are in-ground
  if (environment === "outdoor") {
    if (
      /phlox|coreopsis|echinacea|rudbeckia|lavender|lavandula|salvia|aster|sedum|tulip|narcissus|dahlia|helianthus|alstroemeria/.test(
        text,
      )
    ) {
      return ""; // in ground
    }
    if (/miniature|mini rose|sempervivum|sedum|thyme|thymus/.test(text)) {
      return "1";
    }
    if (/rose|rosa|pelargonium|geranium|petunia|tagetes|basil|mint|mentha/.test(text)) {
      return "5";
    }
    if (/tomato|pepper|cucumber|fragaria|strawberry/.test(text)) {
      return "10";
    }
    // generic outdoor potted
    return "5";
  }

  if (growthStage === "seedling") return "0.5";
  if (growthStage === "juvenile") return "1";

  // Indoor by habit
  if (/cactus|succulent|sansevieria|snake|zz |zamioculcas|aloe|sempervivum|haworthia|echeveria/.test(text) || moisture === "dry") {
    return "1";
  }
  if (/orchid|phalaenopsis|saintpaulia|violet|peperomia|pilea|calathea|maranta/.test(text)) {
    return "1";
  }
  if (/monstera|ficus lyrata|bird of paradise|strelitzia|palm|dracaena marginata/.test(text)) {
    return "5";
  }
  if (/pothos|epipremnum|philodendron|spathiphyllum|peace|hoya|tradescantia|chlorophytum/.test(text)) {
    return "2";
  }
  return "2";
}

function matchPotPreset(liters: number): string {
  const presets = [0.5, 1, 2, 5, 10, 20];
  let best = presets[0];
  let bestDiff = Math.abs(liters - best);
  for (const p of presets) {
    const d = Math.abs(liters - p);
    if (d < bestDiff) {
      best = p;
      bestDiff = d;
    }
  }
  return String(best);
}

export function applyTaxonDefaults(taxon: Taxon): {
  environment: string;
  soilType: string;
  potMaterial?: string;
  potSizePreset: string; // "" = in ground / none
  nicknameHint?: string;
  tags: string[];
} {
  const environment = suggestedEnvironment(taxon);
  let soilType = soilFromCare(taxon.care_profile?.moisture_preference);
  if (environment === "outdoor" && soilType === "standard") {
    soilType = "garden_soil";
  }
  let potMaterial: string | undefined;
  if (taxon.care_profile?.drought_tolerance === "high") {
    potMaterial = "terracotta";
  } else if (environment === "outdoor") {
    potMaterial = "terracotta";
  }

  const potSizePreset = suggestedPotLiters(taxon, environment, "mature");

  const tags: string[] = [];
  if (environment === "outdoor") tags.push("outdoor");
  if (environment === "indoor") tags.push("indoor");
  if (taxon.care_profile?.toxic_to_pets) tags.push("toxic-to-pets");
  if (taxon.care_profile?.toxic_to_pets === false) tags.push("pet-safe");
  if ((taxon.care_profile?.extra?.bloom_months as number[] | undefined)?.length) {
    tags.push("flowering");
  }
  if (taxon.family) {
    // short family tag without aeae noise when useful
    const fam = taxon.family.toLowerCase();
    if (fam.includes("rosaceae")) tags.push("rose-family");
    if (fam.includes("araceae")) tags.push("aroid");
    if (fam.includes("lamiaceae")) tags.push("mint-family");
  }
  const light = taxon.care_profile?.light;
  if (light === "full_sun") tags.push("full-sun");
  if (light === "low") tags.push("low-light");

  return {
    environment,
    soilType,
    potMaterial,
    potSizePreset,
    nicknameHint: taxon.common_names[0],
    tags: [...new Set(tags)],
  };
}
