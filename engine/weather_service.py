"""
AgriAI - Weather Service Module
Fetches, normalizes, and caches real-time weather and 7-day forecasts
from Open-Meteo public API with robust error handling and geocoding fallback.
"""

import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

# WMO Weather interpretation codes (WW) mapping
WMO_CODE_MAP = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Moderate Drizzle", "🌦️"),
    55: ("Dense Drizzle", "🌧️"),
    56: ("Light Freezing Drizzle", "🌧️"),
    57: ("Dense Freezing Drizzle", "🌧️"),
    61: ("Slight Rain", "🌦️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    66: ("Light Freezing Rain", "🌧️"),
    67: ("Heavy Freezing Rain", "🌧️"),
    71: ("Slight Snow Fall", "🌨️"),
    73: ("Moderate Snow Fall", "🌨️"),
    75: ("Heavy Snow Fall", "🌨️"),
    77: ("Snow Grains", "🌨️"),
    80: ("Slight Rain Showers", "🌦️"),
    81: ("Moderate Rain Showers", "🌧️"),
    82: ("Violent Rain Showers", "⛈️"),
    85: ("Slight Snow Showers", "🌨️"),
    86: ("Heavy Snow Showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with Slight Hail", "⛈️"),
    99: ("Thunderstorm with Heavy Hail", "⛈️")
}

def get_condition_from_code(code: Optional[int]) -> Tuple[str, str]:
    """Return (condition_text, icon) for a given WMO weather code."""
    if code is None:
        return ("Unknown", "⛅")
    return WMO_CODE_MAP.get(code, ("Partly Cloudy", "⛅"))

# In-memory caches
_GEOCODE_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_WEATHER_CACHE: Dict[Tuple[float, float], Dict[str, Any]] = {}

CACHE_TTL_SECONDS = 900  # 15 minutes TTL


def geocode_location(village: str = "", district: str = "", state: str = "") -> Optional[Dict[str, Any]]:
    """
    Geocode location into latitude and longitude using Open-Meteo Geocoding API.
    Uses fallback hierarchy: (village + district + state) -> (district + state) -> district -> state.
    """
    v_clean = (village or "").strip()
    d_clean = (district or "").strip()
    s_clean = (state or "").strip()

    cache_key = f"{v_clean}|{d_clean}|{s_clean}".lower()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    queries = []
    if v_clean and d_clean and s_clean:
        queries.append(f"{v_clean}, {d_clean}, {s_clean}")
    if d_clean and s_clean:
        queries.append(f"{d_clean}, {s_clean}")
    if d_clean:
        queries.append(d_clean)
    if s_clean:
        queries.append(s_clean)

    for query in queries:
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": query, "count": 3, "language": "en", "format": "json"}
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results and len(results) > 0:
                    first = results[0]
                    res_dict = {
                        "latitude": round(float(first["latitude"]), 4),
                        "longitude": round(float(first["longitude"]), 4),
                        "resolved_name": first.get("name", query),
                        "admin1": first.get("admin1", s_clean),
                        "country": first.get("country", "India")
                    }
                    _GEOCODE_CACHE[cache_key] = res_dict
                    return res_dict
        except Exception:
            continue

    _GEOCODE_CACHE[cache_key] = None
    return None


