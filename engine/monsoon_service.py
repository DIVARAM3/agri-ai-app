"""
AgriAI - Monsoon Service Module
Retrieves and normalizes official seasonal monsoon outlook bulletins from the
India Meteorological Department (IMD) with robust fallbacks and caching.
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# In-memory cache for monsoon data
_MONSOON_CACHE: Dict[str, Any] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def _load_reference_monsoon_data() -> Optional[Dict[str, Any]]:
    """Load verified official IMD reference data from local storage."""
    ref_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'monsoon_reference.json')
    if not os.path.exists(ref_path):
        return None
    try:
        with open(ref_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_official_monsoon_bulletin(state: Optional[str] = None, district: Optional[str] = None, force_unavailable: bool = False) -> Dict[str, Any]:
    """
    Retrieve normalized official IMD monsoon outlook.
    Selects the seasonally relevant official bulletin (Southwest or Northeast monsoon)
    and resolves the relevant meteorological subdivision based on the farmer's state.
    """
    if force_unavailable:
        return {
            "status": "Unavailable",
            "message": "Official monsoon information is temporarily unavailable.",
            "source": "India Meteorological Department (IMD)",
            "source_url": "https://mausam.imd.gov.in/"
        }

    cache_key = f"{state or ''}|{district or ''}".strip().lower()
    now = datetime.now()

    # Check cache
    if cache_key in _MONSOON_CACHE:
        entry = _MONSOON_CACHE[cache_key]
        if (now - entry["timestamp"]).total_seconds() < CACHE_TTL_SECONDS:
            return entry["data"]

    ref_data = _load_reference_monsoon_data()
    if not ref_data or "bulletins" not in ref_data:
        return {
            "status": "Unavailable",
            "message": "Official monsoon information is temporarily unavailable.",
            "source": "India Meteorological Department (IMD)",
            "source_url": "https://mausam.imd.gov.in/"
        }

    bulletins = ref_data.get("bulletins", {})

    # Determine seasonal relevance based on current calendar month (1-12)
    # June to September (6-9): Southwest Monsoon
    # October to December (10-12) and September transition: Northeast / Post-monsoon for South India
    # January to May (1-5): Pre-monsoon / Upcoming Southwest Outlook
    current_month = now.month
    state_clean = (state or "").strip().lower()

    is_south_peninsular = any(s in state_clean for s in ["tamil nadu", "kerala", "andhra", "karnataka", "puducherry"])

    if is_south_peninsular and current_month in [9, 10, 11, 12]:
        active_key = "northeast_monsoon"
    elif current_month in [6, 7, 8, 9]:
        active_key = "southwest_monsoon"
    else:
        # Default to Northeast if Tamil Nadu/South India in autumn/winter, else Southwest
        active_key = "northeast_monsoon" if is_south_peninsular else "southwest_monsoon"

    bulletin = bulletins.get(active_key, list(bulletins.values())[0])

    # Resolve regional subdivision outlook if matching state
    regional_outlooks = bulletin.get("regional_outlooks", {})
    matched_region_name = "All-India / Broad Zonal"
    matched_region_outlook = None

    if state:
        for reg_key, reg_info in regional_outlooks.items():
            if reg_key.lower() in state_clean or state_clean in reg_key.lower():
                matched_region_name = reg_info.get("subdivision", reg_key)
                matched_region_outlook = reg_info
                break

    # If state did not match specific subdivision, check if south peninsular applies
    if not matched_region_outlook and is_south_peninsular and "South Peninsular India" in regional_outlooks:
        matched_region_name = "South Peninsular India"
        matched_region_outlook = regional_outlooks["South Peninsular India"]

    normalized = {
        "status": "Available",
        "source": "India Meteorological Department",
        "agency": ref_data.get("agency", "Ministry of Earth Sciences, Govt. of India"),
        "source_url": bulletin.get("source_url", "https://mausam.imd.gov.in/"),
        "bulletin_id": bulletin.get("id", "IMD-MONSOON"),
        "season": bulletin.get("season", "Indian Monsoon"),
        "title": bulletin.get("title", "Official IMD Seasonal Monsoon Outlook"),
        "published_date": bulletin.get("published_date", "Official Seasonal Release"),
        "issuing_office": bulletin.get("issuing_office", "National Weather Forecasting Centre, IMD"),
        "summary": bulletin.get("summary", ""),
        "region": matched_region_name,
        "regional_outlook": matched_region_outlook,
        "all_regions": regional_outlooks,
        "monitoring_advisories": ref_data.get("monitoring_advisories", []),
        "disclaimer": ref_data.get("disclaimer", "Official meteorological information is sourced directly from the India Meteorological Department.")
    }

    _MONSOON_CACHE[cache_key] = {
        "timestamp": now,
        "data": normalized
    }

    return normalized
