"""Plant, taxon, photo, and tag routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession, HouseholdContext, require_household_role
from app.core.media import MediaError, absolute_media_path, decode_media_token
from app.modules.plants import service as plant_service
from app.modules.plants.schemas import (
    DeceaseRequest,
    PaginatedPlants,
    PhotoPublic,
    PhotoUpdate,
    PlantCreate,
    PlantDetail,
    PlantListItem,
    PlantUpdate,
    TagPublic,
)
from app.modules.plants.service import PlantError
from app.modules.taxonomy import service as taxon_service
from app.modules.taxonomy.schemas import CareProfilePublic, TaxonCreate, TaxonPublic
from app.modules.taxonomy.service import TaxonomyError

router = APIRouter(prefix="/api/v1", tags=["plants"])


def _plant_err(exc: PlantError | TaxonomyError | MediaError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _taxon_public(taxon) -> TaxonPublic:
    care = None
    if taxon.care_profile:
        care = CareProfilePublic.model_validate(taxon.care_profile)
    return TaxonPublic(
        id=taxon.id,
        household_id=taxon.household_id,
        parent_id=taxon.parent_id,
        rank=taxon.rank,
        scientific_name=taxon.scientific_name,
        authors=taxon.authors,
        common_names=list(taxon.common_names or []),
        family=taxon.family,
        genus=taxon.genus,
        care_profile=care,
        created_at=taxon.created_at,
    )


def _list_item(plant) -> PlantListItem:
    data = plant_service.plant_to_list_item(plant)
    if data["taxon"] is not None:
        data["taxon"] = _taxon_public(data["taxon"])
    if data["cover_photo"] is not None:
        data["cover_photo"] = PhotoPublic(**data["cover_photo"])
    data["tags"] = [TagPublic(**t) for t in data["tags"]]
    return PlantListItem(**data)


def _detail(plant) -> PlantDetail:
    data = plant_service.plant_to_detail(plant)
    if data["taxon"] is not None:
        data["taxon"] = _taxon_public(data["taxon"])
    if data["cover_photo"] is not None:
        data["cover_photo"] = PhotoPublic(**data["cover_photo"])
    data["tags"] = [TagPublic(**t) for t in data["tags"]]
    return PlantDetail(**data)


# --- Taxa ---


@router.get("/taxa", response_model=list[TaxonPublic])
async def search_taxa(
    user: CurrentUser,
    db: DbSession,
    q: str | None = None,
    household_id: uuid.UUID | None = None,
    limit: int = Query(30, ge=1, le=100),
) -> list[TaxonPublic]:
    # If household provided, verify membership for custom taxa visibility
    if household_id is not None:
        from app.modules.households.service import get_membership

        membership = await get_membership(db, household_id=household_id, user_id=user.id)
        if membership is None:
            raise HTTPException(status_code=404, detail="Household not found")
    taxa = await taxon_service.search_taxa(
        db, q=q, household_id=household_id, limit=limit
    )
    return [_taxon_public(t) for t in taxa]


@router.get("/taxa/catalog")
async def catalog_taxa(
    user: CurrentUser,
    db: DbSession,
    q: str | None = None,
    household_id: uuid.UUID | None = None,
    limit: int = Query(24, ge=1, le=100),
    with_images: bool = Query(True),
) -> list[dict]:
    """Browse catalog with optional Wikimedia preview images (cached on care.extra)."""
    if household_id is not None:
        from app.modules.households.service import get_membership

        membership = await get_membership(db, household_id=household_id, user_id=user.id)
        if membership is None:
            raise HTTPException(status_code=404, detail="Household not found")
    taxa = await taxon_service.search_taxa(
        db, q=q, household_id=household_id, limit=limit
    )
    out: list[dict] = []
    # Limit network fan-out for image previews
    image_budget = 16 if with_images else 0
    for t in taxa:
        pub = _taxon_public(t)
        preview = None
        suggested_env = plant_service.suggest_environment(t)
        if image_budget > 0:
            preview = await plant_service.ensure_taxon_preview_url(db, t)
            if preview:
                image_budget -= 1
        out.append(
            {
                **pub.model_dump(mode="json"),
                "preview_url": preview,
                "suggested_environment": suggested_env,
            }
        )
    await db.commit()
    return out


@router.get("/taxa/{taxon_id}/preview")
async def taxon_preview(
    taxon_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    taxon = await taxon_service.get_taxon(db, taxon_id)
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")
    url = await plant_service.ensure_taxon_preview_url(db, taxon)
    await db.commit()
    return {"taxon_id": str(taxon_id), "preview_url": url}


@router.get("/taxa/{taxon_id}", response_model=TaxonPublic)
async def get_taxon(taxon_id: uuid.UUID, user: CurrentUser, db: DbSession) -> TaxonPublic:
    taxon = await taxon_service.get_taxon(db, taxon_id)
    if taxon is None:
        raise HTTPException(status_code=404, detail="Taxon not found")
    if taxon.household_id is not None:
        from app.modules.households.service import get_membership

        membership = await get_membership(
            db, household_id=taxon.household_id, user_id=user.id
        )
        if membership is None:
            raise HTTPException(status_code=404, detail="Taxon not found")
    return _taxon_public(taxon)


@router.post(
    "/households/{household_id}/taxa",
    response_model=TaxonPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_taxon(
    body: TaxonCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> TaxonPublic:
    care = body.care_profile.model_dump() if body.care_profile else None
    taxon = await taxon_service.create_custom_taxon(
        db,
        household_id=ctx.household.id,
        scientific_name=body.scientific_name,
        common_names=body.common_names,
        rank=body.rank,
        family=body.family,
        genus=body.genus,
        parent_id=body.parent_id,
        care=care,
    )
    await db.commit()
    return _taxon_public(taxon)


# --- Plants ---


@router.get("/households/{household_id}/plants", response_model=PaginatedPlants)
async def list_plants(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    q: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    environment: str | None = None,
    tag: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PaginatedPlants:
    # First page: backfill a few missing covers so the grid isn't empty
    if offset == 0 and not q:
        try:
            settings = ctx.household.settings or {}
            if settings.get("auto_cover_images", True):
                await plant_service.fill_missing_covers(
                    db,
                    household_id=ctx.household.id,
                    user_id=ctx.user.id,
                    limit=5,
                )
                await db.commit()
        except Exception:
            await db.rollback()

    plants, total = await plant_service.list_plants(
        db,
        household_id=ctx.household.id,
        q=q,
        status=status_filter,
        environment=environment,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return PaginatedPlants(
        items=[_list_item(p) for p in plants],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/households/{household_id}/plants",
    response_model=PlantDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_plant(
    body: PlantCreate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    try:
        data = body.model_dump(exclude={"tag_names", "auto_cover_image"})
        # Infer outdoor/garden defaults when environment omitted
        data["environment_auto"] = body.environment is None
        plant = await plant_service.create_plant(
            db,
            household_id=ctx.household.id,
            created_by_user_id=ctx.user.id,
            data=data,
            tag_names=body.tag_names,
        )
        # Auto cover image (Wikimedia, free) — can be disabled per household or request
        settings = ctx.household.settings or {}
        auto_default = bool(settings.get("auto_cover_images", True))
        want_auto = auto_default if body.auto_cover_image is None else body.auto_cover_image
        if want_auto and plant.taxon is not None and plant.cover_photo_id is None:
            await plant_service.try_auto_cover_from_wikimedia(
                db, plant=plant, user_id=ctx.user.id
            )
            plant = await plant_service.get_plant(
                db, household_id=ctx.household.id, plant_id=plant.id
            )
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant.id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return _detail(plant)


class BulkImportBody(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    auto_cover: bool = True
    default_environment: str | None = None


@router.post("/households/{household_id}/plants/import")
async def import_plants(
    body: BulkImportBody,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> dict:
    settings = ctx.household.settings or {}
    auto_default = bool(settings.get("auto_cover_images", True))
    want_auto = body.auto_cover and auto_default
    try:
        result = await plant_service.import_plants_bulk(
            db,
            household_id=ctx.household.id,
            created_by_user_id=ctx.user.id,
            text=body.text,
            auto_cover=want_auto,
            default_environment=body.default_environment,
        )
        await db.commit()
        return result
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc


@router.post(
    "/households/{household_id}/plants/{plant_id}/copy",
    response_model=PlantDetail,
    status_code=status.HTTP_201_CREATED,
)
async def copy_plant(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    try:
        plant = await plant_service.copy_plant(
            db,
            household_id=ctx.household.id,
            plant_id=plant_id,
            created_by_user_id=ctx.user.id,
        )
        # Optional auto cover for the copy (same species)
        settings = ctx.household.settings or {}
        if bool(settings.get("auto_cover_images", True)) and plant.taxon is not None:
            if plant.cover_photo_id is None:
                await plant_service.try_auto_cover_from_wikimedia(
                    db, plant=plant, user_id=ctx.user.id
                )
                plant = await plant_service.get_plant(
                    db, household_id=ctx.household.id, plant_id=plant.id
                )
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant.id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return _detail(plant)


@router.post(
    "/households/{household_id}/plants/{plant_id}/auto-cover",
    response_model=PlantDetail,
)
async def fetch_auto_cover(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    if plant.taxon is None:
        raise HTTPException(
            status_code=400, detail="Link a species first so we know what photo to fetch."
        )
    ok = await plant_service.try_auto_cover_from_wikimedia(
        db, plant=plant, user_id=ctx.user.id
    )
    await db.commit()
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    assert plant is not None
    if not ok and plant.cover_photo_id is None:
        raise HTTPException(
            status_code=404,
            detail="No free Wikimedia photo found for this species. Try a different name or upload your own.",
        )
    return _detail(plant)


@router.get("/households/{household_id}/plants/{plant_id}/photo-search")
async def search_plant_photos(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
    q: str | None = Query(None, description="Search text; defaults to species / nickname"),
    limit: int = Query(12, ge=1, le=24),
) -> dict:
    """Search free Wikimedia/Wikipedia images so the user can pick a cover."""
    from app.modules.identify.wikimedia import search_plant_images

    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    query = (q or "").strip()
    if not query:
        if plant.taxon and plant.taxon.scientific_name:
            query = plant.taxon.scientific_name
            commons = list(plant.taxon.common_names or [])
            if commons:
                query = f"{query} {commons[0]}"
        else:
            query = plant.nickname
    results = await search_plant_images(query, limit=limit)
    return {"query": query, "results": results}


class CoverFromUrlBody(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    caption: str | None = Field(default=None, max_length=300)


@router.post(
    "/households/{household_id}/plants/{plant_id}/cover-from-url",
    response_model=PlantDetail,
)
async def cover_from_url(
    plant_id: uuid.UUID,
    body: CoverFromUrlBody,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    """Import a chosen Wikimedia image URL as the plant cover."""
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    try:
        plant = await plant_service.set_cover_from_url(
            db,
            plant=plant,
            user_id=ctx.user.id,
            image_url=body.url,
            caption=body.caption,
        )
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant_id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not import image: {exc}") from exc
    return _detail(plant)


@router.get("/households/{household_id}/plants/{plant_id}", response_model=PlantDetail)
async def get_plant(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    return _detail(plant)


@router.patch("/households/{household_id}/plants/{plant_id}", response_model=PlantDetail)
async def update_plant(
    plant_id: uuid.UUID,
    body: PlantUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    try:
        data = body.model_dump(exclude_unset=True, exclude={"tag_names"})
        tag_names = body.tag_names if "tag_names" in body.model_fields_set else None
        plant = await plant_service.update_plant(
            db,
            plant,
            household_id=ctx.household.id,
            data=data,
            tag_names=tag_names,
        )
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant_id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return _detail(plant)


@router.post(
    "/households/{household_id}/plants/{plant_id}/archive",
    response_model=PlantDetail,
)
async def archive_plant(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    await plant_service.archive_plant(db, plant)
    await db.commit()
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    assert plant is not None
    return _detail(plant)


@router.post(
    "/households/{household_id}/plants/{plant_id}/restore",
    response_model=PlantDetail,
)
async def restore_plant(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    try:
        plant = await plant_service.restore_plant(db, plant)
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant_id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return _detail(plant)


@router.post(
    "/households/{household_id}/plants/{plant_id}/decease",
    response_model=PlantDetail,
)
async def decease_plant(
    plant_id: uuid.UUID,
    body: DeceaseRequest,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    await plant_service.decease_plant(
        db, plant, deceased_at=body.deceased_at, reason=body.reason
    )
    await db.commit()
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    assert plant is not None
    return _detail(plant)


@router.delete(
    "/households/{household_id}/plants/{plant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_plant(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("admin"))],
    db: DbSession,
) -> None:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    await plant_service.delete_plant(db, plant)
    await db.commit()


# --- Photos ---


@router.get(
    "/households/{household_id}/plants/{plant_id}/photos",
    response_model=list[PhotoPublic],
)
async def list_photos(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[PhotoPublic]:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    photos = sorted(plant.photos, key=lambda p: p.created_at, reverse=True)
    return [
        PhotoPublic(**plant_service.photo_to_public(p, cover_id=plant.cover_photo_id))
        for p in photos
    ]


@router.post(
    "/households/{household_id}/plants/{plant_id}/photos",
    response_model=PhotoPublic,
    status_code=status.HTTP_201_CREATED,
)
async def upload_photo(
    plant_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
    file: Annotated[UploadFile, File()],
    caption: Annotated[str | None, Form()] = None,
    set_cover: Annotated[bool, Form()] = False,
) -> PhotoPublic:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        photo = await plant_service.add_photo(
            db,
            plant=plant,
            household_id=ctx.household.id,
            user_id=ctx.user.id,
            data=content,
            content_type=content_type,
            caption=caption,
            set_cover=set_cover,
        )
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant_id
        )
        assert plant is not None
    except (PlantError, MediaError) as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return PhotoPublic(**plant_service.photo_to_public(photo, cover_id=plant.cover_photo_id))


@router.patch(
    "/households/{household_id}/photos/{photo_id}",
    response_model=PhotoPublic,
)
async def update_photo(
    photo_id: uuid.UUID,
    body: PhotoUpdate,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PhotoPublic:
    photo = await plant_service.get_photo(
        db, household_id=ctx.household.id, photo_id=photo_id
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(photo, k, v)
    await db.commit()
    await db.refresh(photo)
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=photo.plant_id
    )
    cover_id = plant.cover_photo_id if plant else None
    return PhotoPublic(**plant_service.photo_to_public(photo, cover_id=cover_id))


@router.post(
    "/households/{household_id}/plants/{plant_id}/photos/{photo_id}/cover",
    response_model=PlantDetail,
)
async def set_cover(
    plant_id: uuid.UUID,
    photo_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> PlantDetail:
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=plant_id
    )
    photo = await plant_service.get_photo(
        db, household_id=ctx.household.id, photo_id=photo_id
    )
    if plant is None or photo is None:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        await plant_service.set_cover_photo(db, plant, photo)
        await db.commit()
        plant = await plant_service.get_plant(
            db, household_id=ctx.household.id, plant_id=plant_id
        )
        assert plant is not None
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc
    return _detail(plant)


@router.delete(
    "/households/{household_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_photo(
    photo_id: uuid.UUID,
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
) -> None:
    photo = await plant_service.get_photo(
        db, household_id=ctx.household.id, photo_id=photo_id
    )
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    plant = await plant_service.get_plant(
        db, household_id=ctx.household.id, plant_id=photo.plant_id
    )
    if plant is None:
        raise HTTPException(status_code=404, detail="Plant not found")
    try:
        await plant_service.delete_photo(db, plant, photo)
        await db.commit()
    except PlantError as exc:
        await db.rollback()
        raise _plant_err(exc) from exc


@router.get("/media/{token}")
async def get_media(token: str) -> FileResponse:
    try:
        key = decode_media_token(token)
        path = absolute_media_path(key)
    except MediaError as exc:
        raise _plant_err(exc) from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    media_type = "image/jpeg"
    if path.suffix.lower() in {".png"}:
        media_type = "image/png"
    elif path.suffix.lower() in {".webp"}:
        media_type = "image/webp"
    return FileResponse(path, media_type=media_type)


@router.get("/households/{household_id}/tags", response_model=list[TagPublic])
async def list_tags(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("viewer"))],
    db: DbSession,
) -> list[TagPublic]:
    tags = await plant_service.list_household_tags(db, ctx.household.id)
    return [TagPublic.model_validate(t) for t in tags]


@router.post("/households/{household_id}/identify")
async def identify_plant_photo(
    ctx: Annotated[HouseholdContext, Depends(require_household_role("member"))],
    db: DbSession,
    file: Annotated[UploadFile, File()],
) -> dict:
    """Identify a plant from a photo via PlantNet (optional free API key)."""
    from app.core.config import get_settings
    from app.modules.identify.plantnet import identify_plant
    from app.modules.timeline import service as timeline_service

    content = await file.read()
    settings = ctx.household.settings or {}
    provider = str(settings.get("plant_id_provider") or "plantnet")
    if provider == "none":
        raise HTTPException(
            status_code=400,
            detail=(
                "Plant photo ID is turned off in Settings. Choose PlantNet there "
                "(free key at my.plantnet.org) or identify species manually from the catalog."
            ),
        )
    key = settings.get("plantnet_api_key") or get_settings().plantnet_api_key
    if not key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Plant ID needs a free PlantNet API key. Get one at https://my.plantnet.org/ "
                "then add it in Settings → Online helpers, or set PLANTNET_API_KEY in .env."
            ),
        )
    try:
        candidates = await identify_plant(
            content,
            filename=file.filename or "photo.jpg",
            content_type=file.content_type or "image/jpeg",
            api_key=str(key),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await timeline_service.create_event(
        db,
        household_id=ctx.household.id,
        event_type="identified",
        actor_user_id=ctx.user.id,
        payload={"provider": "plantnet", "candidates": candidates[:5]},
    )
    await db.commit()
    return {"provider": "plantnet", "candidates": candidates}
