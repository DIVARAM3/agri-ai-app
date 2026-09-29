"""
AgriAI - Monsoon Interpretation Engine
Provides conservative, rule-based agricultural interpretation of official IMD monsoon outlooks.
Does NOT predict weather or invent monsoon data.
"""

from typing import Dict, List, Optional, Any
from engine.crop_engine import get_crop_profile


def interpret_monsoon_outlook(
    monsoon_data: Dict[str, Any],
    crop_name: Optional[str] = None,
    location: Optional[Dict[str, str]] = None,
    weather_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate conservative agricultural decision-support interpretation
    grounded in officially published IMD seasonal outlook information.
    """
    if not monsoon_data or monsoon_data.get("status") != "Available":
        return {
            "status": "Unavailable",
            "official_summary": monsoon_data.get("message", "Official IMD monsoon information is temporarily unavailable."),
            "agri_context": [],
            "monitoring_points": [
                "Monitor district rainfall updates from local IMD Agromet Advisory Services.",
                "Check soil moisture in the root zone before scheduling irrigation.",
                "Follow advisories from local Krishi Vigyan Kendra (KVK) and state agricultural extension."
            ],
            "confidence": "Official source information",
            "source": "India Meteorological Department (IMD)",
            "source_url": monsoon_data.get("source_url", "https://mausam.imd.gov.in/"),
            "crop_context": None,
            "location_context": None,
            "weather_context": None
        }

    official_summary = monsoon_data.get("summary", "")
    season_name = monsoon_data.get("season", "Monsoon")
    region_name = monsoon_data.get("region", "All-India")
    regional_outlook = monsoon_data.get("regional_outlook")

    # 1. Agricultural Interpretation Context (Conservative, agronomy-focused)
    agri_context = [
        {
            "topic": "Rainfall Monitoring",
            "icon": "🌧️",
            "text": "Track 7-day cumulative precipitation and local rain gauge records against soil water infiltration capacity before committing to field operations."
        },
        {
            "topic": "Irrigation Planning",
            "icon": "💧",
            "text": "Utilize seasonal precipitation to recharge on-farm farm ponds and open wells. Delay scheduled pump or canal watering when active rainfall pulses are indicated by short-range forecasts."
        },
        {
            "topic": "Soil Moisture Consistency",
            "icon": "🌱",
            "text": "Inspect soil moisture at the active 15–30 cm root zone before sowing, basal fertilizer application, or biofertilizer inoculation to ensure adequate hydration without saturation."
        },
        {
            "topic": "Field Drainage Awareness",
            "icon": "🌊",
            "text": "Clear primary farm drainage channels, boundary furrows, and bund spillways to prevent ponding and root suffocation during episodic heavy downpours."
        },
        {
            "topic": "Crop-Stage Planning",
            "icon": "📅",
            "text": "Review moisture sensitivity of current crop growth stages. Avoid high-volume nitrogen topdressing immediately prior to anticipated heavy rain spells to minimize leaching losses."
        }
    ]

    # 2. Farmer Monitoring Points Checklist
    monitoring_points = [
        "Monitor district rainfall updates from local IMD and State Agromet bulletins (GKMS).",
        "Monitor root-zone soil moisture before making supplementary irrigation decisions.",
        "Watch for prolonged dry periods or mid-season dry spells during vegetative establishment.",
        "Watch for heavy-rain events that could flood low-lying plots or cause seedling lodging.",
        "Review crop stage and canopy health before initiating fertilizer topdressing or mechanical weeding."
    ]

    # 3. Location Context
    location_context = None
    if location and any(str(v).strip() for v in location.values()):
        v_str = location.get("village", "").strip()
        d_str = location.get("district", "").strip()
        s_str = location.get("state", "").strip()
        loc_display = ", ".join([p for p in [v_str, d_str, s_str] if p])

        reg_note = ""
        if regional_outlook and "category" in regional_outlook:
            reg_note = f" (Official Regional Outlook for {region_name}: {regional_outlook['category']})"

        location_context = {
            "has_location": True,
            "display": loc_display,
            "village": v_str,
            "district": d_str,
            "state": s_str,
            "region": region_name,
            "note": (
                f"Location identified: {loc_display}{reg_note}. "
                "Note: Official seasonal monsoon forecasts are prepared at broad meteorological subdivision scales. "
                "Village-level operational decisions should always be cross-referenced with daily local weather and block-level KVK advisories."
            )
        }
    else:
        location_context = {
            "has_location": False,
            "display": "Location Not Specified",
            "note": "Complete your location in Crop Advisor to receive location context."
        }

    # 4. Crop Context (If Crop Selected)
    crop_context = None
    if crop_name:
        crop_profile = get_crop_profile(crop_name)
        water_req = crop_profile.get("water_requirement", "Medium") if crop_profile else "Medium"

        crop_specific_notes = {
            "Moringa": (
                "Moringa possesses deep taproots and high drought tolerance, but is exceptionally vulnerable to root rot "
                "under prolonged waterlogging. During the monsoon season, keep tree basins well-drained and construct raised "
                "furrows to steer surface runoff away from tree collars."
            ),
            "Paddy": (
                "Paddy benefits significantly from abundant seasonal rainfall. Maintain sturdy field bunds (varappu) to "
                "conserve standing rainwater, reducing tube-well electricity and pumping costs during critical tillering and panicle initiation."
            ),
            "Groundnut": (
                "Groundnut requires steady moisture during pegging and pod development. However, excessive rain near maturity "
                "induces in-situ seed germination and pod rot. Ensure rapid runoff furrows are maintained across broadbeds."
            ),
            "Tomato": (
                "Tomato is sensitive to both moisture stress and continuous foliar wetness. Wet humid conditions elevate risks "
                "of early and late blight. Ensure stake supports are reinforced against monsoon wind gusts and maintain drip irrigation."
            ),
            "Cotton": (
                "Cotton requires moisture security in early vegetative stages but dry weather during boll bursting. "
                "Monitor regional rainfall pulses to time secondary nutrient sprays without wash-off."
            ),
            "Banana": (
                "Banana has high seasonal water demands. However, waterlogged soil suffocates root suckers and destabilizes "
                "heavy bunches. Provide bamboo/casuarina propping to protect fruiting trees against monsoon wind gusts."
            ),
            "Chilli": (
                "Chilli plants cannot tolerate water stagnation even for short periods, which triggers anthracnose fruit rot and damping-off. "
                "Prioritize raised-bed planting and clear field drainage ditches."
            ),
            "Maize": (
                "Maize requires steady moisture through silking and tasseling. Ensure field drainage prevents water pooling in root crowns "
                "during torrential monsoon showers."
            )
        }

        note = crop_specific_notes.get(
            crop_name,
            f"{crop_name} is categorized with {water_req} water requirement. "
            "Use the seasonal outlook together with crop growth stage, soil moisture and local extension guidance."
        )

        crop_context = {
            "crop": crop_name,
            "water_requirement": water_req,
            "agronomic_note": note,
            "disclaimer": "Use the seasonal outlook together with crop growth stage, soil moisture and local extension guidance. AgriAI does not invent crop-specific monsoon thresholds."
        }

    # 5. Weather Context (Step 7 short-term forecast connection)
    weather_context = None
    if weather_data and weather_data.get("success"):
        curr = weather_data.get("current", {})
        daily = weather_data.get("daily", [])
        total_7d_rain = sum(d.get("rainfall", 0.0) for d in daily)
        today_rain_prob = daily[0].get("rain_probability", 0) if daily else 0

        weather_context = {
            "available": True,
            "temperature": curr.get("temperature", "--"),
            "condition": curr.get("condition", "Current Weather"),
            "rainfall_current": curr.get("rain", 0.0),
            "rain_probability_today": today_rain_prob,
            "rainfall_7d_total": round(total_7d_rain, 1),
            "forecast_days": len(daily),
            "disclaimer": "Current weather is separate from the seasonal monsoon outlook. Short-term forecast reflects 7-day atmospheric observations; seasonal monsoon outlook represents broad climatological trends."
        }

    return {
        "status": "Available",
        "season": season_name,
        "region": region_name,
        "official_summary": official_summary,
        "agri_context": agri_context,
        "monitoring_points": monitoring_points,
        "location_context": location_context,
        "crop_context": crop_context,
        "weather_context": weather_context,
        "confidence": "Official source information",
        "source": "India Meteorological Department (IMD)",
        "source_url": monsoon_data.get("source_url", "https://mausam.imd.gov.in/"),
        "published_date": monsoon_data.get("published_date", "Official Seasonal Release"),
        "bulletin_id": monsoon_data.get("bulletin_id", "IMD-MONSOON"),
        "disclaimer": "AgriAI provides agronomic decision-support context grounded in official IMD publications. AgriAI does not independently predict, modify, or simulate monsoon rainfall, onset dates, or withdrawal timelines."
    }