def fetch_weather_from_api(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Fetch raw weather data from Open-Meteo Forecast API."""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto"
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def format_day_label(date_str: str, index: int) -> str:
    """Format date string (YYYY-MM-DD) into user-friendly day name."""
    if index == 0:
        return "Today"
    elif index == 1:
        return "Tomorrow"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%a, %b %d")
    except Exception:
        return date_str


def parse_weather_response(raw: Dict[str, Any], location_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw Open-Meteo JSON into AgriAI structured format."""
    current_raw = raw.get("current", {})
    daily_raw = raw.get("daily", {})

    w_code = current_raw.get("weather_code")
    condition_text, icon = get_condition_from_code(w_code)

    current_data = {
        "temperature": round(float(current_raw.get("temperature_2m", 0.0)), 1),
        "humidity": int(round(float(current_raw.get("relative_humidity_2m", 0)))),
        "rain": round(float(current_raw.get("precipitation", 0.0)), 1),
        "wind_speed": round(float(current_raw.get("wind_speed_10m", 0.0)), 1),
        "weather_code": w_code,
        "condition": condition_text,
        "icon": icon
    }

    dates = daily_raw.get("time", [])
    max_temps = daily_raw.get("temperature_2m_max", [])
    min_temps = daily_raw.get("temperature_2m_min", [])
    precip_sums = daily_raw.get("precipitation_sum", [])
    precip_probs = daily_raw.get("precipitation_probability_max", [])
    weather_codes = daily_raw.get("weather_code", [])
    sunrises = daily_raw.get("sunrise", [])
    sunsets = daily_raw.get("sunset", [])

    daily_list = []
    num_days = min(len(dates), 7)
    for i in range(num_days):
        d_code = weather_codes[i] if i < len(weather_codes) else None
        d_cond, d_icon = get_condition_from_code(d_code)

        # Extract HH:MM from ISO sunrise/sunset if available
        s_rise = ""
        s_set = ""
        if i < len(sunrises) and sunrises[i]:
            s_rise = sunrises[i].split("T")[-1] if "T" in str(sunrises[i]) else str(sunrises[i])
        if i < len(sunsets) and sunsets[i]:
            s_set = sunsets[i].split("T")[-1] if "T" in str(sunsets[i]) else str(sunsets[i])

        p_prob = 0
        if i < len(precip_probs) and precip_probs[i] is not None:
            p_prob = int(round(float(precip_probs[i])))

        daily_list.append({
            "date": dates[i],
            "day": format_day_label(dates[i], i),
            "temperature_max": round(float(max_temps[i]), 1) if i < len(max_temps) else 0.0,
            "temperature_min": round(float(min_temps[i]), 1) if i < len(min_temps) else 0.0,
            "rain_probability": p_prob,
            "rainfall": round(float(precip_sums[i]), 1) if i < len(precip_sums) and precip_sums[i] is not None else 0.0,
            "weather_code": d_code,
            "condition": d_cond,
            "icon": d_icon,
            "sunrise": s_rise,
            "sunset": s_set
        })

    return {
        "success": True,
        "location": location_meta,
        "current": current_data,
        "daily": daily_list,
        "forecast_days": len(daily_list),
        "source": "Open-Meteo",
        "cached": False,
        "updated_minutes_ago": 0
    }


def get_weather(location: Optional[Dict[str, str]]) -> Dict[str, Any]:
    """
    Main entry point for weather retrieval.
    Geocodes, checks cache, fetches from API, and normalizes output.
    """
    if not location or not any(str(v).strip() for v in location.values()):
        return {
            "success": False,
            "error": "missing_location",
            "message": "Please enter a Village, District, or State to view weather."
        }

    village = location.get("village", "").strip()
    district = location.get("district", "").strip()
    state = location.get("state", "").strip()

    geo = geocode_location(village, district, state)
    if not geo:
        return {
            "success": False,
            "error": "location_not_found",
            "message": "We couldn't find this location. Please check the village/district/state spelling."
        }

    lat = geo["latitude"]
    lon = geo["longitude"]
    cache_key = (lat, lon)
    now = datetime.now()

    # Check cache
    if cache_key in _WEATHER_CACHE:
        cached_entry = _WEATHER_CACHE[cache_key]
        age_seconds = (now - cached_entry["time"]).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            data = dict(cached_entry["data"])
            data["cached"] = True
            data["updated_minutes_ago"] = max(0, int(age_seconds // 60))
            return data

    # Fetch from API
    raw = fetch_weather_from_api(lat, lon)
    if not raw:
        # If API is temporarily down, but we have an expired cache entry, serve it with notice
        if cache_key in _WEATHER_CACHE:
            cached_entry = _WEATHER_CACHE[cache_key]
            data = dict(cached_entry["data"])
            data["cached"] = True
            data["stale"] = True
            data["updated_minutes_ago"] = int((now - cached_entry["time"]).total_seconds() // 60)
            return data

        return {
            "success": False,
            "error": "api_unavailable",
            "message": "Weather data is temporarily unavailable. Please check your internet connection or try again later."
        }

    location_meta = {
        "village": village,
        "district": district,
        "state": state,
        "resolved_name": geo.get("resolved_name", district or state),
        "latitude": lat,
        "longitude": lon
    }

    try:
        parsed = parse_weather_response(raw, location_meta)
        _WEATHER_CACHE[cache_key] = {
            "time": now,
            "data": parsed
        }
        return parsed
    except Exception:
        return {
            "success": False,
            "error": "malformed_response",
            "message": "Weather data is temporarily unavailable due to a parsing issue."
        }
