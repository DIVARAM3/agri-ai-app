"""
AgriAI - Weather Intelligence Engine
Rule-based, conservative agricultural weather interpretation, weather alerts,
and crop water-demand context.
"""

from typing import Dict, List, Optional, Any
from engine.crop_engine import get_crop_profile

def generate_weather_insights(weather_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Generate 2–4 conservative farm weather insights based on current conditions
    and the 7-day forecast.
    """
    if not weather_data or not weather_data.get("success"):
        return []

    current = weather_data.get("current", {})
    daily = weather_data.get("daily", [])

    insights = []

    # 1. Rain & Moisture Insight
    total_rain_forecast = sum(d.get("rainfall", 0.0) for d in daily)
    max_rain_prob = max((d.get("rain_probability", 0) for d in daily), default=0)

    if max_rain_prob >= 60 or total_rain_forecast >= 15.0:
        rainy_days = [d["day"] for d in daily if d.get("rain_probability", 0) >= 50]
        day_str = ", ".join(rainy_days[:2]) if rainy_days else "the upcoming forecast window"
        insights.append({
            "category": "Rain Expected",
            "icon": "🌧️",
            "text": f"Elevated chance of precipitation around {day_str} (approx. {round(total_rain_forecast, 1)} mm cumulative). Review field drainage channels and adjust scheduled irrigation."
        })
    elif total_rain_forecast == 0.0 and max_rain_prob < 30:
        insights.append({
            "category": "Dry Conditions Prevailing",
            "icon": "☀️",
            "text": "Negligible rainfall predicted across the 7-day outlook. Evapotranspiration will steadily deplete surface moisture; monitor root-zone moisture consistency."
        })
    else:
        insights.append({
            "category": "Intermittent Moisture",
            "icon": "🌦️",
            "text": f"Scattered light moisture possible ({round(total_rain_forecast, 1)} mm cumulative across 7 days). Track soil moisture before initiating heavy irrigation cycles."
        })

    # 2. Temperature & Heat Insight
    max_temp_week = max((d.get("temperature_max", 0.0) for d in daily), default=current.get("temperature", 30))
    current_temp = current.get("temperature", 30)

    if max_temp_week >= 36.0 or current_temp >= 35.0:
        insights.append({
            "category": "Hot Conditions",
            "icon": "🌡️",
            "text": f"Daytime temperatures reaching up to {max_temp_week}°C. Heat accelerates plant transpiration; ensure adequate soil moisture and schedule field labor during early morning or evening hours."
        })
    elif max_temp_week <= 26.0:
        insights.append({
            "category": "Mild / Cool Weather",
            "icon": "🌤️",
            "text": f"Daytime temperatures remain moderate ({round(max_temp_week, 1)}°C max). Low heat stress favors vegetative growth and reduces daily water loss."
        })
    else:
        insights.append({
            "category": "Normal Thermal Range",
            "icon": "⛅",
            "text": f"Daytime highs hovering around {round(max_temp_week, 1)}°C, providing a standard thermal environment for active photosynthesis and flowering."
        })

    # 3. Wind & Spraying Conditions Insight
    wind_spd = current.get("wind_speed", 10.0)
    if wind_spd >= 20.0:
        insights.append({
            "category": "Breezy / Windy Weather",
            "icon": "💨",
            "text": f"Current wind speeds around {wind_spd} km/h. Avoid foliar bio-inoculant spraying or organic dusting during gusty hours to prevent drift loss and uneven application."
        })
    else:
        insights.append({
            "category": "Calm Airflow",
            "icon": "🍃",
            "text": f"Gentle wind speeds ({wind_spd} km/h) offer favorable conditions for foliar applications and standard canopy aeration."
        })

    # 4. Relative Humidity & Canopy Wetness
    humidity = current.get("humidity", 65)
    if humidity >= 78:
        insights.append({
            "category": "High Atmospheric Humidity",
            "icon": "💧",
            "text": f"Relative humidity stands at {humidity}%. High moisture and morning dew prolong leaf wetness; scout for fungal leaf spots and avoid dense weed growth around crop bases."
        })

    return insights[:4]


def generate_weather_alerts(weather_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Generate conservative weather-based alerts strictly justified by forecast thresholds.
    Categories: RAIN, HEAT, WIND, DRY CONDITIONS.
    """
    if not weather_data or not weather_data.get("success"):
        return []

    current = weather_data.get("current", {})
    daily = weather_data.get("daily", [])

    alerts = []

    # RAIN ALERT
    max_prob = max((d.get("rain_probability", 0) for d in daily), default=0)
    total_rain = sum(d.get("rainfall", 0.0) for d in daily)
    if max_prob >= 65 or total_rain >= 20.0:
        alerts.append({
            "category": "RAIN",
            "level": "warning",
            "badge": "badge-warning",
            "title": "Elevated Rain Probability Ahead",
            "reason": f"Forecast indicates rain probability reaching {max_prob}% with an estimated {round(total_rain, 1)} mm cumulative precipitation.",
            "action": "Ensure field bunds and drainage outlets are free of debris to prevent water ponding. Postpone planned fertilizer or bio-inoculant broadcast until rain subsides."
        })

    # HEAT ALERT
    max_temp = max((d.get("temperature_max", 0.0) for d in daily), default=0.0)
    if max_temp >= 37.0 or current.get("temperature", 0) >= 37.0:
        alerts.append({
            "category": "HEAT",
            "level": "danger",
            "badge": "badge-danger",
            "title": "High Daytime Temperatures Expected",
            "reason": f"Forecast peak temperature reaches {max_temp}°C, which can cause moisture stress and flower shedding in sensitive crops.",
            "action": "Maintain soil cover through organic mulching to buffer soil temperature. Avoid moisture stress by irrigating during early morning or late evening."
        })

    # WIND ALERT
    current_wind = current.get("wind_speed", 0.0)
    if current_wind >= 25.0:
        alerts.append({
            "category": "WIND",
            "level": "warning",
            "badge": "badge-warning",
            "title": "Gusty Winds Active",
            "reason": f"Wind speeds recorded at {current_wind} km/h across the local area.",
            "action": "Check support stakes for young fruit trees or climbing crops. Suspend foliar spraying operations to prevent significant drift loss."
        })

    # DRY CONDITIONS ALERT
    if total_rain == 0.0 and max_prob < 20 and max_temp >= 33.0:
        alerts.append({
            "category": "DRY CONDITIONS",
            "level": "info",
            "badge": "badge-primary",
            "title": "Prolonged Dry Outlook",
            "reason": "Seven-day forecast indicates zero rainfall with continuous sunshine and elevated daytime temperatures.",
            "action": "Plan irrigation cycles carefully based on crop growth stage. Check soil moisture in the active 15–30 cm root zone before applying supplementary water."
        })

    return alerts


def generate_crop_weather_context(crop_name: Optional[str], weather_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Provide conservative agronomic context connecting the farmer's selected crop
    water requirements with the active weather forecast.
    """
    if not crop_name or not weather_data or not weather_data.get("success"):
        return None

    crop_prof = get_crop_profile(crop_name)
    water_req = crop_prof.get("water_requirement", "Medium") if crop_prof else "Medium"

    total_rain = sum(d.get("rainfall", 0.0) for d in weather_data.get("daily", []))
    max_temp = max((d.get("temperature_max", 0.0) for d in weather_data.get("daily", [])), default=30.0)

    # General crop-water interpretations grounded in agronomy
    crop_notes = {
        "Moringa": (
            "Moringa is drought-hardy and sensitive to stagnant water in the root basin. "
            f"With {round(total_rain, 1)} mm rain in the 7-day forecast, ensure basin drainage is clear "
            "and avoid water accumulation around the tree collar."
        ),
        "Paddy": (
            "Paddy requires regular water replenishment and consistent standing water during tillering and flowering. "
            f"With forecasted rainfall of {round(total_rain, 1)} mm, inspect field bunds to conserve rainwater "
            "and adjust supplementary pump irrigation accordingly."
        ),
        "Groundnut": (
            "Groundnut is vulnerable to moisture stress during peg penetration and pod formation. "
            f"Under current temperatures (up to {max_temp}°C), maintain light, frequent soil moisture "
            "without creating hard soil crusting."
        ),
        "Tomato": (
            "Tomato plants are sensitive to both water deficit (causing blossom end rot) and leaf wetness "
            "(encouraging fungal leaf blights). Under current forecast conditions, prefer furrow or drip irrigation "
            "and avoid overhead canopy splashing."
        ),
        "Cotton": (
            "Cotton requires adequate root moisture during square formation and boll development, but benefits "
            "from dry weather during boll opening. Track current weather alongside local stage progression."
        ),
        "Banana": (
            "Banana has high water consumption owing to its broad canopy and rapid biomass production. "
            f"With temperatures reaching {max_temp}°C, monitor pseudostem hydration and provide regular irrigation "
            "while keeping drainage furrows open."
        ),
        "Chilli": (
            "Chilli is sensitive to flower and fruit drop under sudden heat stress and is intolerant of water stagnation. "
            "Maintain moderate, consistent moisture and avoid extreme moisture fluctuations."
        ),
        "Maize": (
            "Maize has critical water demand during the tasseling and silking stages. "
            f"With {max_temp}°C max temperature forecast, ensure plants do not experience drought stress "
            "during reproductive development."
        )
    }

    interpretation = crop_notes.get(
        crop_name,
        f"{crop_name} water requirements ({water_req}) should be evaluated alongside the current 7-day forecast "
        f"({round(total_rain, 1)} mm predicted rain and {max_temp}°C max temperature)."
    )

    return {
        "crop": crop_name,
        "water_requirement": water_req,
        "interpretation": interpretation,
        "disclaimer": "Current weather conditions should be monitored alongside the crop's water requirements and local soil texture."
    }
