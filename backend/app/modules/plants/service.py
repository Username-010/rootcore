"""Plant specimen services."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.media import delete_media_keys, save_plant_image, sign_media_url
from app.modules.plants.models import Plant, PlantPhoto, PlantTag, Tag
from app.modules.taxonomy.models import Taxon
from app.modules.taxonomy.service import get_taxon


class PlantError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _plant_load_options():
    return (
        selectinload(Plant.taxon).selectinload(Taxon.care_profile),
        selectinload(Plant.tag_links).selectinload(PlantTag.tag),
        selectinload(Plant.photos),
    )


async def get_plant(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID,
) -> Plant | None:
    result = await db.execute(
        select(Plant)
        .options(*_plant_load_options())
        .where(Plant.id == plant_id, Plant.household_id == household_id)
    )
    return result.scalar_one_or_none()


async def list_plants(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    q: str | None = None,
    status: str | None = None,
    environment: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Plant], int]:
    filters = [Plant.household_id == household_id]
    if status:
        filters.append(Plant.status == status)
    else:
        # Default: hide archived/deceased unless filtered
        filters.append(Plant.status.in_(["active", "dormant"]))
    if environment:
        filters.append(Plant.environment == environment)
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Plant.nickname.ilike(pattern),
                Plant.notes.ilike(pattern),
            )
        )

    base = select(Plant).where(*filters)
    if tag:
        base = (
            base.join(PlantTag, PlantTag.plant_id == Plant.id)
            .join(Tag, Tag.id == PlantTag.tag_id)
            .where(func.lower(Tag.name) == tag.strip().lower())
        )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        base.options(*_plant_load_options())
        .order_by(Plant.nickname)
        .limit(min(max(limit, 1), 200))
        .offset(max(offset, 0))
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique()), total


async def _upsert_tags(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant: Plant,
    tag_names: list[str],
) -> None:
    # Delete existing links without lazy-loading the collection
    await db.execute(PlantTag.__table__.delete().where(PlantTag.plant_id == plant.id))
    await db.flush()

    for raw in tag_names:
        name = raw.strip()
        if not name:
            continue
        result = await db.execute(
            select(Tag).where(
                Tag.household_id == household_id,
                func.lower(Tag.name) == name.lower(),
            )
        )
        tag = result.scalar_one_or_none()
        if tag is None:
            tag = Tag(household_id=household_id, name=name)
            db.add(tag)
            await db.flush()
        db.add(PlantTag(plant_id=plant.id, tag_id=tag.id))
    await db.flush()


def _auto_tags_for(taxon: Taxon | None, environment: str) -> list[str]:
    tags: list[str] = []
    if environment:
        tags.append(environment)
    if taxon is None:
        return tags
    care = taxon.care_profile
    if care is not None:
        if care.toxic_to_pets is True:
            tags.append("toxic-to-pets")
        elif care.toxic_to_pets is False:
            tags.append("pet-safe")
        if care.light == "full_sun":
            tags.append("full-sun")
        elif care.light == "low":
            tags.append("low-light")
        if care.moisture_preference == "dry":
            tags.append("drought-tolerant")
        extra = care.extra or {}
        if extra.get("bloom_months"):
            tags.append("flowering")
    if taxon.family:
        fam = taxon.family.lower()
        if "araceae" in fam:
            tags.append("aroid")
        if "rosaceae" in fam:
            tags.append("rose-family")
        if "lamiaceae" in fam:
            tags.append("herb")
    return tags[:8]


def suggest_environment(taxon: Taxon | None) -> str:
    """Infer indoor/outdoor/greenhouse from taxon care extras + light."""
    if taxon is None or taxon.care_profile is None:
        return "indoor"
    care = taxon.care_profile
    extra = care.extra or {}
    preferred = extra.get("default_environment")
    if preferred in {"indoor", "outdoor", "greenhouse"}:
        return str(preferred)
    light = (care.light or "").lower()
    if light == "full_sun":
        return "outdoor"
    if light in {"partial_shade", "shade"} and (
        "garden" in (care.soil_notes or "").lower()
        or "bed" in (care.soil_notes or "").lower()
    ):
        return "outdoor"
    return "indoor"


def suggest_soil(taxon: Taxon | None) -> str | None:
    if taxon is None or taxon.care_profile is None:
        return None
    moisture = taxon.care_profile.moisture_preference
    if moisture == "dry":
        return "cactus"
    if moisture == "moist":
        return "moisture_retentive"
    env = suggest_environment(taxon)
    if env == "outdoor":
        return "garden_soil"
    return "standard"


async def create_plant(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
    data: dict,
    tag_names: list[str] | None = None,
) -> Plant:
    taxon_id = data.get("taxon_id")
    taxon: Taxon | None = None
    if taxon_id:
        taxon = await get_taxon(db, taxon_id)
        if taxon is None or (
            taxon.household_id is not None and taxon.household_id != household_id
        ):
            raise PlantError("Taxon not found", status_code=404)

    # Smart defaults from species when not explicitly overridden
    env = data.get("environment")
    if not env or data.get("environment_auto"):
        env = suggest_environment(taxon)

    soil = data.get("soil_type")
    if not soil and taxon:
        soil = suggest_soil(taxon)

    pot_material = data.get("pot_material")
    if not pot_material and taxon and taxon.care_profile:
        if (taxon.care_profile.drought_tolerance or "") == "high":
            pot_material = "terracotta"
        elif env == "outdoor":
            pot_material = "terracotta"

    plant = Plant(
        household_id=household_id,
        created_by_user_id=created_by_user_id,
        nickname=data["nickname"].strip(),
        taxon_id=taxon_id,
        status=data.get("status") or "active",
        environment=env or "indoor",
        acquired_at=data.get("acquired_at"),
        pot_size_liters=data.get("pot_size_liters"),
        pot_material=pot_material,
        soil_type=soil,
        growth_stage=data.get("growth_stage"),
        estimated_value=data.get("estimated_value"),
        notes=data.get("notes"),
        custom_attributes=data.get("custom_attributes") or {},
    )
    db.add(plant)
    await db.flush()

    # Auto tags from species only when none were provided (imports / catalog quick-add)
    provided = list(tag_names or [])
    if provided:
        await _upsert_tags(db, household_id=household_id, plant=plant, tag_names=provided)
    elif taxon is not None:
        await _upsert_tags(
            db,
            household_id=household_id,
            plant=plant,
            tag_names=_auto_tags_for(taxon, env or "indoor"),
        )
    plant = await get_plant(db, household_id=household_id, plant_id=plant.id)  # type: ignore[assignment]
    # Initialize watering recommendation
    from app.modules.watering import service as watering_service

    await watering_service.recompute_plant(db, plant)

    # Optional fertilize history on create
    last_fert = data.get("last_fertilized_at")
    if last_fert is not None:
        from datetime import UTC as _UTC
        from datetime import datetime

        from app.modules.timeline import service as timeline_service

        occurred = datetime.combine(last_fert, datetime.min.time()).replace(tzinfo=_UTC)
        await timeline_service.create_event(
            db,
            household_id=household_id,
            event_type="fertilized",
            plant_id=plant.id,
            actor_user_id=created_by_user_id,
            occurred_at=occurred,
            payload={"source": "plant_create"},
        )

    return await get_plant(db, household_id=household_id, plant_id=plant.id)  # type: ignore[return-value]


async def copy_plant(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    plant_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
    nickname: str | None = None,
) -> Plant:
    """Duplicate a plant (species, pot, tags, notes) without photos or care history."""
    source = await get_plant(db, household_id=household_id, plant_id=plant_id)
    if source is None:
        raise PlantError("Plant not found", status_code=404)
    if source.status not in {"active", "dormant"}:
        raise PlantError("Can only copy active or dormant plants", status_code=400)

    base_name = (nickname or source.nickname).strip()
    # Avoid exact duplicate nicknames looking identical
    copy_name = base_name if base_name.lower().endswith("(copy)") else f"{base_name} (copy)"

    tag_names = [t.tag.name for t in (source.tag_links or []) if t.tag]
    data = {
        "nickname": copy_name,
        "taxon_id": source.taxon_id,
        "status": "active",
        "environment": source.environment,
        "environment_auto": False,
        "pot_size_liters": source.pot_size_liters,
        "pot_material": source.pot_material,
        "soil_type": source.soil_type,
        "growth_stage": source.growth_stage,
        "estimated_value": source.estimated_value,
        "notes": source.notes,
        "custom_attributes": dict(source.custom_attributes or {}),
        "acquired_at": None,
    }
    return await create_plant(
        db,
        household_id=household_id,
        created_by_user_id=created_by_user_id,
        data=data,
        tag_names=tag_names,
    )


async def try_auto_cover_from_wikimedia(
    db: AsyncSession,
    *,
    plant: Plant,
    user_id: uuid.UUID | None,
) -> bool:
    """Download a free Commons/Wikipedia image as cover. Returns True if set."""
    if not plant.taxon or not plant.taxon.scientific_name:
        return False
    if plant.cover_photo_id is not None:
        return True
    try:
        from app.modules.identify.wikimedia import download_image, fetch_species_image_url

        commons = list(plant.taxon.common_names or [])
        url = await fetch_species_image_url(plant.taxon.scientific_name, commons)
        if not url:
            return False
        data, content_type = await download_image(url)
        await add_photo(
            db,
            plant=plant,
            household_id=plant.household_id,
            user_id=user_id,
            data=data,
            content_type=content_type,
            caption=f"Auto photo · {plant.taxon.scientific_name}",
            set_cover=True,
        )
        return True
    except Exception:
        return False


async def set_cover_from_url(
    db: AsyncSession,
    *,
    plant: Plant,
    user_id: uuid.UUID | None,
    image_url: str,
    caption: str | None = None,
) -> Plant:
    """Download an image URL and set it as the plant cover photo."""
    from app.modules.identify.wikimedia import download_image

    url = (image_url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise PlantError("Invalid image URL", status_code=400)
    # Only allow free Wikimedia / Wikipedia hosts (avoid open proxy abuse)
    allowed = (
        "upload.wikimedia.org",
        "commons.wikimedia.org",
        "wikipedia.org",
        "wikimedia.org",
    )
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    if not any(host == a or host.endswith("." + a) for a in allowed):
        raise PlantError(
            "Only Wikimedia / Wikipedia image URLs can be imported this way",
            status_code=400,
        )
    data, content_type = await download_image(url)
    await add_photo(
        db,
        plant=plant,
        household_id=plant.household_id,
        user_id=user_id,
        data=data,
        content_type=content_type,
        caption=caption or "From Wikimedia",
        set_cover=True,
    )
    return await get_plant(db, household_id=plant.household_id, plant_id=plant.id)  # type: ignore[return-value]


async def fill_missing_covers(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    limit: int = 8,
) -> int:
    """Fetch Wikimedia covers for active plants that have a species but no photo."""
    result = await db.execute(
        select(Plant)
        .options(*_plant_load_options())
        .where(
            Plant.household_id == household_id,
            Plant.status.in_(["active", "dormant"]),
            Plant.cover_photo_id.is_(None),
            Plant.taxon_id.is_not(None),
        )
        .order_by(Plant.created_at.desc())
        .limit(max(1, min(limit, 20)))
    )
    filled = 0
    for plant in result.scalars().unique():
        ok = await try_auto_cover_from_wikimedia(db, plant=plant, user_id=user_id)
        if ok:
            filled += 1
    return filled


async def import_plants_bulk(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
    text: str,
    auto_cover: bool = True,
    default_environment: str | None = None,
) -> dict:
    """Parse multi-line plant list and create specimens.

    Supported formats (mixed ok):
      Nickname
      Scientific name

      Nickname (2)
      Scientific name

      nickname,scientific_name,environment,notes
      nickname;scientific_name
    """
    from app.modules.taxonomy.service import search_taxa

    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    # Drop pure comment lines
    lines = [ln for ln in lines if ln and not ln.startswith("#")]

    created: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        nickname = None
        scientific = None
        environment = default_environment
        notes = None
        qty = 1

        if "," in line or ";" in line:
            sep = "," if line.count(",") >= line.count(";") else ";"
            parts = [p.strip() for p in line.split(sep)]
            nickname = parts[0] if parts else None
            scientific = parts[1] if len(parts) > 1 else None
            if len(parts) > 2 and parts[2] in {"indoor", "outdoor", "greenhouse"}:
                environment = parts[2]
            if len(parts) > 3:
                notes = parts[3]
            i += 1
        else:
            # HortusFox-ish: nickname line, optional (n), then scientific on next line
            nickname = line
            import re

            m = re.match(r"^(.*?)\s*\((\d+)\)\s*$", line)
            if m:
                nickname = m.group(1).strip()
                qty = max(1, min(int(m.group(2)), 20))
            # next non-empty as scientific if it looks like Latin / has space or quotes
            if i + 1 < len(lines):
                nxt = lines[i + 1]
                if "," not in nxt and ";" not in nxt:
                    scientific = nxt
                    i += 2
                else:
                    i += 1
            else:
                i += 1

        if not nickname:
            continue
        if not scientific:
            # try nickname as search
            scientific = nickname

        try:
            matches = await search_taxa(db, q=scientific, household_id=household_id, limit=8)
            taxon = None
            sci_l = scientific.lower().strip()
            for t in matches:
                if t.scientific_name.lower() == sci_l:
                    taxon = t
                    break
            if taxon is None:
                for t in matches:
                    commons = [c.lower() for c in (t.common_names or [])]
                    if sci_l in commons or any(sci_l in c for c in commons):
                        taxon = t
                        break
            if taxon is None and matches:
                taxon = matches[0]

            for n in range(qty):
                nick = nickname if qty == 1 else f"{nickname} ({n + 1})"
                plant_data: dict = {
                    "nickname": nick,
                    "taxon_id": taxon.id if taxon else None,
                    "notes": notes,
                    "environment_auto": True,
                }
                if environment:
                    plant_data["environment"] = environment
                    plant_data["environment_auto"] = False
                plant = await create_plant(
                    db,
                    household_id=household_id,
                    created_by_user_id=created_by_user_id,
                    data=plant_data,
                )
                if auto_cover and plant.taxon and not plant.cover_photo_id:
                    await try_auto_cover_from_wikimedia(
                        db, plant=plant, user_id=created_by_user_id
                    )
                    plant = await get_plant(
                        db, household_id=household_id, plant_id=plant.id
                    )
                created.append(
                    {
                        "id": str(plant.id) if plant else None,
                        "nickname": nick,
                        "taxon": taxon.scientific_name if taxon else None,
                        "environment": plant.environment if plant else None,
                    }
                )
        except Exception as exc:
            errors.append({"line": line, "error": str(exc)})
            if not scientific:
                skipped.append({"line": line, "reason": "no species match"})

    return {
        "created_count": len(created),
        "created": created,
        "errors": errors,
        "skipped": skipped,
    }


async def ensure_taxon_preview_url(db: AsyncSession, taxon: Taxon) -> str | None:
    """Return cached preview URL or fetch once from Wikimedia and store on care.extra."""
    if not taxon.scientific_name:
        return None
    care = taxon.care_profile
    extra = dict(care.extra or {}) if care else {}
    if extra.get("preview_url"):
        return str(extra["preview_url"])
    try:
        from app.modules.identify.wikimedia import fetch_species_image_url

        url = await fetch_species_image_url(taxon.scientific_name)
        if url and care is not None:
            extra["preview_url"] = url
            care.extra = extra
            await db.flush()
        return url
    except Exception:
        return None



async def update_plant(
    db: AsyncSession,
    plant: Plant,
    *,
    household_id: uuid.UUID,
    data: dict,
    tag_names: list[str] | None = None,
) -> Plant:
    if "taxon_id" in data and data["taxon_id"] is not None:
        taxon = await get_taxon(db, data["taxon_id"])
        if taxon is None or (
            taxon.household_id is not None and taxon.household_id != household_id
        ):
            raise PlantError("Taxon not found", status_code=404)

    for key, value in data.items():
        if key == "tag_names":
            continue
        if key == "nickname" and value is not None:
            setattr(plant, key, value.strip())
        else:
            setattr(plant, key, value)

    if tag_names is not None:
        # reload relationships
        plant = await get_plant(db, household_id=household_id, plant_id=plant.id)  # type: ignore[assignment]
        await _upsert_tags(db, household_id=household_id, plant=plant, tag_names=tag_names)

    await db.flush()
    plant = await get_plant(db, household_id=household_id, plant_id=plant.id)  # type: ignore[assignment]
    from app.modules.watering import service as watering_service

    await watering_service.recompute_plant(db, plant)
    return await get_plant(db, household_id=household_id, plant_id=plant.id)  # type: ignore[return-value]


async def archive_plant(db: AsyncSession, plant: Plant) -> Plant:
    plant.status = "archived"
    plant.archived_at = datetime.now(UTC)
    # Drop open engine care tasks so they leave the calendar
    from sqlalchemy import select

    from app.modules.tasks.models import Task, TaskPlant

    result = await db.execute(
        select(Task)
        .join(TaskPlant, TaskPlant.task_id == Task.id)
        .where(
            TaskPlant.plant_id == plant.id,
            Task.status == "open",
            Task.source == "engine",
        )
    )
    for task in result.scalars():
        task.status = "cancelled"
    # Remove layout placement so it leaves maps
    from app.modules.layout.models import Placement

    pl = await db.execute(select(Placement).where(Placement.plant_id == plant.id))
    placement = pl.scalar_one_or_none()
    if placement:
        await db.delete(placement)
    await db.flush()
    return plant


async def restore_plant(db: AsyncSession, plant: Plant) -> Plant:
    if plant.status != "archived":
        raise PlantError("Plant is not archived", status_code=400)
    household_id = plant.household_id
    plant_id = plant.id
    plant.status = "active"
    plant.archived_at = None
    await db.flush()
    restored = await get_plant(db, household_id=household_id, plant_id=plant_id)
    if restored is None:
        raise PlantError("Plant not found after restore", status_code=404)
    from app.modules.watering import service as watering_service

    await watering_service.recompute_plant(db, restored)
    final = await get_plant(db, household_id=household_id, plant_id=plant_id)
    if final is None:
        raise PlantError("Plant not found after restore", status_code=404)
    return final


async def decease_plant(
    db: AsyncSession,
    plant: Plant,
    *,
    deceased_at: date | None = None,
    reason: str | None = None,
) -> Plant:
    plant.status = "deceased"
    plant.deceased_at = deceased_at or date.today()
    plant.deceased_reason = reason
    await db.flush()
    return plant


async def delete_plant(db: AsyncSession, plant: Plant) -> None:
    for photo in list(plant.photos):
        delete_media_keys(photo.storage_key, photo.thumb_key, photo.display_key)
    await db.delete(plant)
    await db.flush()


async def add_photo(
    db: AsyncSession,
    *,
    plant: Plant,
    household_id: uuid.UUID,
    user_id: uuid.UUID | None,
    data: bytes,
    content_type: str,
    caption: str | None = None,
    set_cover: bool = False,
) -> PlantPhoto:
    saved = save_plant_image(
        household_id=household_id,
        plant_id=plant.id,
        data=data,
        content_type=content_type,
    )
    photo = PlantPhoto(
        id=saved["id"],
        household_id=household_id,
        plant_id=plant.id,
        storage_key=saved["storage_key"],
        thumb_key=saved["thumb_key"],
        display_key=saved["display_key"],
        mime_type=saved["mime_type"],
        byte_size=saved["byte_size"],
        width=saved["width"],
        height=saved["height"],
        caption=caption,
        uploaded_by_user_id=user_id,
    )
    db.add(photo)
    await db.flush()
    if set_cover or plant.cover_photo_id is None:
        plant.cover_photo_id = photo.id
        await db.flush()
    return photo


async def get_photo(
    db: AsyncSession,
    *,
    household_id: uuid.UUID,
    photo_id: uuid.UUID,
) -> PlantPhoto | None:
    result = await db.execute(
        select(PlantPhoto).where(
            PlantPhoto.id == photo_id,
            PlantPhoto.household_id == household_id,
        )
    )
    return result.scalar_one_or_none()


async def set_cover_photo(db: AsyncSession, plant: Plant, photo: PlantPhoto) -> Plant:
    if photo.plant_id != plant.id:
        raise PlantError("Photo does not belong to this plant", status_code=400)
    plant.cover_photo_id = photo.id
    await db.flush()
    return plant


async def delete_photo(db: AsyncSession, plant: Plant, photo: PlantPhoto) -> None:
    if photo.plant_id != plant.id:
        raise PlantError("Photo does not belong to this plant", status_code=400)
    delete_media_keys(photo.storage_key, photo.thumb_key, photo.display_key)
    was_cover = plant.cover_photo_id == photo.id
    await db.delete(photo)
    await db.flush()
    if was_cover:
        result = await db.execute(
            select(PlantPhoto)
            .where(PlantPhoto.plant_id == plant.id)
            .order_by(PlantPhoto.created_at.desc())
            .limit(1)
        )
        next_photo = result.scalar_one_or_none()
        plant.cover_photo_id = next_photo.id if next_photo else None
        await db.flush()


async def list_household_tags(db: AsyncSession, household_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.household_id == household_id).order_by(Tag.name)
    )
    return list(result.scalars())


def photo_to_public(photo: PlantPhoto, *, cover_id: uuid.UUID | None) -> dict:
    return {
        "id": photo.id,
        "plant_id": photo.plant_id,
        "caption": photo.caption,
        "taken_at": photo.taken_at,
        "mime_type": photo.mime_type,
        "byte_size": photo.byte_size,
        "width": photo.width,
        "height": photo.height,
        "thumb_url": sign_media_url(photo.thumb_key) if photo.thumb_key else None,
        "display_url": sign_media_url(photo.display_key) if photo.display_key else None,
        "original_url": sign_media_url(photo.storage_key),
        "created_at": photo.created_at,
        "is_cover": cover_id == photo.id,
    }


def plant_to_list_item(plant: Plant) -> dict:
    cover = None
    if plant.cover_photo_id:
        for p in plant.photos:
            if p.id == plant.cover_photo_id:
                cover = photo_to_public(p, cover_id=plant.cover_photo_id)
                break
    tags = [
        {"id": link.tag.id, "name": link.tag.name, "color": link.tag.color}
        for link in plant.tag_links
        if link.tag
    ]
    taxon = None
    if plant.taxon:
        taxon = plant.taxon
    attrs = dict(plant.custom_attributes or {})
    emoji = attrs.get("emoji")
    if isinstance(emoji, str):
        emoji = emoji.strip()[:8] or None
    else:
        emoji = None
    return {
        "id": plant.id,
        "nickname": plant.nickname,
        "status": plant.status,
        "environment": plant.environment,
        "taxon": taxon,
        "cover_photo": cover,
        "tags": tags,
        "pot_size_liters": plant.pot_size_liters,
        "acquired_at": plant.acquired_at,
        "created_at": plant.created_at,
        "emoji": emoji,
        "custom_attributes": attrs,
    }


def plant_to_detail(plant: Plant) -> dict:
    base = plant_to_list_item(plant)
    base.update(
        {
            "pot_material": plant.pot_material,
            "soil_type": plant.soil_type,
            "growth_stage": plant.growth_stage,
            "estimated_value": plant.estimated_value,
            "notes": plant.notes,
            "custom_attributes": plant.custom_attributes or {},
            "deceased_at": plant.deceased_at,
            "deceased_reason": plant.deceased_reason,
            "archived_at": plant.archived_at,
            "created_by_user_id": plant.created_by_user_id,
            "updated_at": plant.updated_at,
        }
    )
    return base
