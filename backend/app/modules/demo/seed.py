"""One-click demo garden + sample plants for first-time exploration."""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.layout import service as layout_service
from app.modules.layout.models import Site
from app.modules.plants import service as plant_service
from app.modules.plants.models import Plant, PlantTag, Tag
from app.modules.taxonomy.service import search_taxa

DEMO_SITE_NAME = "Demo Home"

log = logging.getLogger(__name__)

DEMO_PLANTS = [
    ("Monstera by the window", "Monstera deliciosa", "indoor"),
    ("Kitchen basil", "Ocimum basilicum", "outdoor"),
    ("Front path lavender", "Lavandula angustifolia", "outdoor"),
    ("Hot Lips pot", "Salvia microphylla", "outdoor"),
    ("Snake plant hallway", "Sansevieria trifasciata", "indoor"),
    ("Peace lily desk", "Spathiphyllum", "indoor"),
    ("Garden phlox bed", "Phlox paniculata", "outdoor"),
    ("Mini rose patio", "Rosa", "outdoor"),
]


async def seed_demo_garden(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID | None,
    auto_cover: bool = False,
) -> dict:
    """Create a demo site, garden beds (incl. L/U freehand), and sample plants.

    Photos are optional and never block the seed — Wikimedia can be slow/offline.
    """
    site = await layout_service.create_site(
        db, household_id=household_id, name=DEMO_SITE_NAME
    )
    garden = await layout_service.create_space(
        db,
        household_id=household_id,
        site_id=site.id,
        name="Front garden",
        kind="garden",
        length_m=10,
        width_m=6,
    )
    room = await layout_service.create_space(
        db,
        household_id=household_id,
        site_id=site.id,
        name="Living room",
        kind="room",
        length_m=5,
        width_m=4,
    )

    pots = []
    pots.append(
        await layout_service.create_container(
            db,
            household_id=household_id,
            space_id=garden.id,
            name="Circle pot",
            kind="circle",
            x=40,
            y=40,
            width=64,
            height=64,
        )
    )
    pots.append(
        await layout_service.create_container(
            db,
            household_id=household_id,
            space_id=garden.id,
            name="Square bed",
            kind="square",
            x=140,
            y=50,
            width=80,
            height=80,
        )
    )
    # L-shaped freehand (canvas ~400×240 for 10×6 m)
    l_path = [
        [250, 40],
        [340, 40],
        [340, 100],
        [300, 100],
        [300, 180],
        [250, 180],
        [250, 40],
    ]
    pots.append(
        await layout_service.create_container(
            db,
            household_id=household_id,
            space_id=garden.id,
            name="L-shaped bed",
            kind="polygon",
            path_json=l_path,
        )
    )
    u_path = [
        [50, 200],
        [50, 320],
        [200, 320],
        [200, 200],
        [170, 200],
        [170, 280],
        [80, 280],
        [80, 200],
        [50, 200],
    ]
    pots.append(
        await layout_service.create_container(
            db,
            household_id=household_id,
            space_id=garden.id,
            name="U-shaped bed",
            kind="polygon",
            path_json=u_path,
        )
    )
    indoor_pot = await layout_service.create_container(
        db,
        household_id=household_id,
        space_id=room.id,
        name="Shelf pot",
        kind="circle",
        x=60,
        y=60,
        width=56,
        height=56,
    )

    created: list[dict[str, str]] = []
    today = date.today()
    outdoor_i = 0
    for i, (nick, sci, env) in enumerate(DEMO_PLANTS):
        taxon = None
        try:
            matches = await search_taxa(db, q=sci, household_id=household_id, limit=8)
            sci_l = sci.lower()
            for t in matches:
                if t.scientific_name.lower().startswith(sci_l.split()[0]):
                    taxon = t
                    break
            if taxon is None and matches:
                taxon = matches[0]
        except Exception as exc:  # noqa: BLE001
            log.warning("demo taxon search failed for %s: %s", sci, exc)

        plant = await plant_service.create_plant(
            db,
            household_id=household_id,
            created_by_user_id=user_id,
            data={
                "nickname": nick,
                "taxon_id": taxon.id if taxon else None,
                "environment": env,
                "environment_auto": False,
                "acquired_at": today - timedelta(days=14 + i * 3),
                "notes": "Demo plant — feel free to edit or archive.",
            },
            tag_names=["demo"],
        )
        plant_id = plant.id
        nickname = plant.nickname

        if auto_cover and plant.taxon is not None:
            try:
                await plant_service.try_auto_cover_from_wikimedia(
                    db, plant=plant, user_id=user_id
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("demo auto-cover skipped for %s: %s", nickname, exc)

        if env == "indoor":
            await layout_service.upsert_placement(
                db,
                household_id=household_id,
                plant_id=plant_id,
                space_id=room.id,
                container_id=indoor_pot.id if outdoor_i == 0 and i == 0 else None,
                x=60.0 + (i % 3) * 50,
                y=60.0 + (i % 2) * 40,
            )
        else:
            pot = pots[outdoor_i % len(pots)]
            await layout_service.upsert_placement(
                db,
                household_id=household_id,
                plant_id=plant_id,
                space_id=garden.id,
                container_id=pot.id if outdoor_i < 4 else None,
                x=float(pot.x or 0) + 10,
                y=float(pot.y or 0) + 10,
            )
            outdoor_i += 1
        created.append({"id": str(plant_id), "nickname": nickname})

    await db.flush()
    return {
        "site_id": str(site.id),
        "garden_id": str(garden.id),
        "plants": created,
        "message": (
            f"Demo ready: {len(created)} plants on “{DEMO_SITE_NAME}” "
            f"(Front garden with L & U beds + Living room). Open Map to explore."
        ),
    }


async def clear_demo_garden(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
) -> dict:
    """Remove demo site(s) and plants tagged 'demo' for this household."""
    plants_removed = 0
    sites_removed = 0

    # Plants with the demo tag
    tag_q = await db.execute(
        select(Tag.id).where(
            Tag.household_id == household_id,
            func.lower(Tag.name) == "demo",
        )
    )
    tag_ids = list(tag_q.scalars().all())
    plant_ids: set[uuid.UUID] = set()
    if tag_ids:
        links = await db.execute(
            select(PlantTag.plant_id).where(PlantTag.tag_id.in_(tag_ids))
        )
        plant_ids.update(links.scalars().all())

    # Also catch any plant still on a Demo Home site
    sites_q = await db.execute(
        select(Site)
        .options(selectinload(Site.spaces))
        .where(
            Site.household_id == household_id,
            Site.name == DEMO_SITE_NAME,
        )
    )
    demo_sites = list(sites_q.scalars().unique())

    for plant_id in plant_ids:
        plant = await plant_service.get_plant(
            db, household_id=household_id, plant_id=plant_id
        )
        if plant is None:
            continue
        await plant_service.delete_plant(db, plant)
        plants_removed += 1

    for site in demo_sites:
        await layout_service.delete_site(db, household_id, site.id)
        sites_removed += 1

    await db.flush()
    if plants_removed == 0 and sites_removed == 0:
        message = "No demo garden found — nothing to remove."
    else:
        message = (
            f"Demo removed: {plants_removed} plant(s), {sites_removed} map site(s). "
            "Your other plants and maps are unchanged."
        )
    return {
        "plants_removed": plants_removed,
        "sites_removed": sites_removed,
        "message": message,
    }
