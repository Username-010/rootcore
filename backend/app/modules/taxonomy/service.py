"""Taxonomy services."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.taxonomy.models import CareProfile, Taxon


class TaxonomyError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def search_taxa(
    db: AsyncSession,
    *,
    q: str | None = None,
    household_id: uuid.UUID | None = None,
    limit: int = 30,
) -> list[Taxon]:
    stmt = select(Taxon).options(selectinload(Taxon.care_profile))
    if household_id is not None:
        stmt = stmt.where(
            or_(Taxon.household_id.is_(None), Taxon.household_id == household_id)
        )
    else:
        stmt = stmt.where(Taxon.household_id.is_(None))

    if q:
        from sqlalchemy import String, cast, func

        pattern = f"%{q.strip()}%"
        common = cast(func.array_to_string(Taxon.common_names, " "), String)
        stmt = stmt.where(
            or_(
                Taxon.scientific_name.ilike(pattern),
                Taxon.genus.ilike(pattern),
                common.ilike(pattern),
            )
        )

    stmt = stmt.order_by(Taxon.scientific_name).limit(min(limit, 100))
    result = await db.execute(stmt)
    return list(result.scalars())


async def get_taxon(db: AsyncSession, taxon_id: uuid.UUID) -> Taxon | None:
    result = await db.execute(
        select(Taxon)
        .options(selectinload(Taxon.care_profile))
        .where(Taxon.id == taxon_id)
    )
    return result.scalar_one_or_none()


async def create_custom_taxon(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    scientific_name: str,
    common_names: list[str] | None = None,
    rank: str = "species",
    family: str | None = None,
    genus: str | None = None,
    parent_id: uuid.UUID | None = None,
    care: dict | None = None,
) -> Taxon:
    genus_val = genus or (scientific_name.split()[0] if scientific_name.strip() else None)
    taxon = Taxon(
        household_id=household_id,
        parent_id=parent_id,
        rank=rank,
        scientific_name=scientific_name.strip(),
        common_names=common_names or [],
        family=family,
        genus=genus_val,
        external_ids={},
    )
    db.add(taxon)
    await db.flush()
    if care:
        care_data = {k: v for k, v in care.items() if v is not None and k != "extra"}
        extra = care.get("extra") if isinstance(care.get("extra"), dict) else {}
        profile = CareProfile(taxon_id=taxon.id, extra=extra or {}, **care_data)
        db.add(profile)
        await db.flush()
    await db.refresh(taxon, attribute_names=["care_profile"])
    return await get_taxon(db, taxon.id)  # type: ignore[return-value]


async def count_global_taxa(db: AsyncSession) -> int:
    from sqlalchemy import func

    result = await db.execute(
        select(func.count()).select_from(Taxon).where(Taxon.household_id.is_(None))
    )
    return int(result.scalar_one())


def _seed_path() -> Path:
    # app/modules/taxonomy/service.py → app/data/taxa_seed.json
    return Path(__file__).resolve().parent.parent.parent / "data" / "taxa_seed.json"


async def seed_global_taxa(db: AsyncSession, *, force: bool = False) -> int:
    """Load bundled plant catalog.

    Always inserts any missing global taxa (so catalog updates ship on restart).
    When force=True, also refreshes care.extra and common_names on existing rows.
    Returns number of taxa inserted (not updates).
    """
    seed_path = _seed_path()
    if not seed_path.is_file():
        raise TaxonomyError(f"Seed file missing: {seed_path}")

    if not force and await count_global_taxa(db) == 0:
        # empty DB — full seed below
        pass

    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    inserted = 0
    for item in payload:
        existing = await db.execute(
            select(Taxon)
            .options(selectinload(Taxon.care_profile))
            .where(
                Taxon.household_id.is_(None),
                Taxon.scientific_name == item["scientific_name"],
            )
        )
        taxon = existing.scalar_one_or_none()
        care = item.get("care") or {}
        extra = care.get("extra") if isinstance(care.get("extra"), dict) else {}

        if taxon is not None:
            if force:
                taxon.common_names = item.get("common_names", taxon.common_names)
                taxon.family = item.get("family") or taxon.family
                taxon.genus = item.get("genus") or taxon.genus
                if taxon.care_profile is not None:
                    cp = taxon.care_profile
                    for key in (
                        "light",
                        "moisture_preference",
                        "drought_tolerance",
                        "humidity_preference",
                        "baseline_interval_days_min",
                        "baseline_interval_days_max",
                        "water_amount_default",
                        "fertilize_notes",
                        "soil_notes",
                        "toxic_to_pets",
                    ):
                        if key in care:
                            setattr(cp, key, care.get(key))
                    # merge extras so bloom/fertilize/repot land in DB
                    cp.extra = {**(cp.extra or {}), **(extra or {})}
                elif care:
                    db.add(
                        CareProfile(
                            taxon_id=taxon.id,
                            light=care.get("light"),
                            moisture_preference=care.get("moisture_preference"),
                            drought_tolerance=care.get("drought_tolerance"),
                            humidity_preference=care.get("humidity_preference"),
                            baseline_interval_days_min=care.get("baseline_interval_days_min"),
                            baseline_interval_days_max=care.get("baseline_interval_days_max"),
                            water_amount_default=care.get("water_amount_default"),
                            fertilize_notes=care.get("fertilize_notes"),
                            soil_notes=care.get("soil_notes"),
                            toxic_to_pets=care.get("toxic_to_pets"),
                            extra=extra or {},
                        )
                    )
            continue

        taxon = Taxon(
            household_id=None,
            rank=item.get("rank", "species"),
            scientific_name=item["scientific_name"],
            common_names=item.get("common_names", []),
            family=item.get("family"),
            genus=item.get("genus") or item["scientific_name"].split()[0],
            external_ids={},
        )
        db.add(taxon)
        await db.flush()
        db.add(
            CareProfile(
                taxon_id=taxon.id,
                light=care.get("light"),
                moisture_preference=care.get("moisture_preference"),
                drought_tolerance=care.get("drought_tolerance"),
                humidity_preference=care.get("humidity_preference"),
                baseline_interval_days_min=care.get("baseline_interval_days_min"),
                baseline_interval_days_max=care.get("baseline_interval_days_max"),
                water_amount_default=care.get("water_amount_default"),
                fertilize_notes=care.get("fertilize_notes"),
                soil_notes=care.get("soil_notes"),
                toxic_to_pets=care.get("toxic_to_pets"),
                extra=extra or {},
            )
        )
        inserted += 1

    await db.flush()
    return inserted
