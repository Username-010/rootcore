"""Household-scoped read-only integrations and plant sensor bindings."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, HouseholdContext, require_household_role
from app.core.config import get_settings
from app.core.sensor_body_limit import bounded_body, write_guard
from app.modules.plants.models import Plant
from app.modules.sensors.adapter import SensorError
from app.modules.sensors.models import SensorBinding
from app.modules.sensors.registry import ADAPTERS, CATALOG


class SensorRoute(APIRoute):
    """Check browser origin and bound streamed bodies before FastAPI parses JSON."""

    def get_route_handler(self):
        original = super().get_route_handler()

        async def guarded(request: Request):
            write_guard(request)
            if request.method not in {
                "GET",
                "HEAD",
                "OPTIONS",
            } and not request.scope.get("sensor_body_bounded"):
                request._body = await bounded_body(request)
            return await original(request)

        return guarded


router = APIRouter(
    prefix="/api/v1/households/{household_id}",
    tags=["sensors"],
    route_class=SensorRoute,
)
ReadContext = Annotated[HouseholdContext, Depends(require_household_role("viewer"))]
WriteContext = Annotated[HouseholdContext, Depends(require_household_role("member"))]
AdminContext = Annotated[HouseholdContext, Depends(require_household_role("admin"))]


def configured(household_id):
    settings = get_settings()
    return bool(
        settings.rootcore_ha_url
        and settings.rootcore_ha_token
        and settings.rootcore_ha_household_id == str(household_id)
    )


def adapter_for(household_id):
    if not configured(household_id):
        raise HTTPException(
            409,
            "Home Assistant is not configured for this household. Ask the server administrator.",
        )
    settings = get_settings()
    try:
        return ADAPTERS["home_assistant"](
            settings.rootcore_ha_url, settings.rootcore_ha_token.get_secret_value()
        )
    except SensorError as exc:
        raise HTTPException(409, str(exc)) from None


async def discover(household_id):
    try:
        return await adapter_for(household_id).discover()
    except SensorError as exc:
        raise HTTPException(502, str(exc)) from None


@router.get("/integrations")
async def integrations(ctx: ReadContext):
    return [{**entry, "configured": configured(ctx.household.id)} for entry in CATALOG]


@router.post("/integrations/home_assistant/test")
async def test_connection(ctx: AdminContext):
    readings = await discover(ctx.household.id)
    return {"connected": True, "sensor_count": len(readings), "read_only": True}


@router.get("/sensors")
async def sensors(ctx: ReadContext):
    return await discover(ctx.household.id)


@router.get("/sensors/{entity_id}/history")
async def history(entity_id: str, ctx: ReadContext, hours: int = 24):
    if hours not in {24, 168}:
        raise HTTPException(422, "History window must be 24 or 168 hours")
    readings = await discover(ctx.household.id)
    if not any(r["entity_id"] == entity_id for r in readings):
        raise HTTPException(404, "Sensor not exposed by this integration")
    try:
        points = await adapter_for(ctx.household.id).history(entity_id, hours)
    except SensorError as exc:
        raise HTTPException(502, str(exc)) from None
    return {
        "entity_id": entity_id,
        "hours": hours,
        "source": "Home Assistant Recorder",
        "points": points,
    }


class BindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: uuid.UUID
    entity_id: str = Field(pattern=r"^sensor\.[a-z0-9_]{1,200}$", max_length=208)


def public_binding(binding):
    return {
        "id": str(binding.id),
        "plant_id": str(binding.plant_id),
        "entity_id": binding.entity_id,
        "adapter_id": binding.adapter_id,
    }


@router.get("/sensor-bindings")
async def bindings(ctx: ReadContext, db: DbSession):
    rows = await db.scalars(
        select(SensorBinding)
        .where(SensorBinding.household_id == ctx.household.id)
        .order_by(SensorBinding.created_at)
    )
    return [public_binding(row) for row in rows]


@router.post("/sensor-bindings", status_code=201)
async def create_binding(body: BindingCreate, ctx: WriteContext, db: DbSession):
    plant = await db.scalar(
        select(Plant.id).where(
            Plant.id == body.plant_id, Plant.household_id == ctx.household.id
        )
    )
    if plant is None:
        raise HTTPException(404, "Plant not found")
    readings = await discover(ctx.household.id)
    if not any(r["entity_id"] == body.entity_id for r in readings):
        raise HTTPException(404, "Sensor not exposed by this integration")
    binding = SensorBinding(
        household_id=ctx.household.id,
        plant_id=body.plant_id,
        entity_id=body.entity_id,
        adapter_id="home_assistant",
    )
    db.add(binding)
    try:
        await db.commit()
        await db.refresh(binding)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            409, "This sensor is already linked to this plant"
        ) from None
    return public_binding(binding)


@router.delete("/sensor-bindings/{binding_id}", status_code=204)
async def delete_binding(binding_id: uuid.UUID, ctx: WriteContext, db: DbSession):
    binding = await db.scalar(
        select(SensorBinding).where(
            SensorBinding.id == binding_id,
            SensorBinding.household_id == ctx.household.id,
        )
    )
    if binding is None:
        raise HTTPException(404, "Sensor binding not found")
    await db.delete(binding)
    await db.commit()
    return Response(status_code=204)
