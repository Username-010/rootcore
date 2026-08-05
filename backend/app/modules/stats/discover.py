"""Daily tips, plant of the day, and seasonal plant recommendations."""

from __future__ import annotations

from datetime import date
from typing import Any


TIPS = [
    "Water early in the morning so less evaporates and leaves dry before night.",
    "Finger test: poke 2 cm into the soil — if it feels cool and damp, wait another day.",
    "Empty saucers 10 minutes after watering so roots never sit in stagnant water.",
    "Group plants with similar thirst so you don’t overwater the dry-lovers.",
    "Terracotta pots dry faster than plastic — check them more often in heat.",
    "Yellow lower leaves often mean too much water; crispy edges often mean too little.",
    "Rotate indoor plants a quarter-turn each week for even growth toward the light.",
    "After a heatwave, check outdoor pots daily — small pots can dry out by afternoon.",
    "Rain doesn’t always soak pots under eaves or against a wall — still check soil.",
    "Fertilise lightly in active growth months; skip or reduce in winter rest.",
    "Dust shiny leaves gently so they can photosynthesise better.",
    "New plants need a week to settle before you change their pot or light.",
    "Bottom-watering (soak the pot 10 min) helps dry peaty mixes rewet evenly.",
    "Mulch outdoor beds lightly to hold moisture during hot, dry spells.",
    "If humidity is very low, pebble trays help tropical houseplants more than misting alone.",
]

PLANTS_OF_DAY = [
    {"name": "Monstera deliciosa", "common": "Swiss cheese plant", "why": "Forgiving indoor classic; bright indirect light.", "emoji": "🪴"},
    {"name": "Lavandula angustifolia", "common": "Lavender", "why": "Loves sun and dryish soil — great outdoor scent.", "emoji": "💜"},
    {"name": "Ocimum basilicum", "common": "Basil", "why": "Kitchen hero; water when the top feels dry.", "emoji": "🌿"},
    {"name": "Sansevieria trifasciata", "common": "Snake plant", "why": "Low light, sparse water — ideal starter plant.", "emoji": "🪴"},
    {"name": "Spathiphyllum", "common": "Peace lily", "why": "Tells you when thirsty by drooping — then rebounds.", "emoji": "🤍"},
    {"name": "Rosmarinus officinalis", "common": "Rosemary", "why": "Sunny, free-draining outdoor herb.", "emoji": "🌿"},
    {"name": "Chlorophytum comosum", "common": "Spider plant", "why": "Easy indoor; makes free baby plantlets.", "emoji": "🕷️"},
    {"name": "Mentha spicata", "common": "Mint", "why": "Loves moisture; keep in a pot so it doesn’t take over.", "emoji": "🍃"},
    {"name": "Echinocactus", "common": "Barrel cactus", "why": "Very sparse water; bright sun.", "emoji": "🌵"},
    {"name": "Ficus elastica", "common": "Rubber plant", "why": "Bold leaves; medium light and moderate water.", "emoji": "🌳"},
    {"name": "Calendula officinalis", "common": "Pot marigold", "why": "Cheerful outdoor blooms; sow in cool seasons.", "emoji": "🌼"},
    {"name": "Thymus vulgaris", "common": "Thyme", "why": "Drought-tolerant sunny herb for edges and pots.", "emoji": "🌿"},
]

