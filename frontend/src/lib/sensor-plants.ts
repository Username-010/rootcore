import { apiRequest } from "./api";

type PlantOption = { id: string; nickname: string };
/** A bounded selector fetch; never triggers the plant browser's cover backfill. */
export async function loadSensorPlants(householdId: string): Promise<PlantOption[]> {
  const all: PlantOption[] = [];
  for (let offset = 0; offset < 2000; offset += 200) {
    const page = await apiRequest<{items: PlantOption[]; total:number}>(`/api/v1/households/${householdId}/plants?limit=200&offset=${offset}&backfill_covers=false`);
    all.push(...page.items);
    if (offset + 200 >= page.total) return all;
  }
  throw new Error("Plant selector supports up to 2,000 plants per household.");
}