# month 1-12 → seasonal suggestions
SEASONAL: dict[int, list[dict[str, str]]] = {
    1: [
        {"name": "Amaryllis / Hippeastrum", "tip": "Indoor winter blooms; keep cool and bright.", "emoji": "🌺"},
        {"name": "Forced bulbs (tulip, hyacinth)", "tip": "Bright cool windowsill colour.", "emoji": "🌷"},
        {"name": "Citrus (indoor)", "tip": "Brightest spot; careful not to overwater in short days.", "emoji": "🍋"},
    ],
    2: [
        {"name": "Seed starting (tomato, pepper)", "tip": "Start indoors under light for spring planting.", "emoji": "🌱"},
        {"name": "Primrose", "tip": "Cool-season colour for pots and beds.", "emoji": "🌸"},
        {"name": "Hellebore", "tip": "Shade garden winter interest.", "emoji": "🪴"},
    ],
    3: [
        {"name": "Peas & broad beans", "tip": "Cool outdoor sowing when soil works.", "emoji": "🟢"},
        {"name": "Lettuce & spinach", "tip": "Quick cool crops for beds and trays.", "emoji": "🥬"},
        {"name": "Hardy herbs (parsley, chives)", "tip": "Plant out as frost risk eases.", "emoji": "🌿"},
    ],
    4: [
        {"name": "Tomato seedlings", "tip": "Harden off before outdoor nights warm.", "emoji": "🍅"},
        {"name": "Marigolds", "tip": "Companion colour; love sun.", "emoji": "🧡"},
        {"name": "Basil (after frost)", "tip": "Only plant out when nights are mild.", "emoji": "🌿"},
    ],
    5: [
        {"name": "Courgette / zucchini", "tip": "Warm soil; regular water once fruiting.", "emoji": "🥒"},
        {"name": "Sunflowers", "tip": "Direct sow in sunny beds.", "emoji": "🌻"},
        {"name": "Geraniums / Pelargonium", "tip": "Classic summer pots; deadhead for more blooms.", "emoji": "🌺"},
    ],
    6: [
        {"name": "Lavender", "tip": "Peak planting for sunny free-draining spots.", "emoji": "💜"},
        {"name": "Succulents outdoors", "tip": "Full sun; water sparingly in heatwaves.", "emoji": "🌵"},
        {"name": "Climbing beans", "tip": "Warm nights; deep water weekly if dry.", "emoji": "🫘"},
    ],
    7: [
        {"name": "Drought-tolerant herbs (thyme, oregano)", "tip": "Cope with heat better than leafy salads.", "emoji": "🌿"},
        {"name": "Mulched perennials", "tip": "Hold moisture during heatwaves.", "emoji": "🪴"},
        {"name": "Evening-scented stocks", "tip": "Cooler evening blooms after hot days.", "emoji": "🌸"},
    ],
    8: [
        {"name": "Autumn vegetables (kale, chard)", "tip": "Sow for cooler months ahead.", "emoji": "🥬"},
        {"name": "Late-season annuals", "tip": "Fill gaps; keep watered in heat.", "emoji": "🌼"},
        {"name": "Figs (potted)", "tip": "Sun and careful water when fruiting.", "emoji": "🪴"},
    ],
    9: [
        {"name": "Spring bulbs", "tip": "Plant tulips, daffodils, alliums now.", "emoji": "🌷"},
        {"name": "Garlic", "tip": "Autumn plant for next summer harvest.", "emoji": "🧄"},
        {"name": "Pansies & violas", "tip": "Cool-season pots and borders.", "emoji": "🌸"},
    ],
    10: [
        {"name": "Garlic & shallots", "tip": "Still good planting window in many climates.", "emoji": "🧄"},
        {"name": "Evergreen structure (box, bay)", "tip": "Shape the winter garden.", "emoji": "🌳"},
        {"name": "Indoor foliage refresh", "tip": "Bring tender plants in before frost.", "emoji": "🪴"},
    ],
    11: [
        {"name": "Amaryllis for holidays", "tip": "Start bulbs for indoor blooms.", "emoji": "🌺"},
        {"name": "Paperwhites", "tip": "Easy forced bulbs on a pebble tray.", "emoji": "🤍"},
        {"name": "Houseplant tidy-up", "tip": "Reduce water; increase light if days are short.", "emoji": "🪴"},
    ],
    12: [
        {"name": "Poinsettia care", "tip": "Bright cool room; water when surface dries.", "emoji": "❤️"},
        {"name": "Cyclamen", "tip": "Cool windowsill colour.", "emoji": "🌸"},
        {"name": "Herb windowsill pots", "tip": "Parsley and chives for kitchen snips.", "emoji": "🌿"},
    ],
}


def build_discover(
    *,
    today: date | None = None,
    weather: dict[str, Any] | None = None,
    plant_count: int = 0,
) -> dict[str, Any]:
    today = today or date.today()
    day_index = today.toordinal()
    tip = TIPS[day_index % len(TIPS)]
    potd = PLANTS_OF_DAY[day_index % len(PLANTS_OF_DAY)]
    seasonal = list(SEASONAL.get(today.month, SEASONAL[6]))

    # Weather-aware tip boost
    extra = None
    if weather:
        t = weather.get("temperature_c")
        h = weather.get("humidity")
        rain = weather.get("precip_next_24h_mm")
        if t is not None and t >= 32:
            extra = (
                "Heatwave tip: water outdoor pots in the early morning, use deeper soaks, "
                "and move delicate plants into light shade if leaves crisp."
            )
            tip = extra
        elif t is not None and t >= 28:
            extra = (
                "Hot day: expect soil to dry faster — check small pots twice if they’re in full sun."
            )
        elif h is not None and h < 30:
            extra = "Dry air speeds evaporation — tropical houseplants may need water a day sooner."
        elif rain is not None and rain >= 5:
            extra = (
                "Rain on the way: outdoor beds may skip a watering, but pots under cover still need a check."
            )

    season_name = {
        12: "winter",
        1: "winter",
        2: "winter",
        3: "early spring",
        4: "spring",
        5: "late spring",
        6: "early summer",
        7: "summer",
        8: "late summer",
        9: "early autumn",
        10: "autumn",
        11: "late autumn",
    }.get(today.month, "this season")

    intro = (
        f"It’s {season_name}. "
        + (
            "You’ve got a good collection — try a seasonal add-on that matches your climate."
            if plant_count >= 5
            else "Starting out? Pick one easy plant from the list that matches your light and space."
        )
    )

    return {
        "tip_of_day": tip,
        "weather_nudge": extra,
        "plant_of_day": potd,
        "season_label": season_name,
        "season_intro": intro,
        "recommendations": seasonal,
    }
