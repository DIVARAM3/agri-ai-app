"""
AgriAI - Crop Advisor & Intelligence Engine
Handles crop database queries, validation, profile loading,
and multi-factor crop suitability evaluation combining soil test data,
crop physiological requirements, and farm location.
"""

import os
import json
from engine.soil_engine import analyze_soil, safe_float

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'crops.json')

_CROPS_CACHE = None


def load_crops() -> list:
    """Load all crops from data/crops.json with caching."""
    global _CROPS_CACHE
    if _CROPS_CACHE is not None:
        return _CROPS_CACHE

    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            _CROPS_CACHE = json.load(f)
            return _CROPS_CACHE
    except Exception:
        return []


def get_crop_by_name(crop_name: str) -> dict | None:
    """Find a crop by name, ID, or aliases (case-insensitive)."""
    if not crop_name:
        return None

    crop_name_clean = crop_name.strip().lower()
    crops = load_crops()
    for crop in crops:
        if crop.get('name', '').lower() == crop_name_clean or crop.get('id', '').lower() == crop_name_clean:
            return crop
        # Check aliases
        for alias in crop.get('aliases', []):
            if alias.strip().lower() == crop_name_clean:
                return crop
    return None


def validate_crop(crop_name: str) -> bool:
    """Check if crop exists in the crops database."""
    return get_crop_by_name(crop_name) is not None


def get_crop_profile(crop_name: str) -> dict | None:
    """Return the complete crop profile."""
    return get_crop_by_name(crop_name)


def combine_crop_and_soil(crop_name: str, soil_data: dict | None, location: dict | None) -> dict:
    """
    Creates a structured combined object for analysis:
    {
        "crop": {...},
        "soil": {...},
        "location": {...},
        "status": "ready_for_analysis"
    }
    """
    crop_profile = get_crop_by_name(crop_name)

    clean_soil = {
        'ph': None,
        'nitrogen': None,
        'phosphorus': None,
        'potassium': None,
        'organic_carbon': None,
        'ec': None
    }
    if soil_data and isinstance(soil_data, dict):
        for k in clean_soil:
            clean_soil[k] = safe_float(soil_data.get(k))

    clean_location = {
        'village': '',
        'district': '',
        'state': 'Tamil Nadu'
    }
    if location and isinstance(location, dict):
        clean_location.update({k: v for k, v in location.items() if v is not None})

    has_soil_values = any(v is not None for v in clean_soil.values())

    return {
        "crop": crop_profile,
        "soil": clean_soil,
        "location": clean_location,
        "has_soil_data": has_soil_values,
        "status": "ready_for_analysis" if (crop_profile and has_soil_values) else "incomplete_data"
    }


def evaluate_crop_suitability(crop_profile: dict, soil_analysis: dict) -> dict:
    """
    Evaluate crop suitability based on:
    1. Soil pH vs Crop preferred pH
    2. EC / Salinity vs Crop tolerance
    3. Organic Carbon condition
    4. Macronutrient reserves (N, P, K)
    5. Soil physical traits & water requirement

    Returns:
    {
        "status": "Highly Suitable" | "Suitable" | "Needs Attention" | "Not Recommended",
        "reasons": list of strings,
        "concerns": list of strings,
        "priority_actions": list of dicts (HIGH, MEDIUM, LOW),
        "summary": str
    }
    """
    reasons = []
    concerns = []
    priority_actions = []

    critical_count = 0
    moderate_count = 0

    crop_name = crop_profile.get('name', 'Selected Crop')
    params = soil_analysis.get('parameters', {})

    # 1. Soil pH vs Crop Preferred pH
    pref_ph = crop_profile.get('preferred_ph', {'min': 6.0, 'max': 7.5})
    ph_data = params.get('ph', {})
    ph_val = ph_data.get('value')

    if ph_val is not None:
        ph_min = pref_ph.get('min', 6.0)
        ph_max = pref_ph.get('max', 7.5)

        if ph_min <= ph_val <= ph_max:
            reasons.append(f"Soil pH ({ph_val}) is optimal for {crop_name} (preferred: {ph_min} - {ph_max}).")
        elif ph_val < ph_min:
            diff = round(ph_min - ph_val, 2)
            if diff <= 0.6:
                moderate_count += 1
                concerns.append(f"Soil pH ({ph_val}) is slightly below the preferred minimum ({ph_min}) for {crop_name}.")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Soil Acidity Management",
                    "guidance": "Incorporate well-decomposed organic matter or agricultural lime to gradually buffer soil acidity."
                })
            else:
                critical_count += 1
                concerns.append(f"Soil pH ({ph_val}) is acidic, well below {crop_name}'s preferred minimum ({ph_min}).")
                priority_actions.append({
                    "priority": "HIGH",
                    "title": "Corrective Liming Required",
                    "guidance": f"{crop_name} prefers a pH of {ph_min}–{ph_max}. Consult local extension officers for corrective liming or dolomite application."
                })
        else:
            diff = round(ph_val - ph_max, 2)
            if diff <= 0.6:
                moderate_count += 1
                concerns.append(f"Soil pH ({ph_val}) is slightly above the preferred maximum ({ph_max}) for {crop_name}.")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Alkalinity Buffering",
                    "guidance": "Apply organic compost and green manure to moderate root zone alkalinity."
                })
            else:
                critical_count += 1
                concerns.append(f"Soil pH ({ph_val}) is strongly alkaline for {crop_name} (prefers {ph_min} - {ph_max}).")
                priority_actions.append({
                    "priority": "HIGH",
                    "title": "Alkalinity Conditioning",
                    "guidance": f"Strongly alkaline soil limits zinc and phosphorus uptake for {crop_name}. Consider gypsum and organic matter conditioning."
                })

    # 2. EC / Salinity Assessment
    ec_data = params.get('ec', {})
    ec_val = ec_data.get('value')
    if ec_val is not None:
        if ec_val <= 1.0:
            reasons.append(f"Electrical Conductivity ({ec_val} dS/m) is normal with zero salinity stress for {crop_name}.")
        elif 1.0 < ec_val <= 2.0:
            moderate_count += 1
            concerns.append(f"Electrical Conductivity ({ec_val} dS/m) indicates slight salinity; salt-sensitive growth stages may be affected.")
            priority_actions.append({
                "priority": "MEDIUM",
                "title": "Salinity & Irrigation Monitoring",
                "guidance": "Monitor irrigation water quality and provide adequate furrow drainage to prevent root-zone salt buildup."
            })
        else:
            critical_count += 1
            concerns.append(f"Elevated soil salinity ({ec_val} dS/m) poses severe osmotic risk to {crop_name}.")
            priority_actions.append({
                "priority": "HIGH",
                "title": "Salinity Hazard Mitigation",
                "guidance": f"High salinity impairs water uptake in {crop_name}. Flush the field with good quality irrigation water prior to planting."
            })

    # 3. Organic Carbon Condition
    oc_data = params.get('organic_carbon', {})
    oc_val = oc_data.get('value')
    if oc_val is not None:
        if oc_val >= 0.50:
            reasons.append(f"Organic Carbon ({oc_val}%) provides favorable moisture retention and biological activity.")
        else:
            moderate_count += 1
            concerns.append(f"Organic Carbon ({oc_val}%) is low, restricting soil water holding capacity.")
            priority_actions.append({
                "priority": "MEDIUM",
                "title": "Organic Matter Management",
                "guidance": "Incorporate well-rotted farmyard manure, compost, or vermicompost to build soil organic reserves."
            })

    # 4. Nitrogen Condition
    n_data = params.get('nitrogen', {})
    n_val = n_data.get('value')
    if n_val is not None:
        if n_data.get('status_code') == 'optimal':
            reasons.append(f"Available Nitrogen ({n_val} kg/ha) supports active vegetative canopy development.")
        elif n_val < 280.0:
            # If nitrogen is deficient, flag priority action
            moderate_count += 1
            concerns.append(f"Available Nitrogen is low ({n_val} kg/ha), which may limit vegetative canopy expansion.")
            priority_actions.append({
                "priority": "HIGH" if n_val < 200 else "MEDIUM",
                "title": "Nitrogen Management Plan",
                "guidance": f"Consider an appropriate nitrogen-management plan based on soil-test recommendations to support {crop_name}'s vegetative stage."
            })

    # 5. Phosphorus Condition
    p_data = params.get('phosphorus', {})
    p_val = p_data.get('value')
    if p_val is not None:
        if p_data.get('status_code') == 'optimal':
            reasons.append(f"Available Phosphorus ({p_val} kg/ha) is sufficient for early root architecture.")
        elif p_val < 11.0:
            moderate_count += 1
            concerns.append(f"Available Phosphorus is low ({p_val} kg/ha).")
            priority_actions.append({
                "priority": "MEDIUM",
                "title": "Phosphorus Soil Supplementation",
                "guidance": "Incorporate phosphatic amendments as basal placement before sowing for optimal root development."
            })

    # 6. Potassium Condition
    k_data = params.get('potassium', {})
    k_val = k_data.get('value')
    if k_val is not None:
        if k_data.get('status_code') == 'optimal':
            reasons.append(f"Available Potassium ({k_val} kg/ha) provides disease resilience and water regulation.")
        elif k_val < 140.0:
            moderate_count += 1
            concerns.append(f"Available Potassium is low ({k_val} kg/ha).")
            priority_actions.append({
                "priority": "MEDIUM",
                "title": "Potassium Balance",
                "guidance": "Apply potassium as per local soil-test recommendations to enhance drought tolerance and harvest quality."
            })

    # Deduplicate priority actions by title
    seen_titles = set()
    unique_actions = []
    for action in priority_actions:
        if action['title'] not in seen_titles:
            seen_titles.add(action['title'])
            unique_actions.append(action)

    # General baseline action
    unique_actions.append({
        "priority": "LOW",
        "title": "Consult Qualified Agronomist",
        "guidance": "AgriAI provides preliminary decision support. Always consult local agricultural extension officers before applying commercial inputs."
    })

    # Sort actions by priority (HIGH, MEDIUM, LOW)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    unique_actions.sort(key=lambda x: priority_order.get(x["priority"], 3))

    # Evaluate Overall Suitability Status
    total_tested = soil_analysis.get('tested_count', 0)
    if total_tested == 0:
        status = "Needs Attention"
        summary = "No soil parameters available for evaluation."
    elif critical_count >= 2:
        status = "Not Recommended"
        summary = f"Multiple severe soil constraints detected for growing {crop_name} in current conditions."
    elif critical_count == 1 or moderate_count >= 3:
        status = "Needs Attention"
        summary = f"{crop_name} can be cultivated, but specific nutrient or soil amendments are required to ensure optimal vigor."
    elif moderate_count in {1, 2}:
        status = "Suitable"
        summary = f"Soil conditions are generally favorable for {crop_name}, with minor nutrient adjustments recommended."
    else:
        status = "Highly Suitable"
        summary = f"Soil conditions align excellently with the preferred agronomic requirements of {crop_name}."

    # Deterministic suitability score
    if total_tested == 0:
        suitability_score = 0
    else:
        score_base = 95
        score_base -= (critical_count * 25)
        score_base -= (moderate_count * 8)
        suitability_score = max(25, min(95, score_base))

    return {
        "status": status,
        "suitability_status": status,
        "suitability_score": suitability_score,
        "reasons": reasons,
        "supporting_factors": reasons,
        "concerns": concerns,
        "limiting_factors": concerns,
        "priority_actions": unique_actions,
        "summary": summary
    }


def generate_crop_soil_intelligence(crop_name: str | dict, soil_data: dict | None = None, location: dict | None = None) -> dict:
    """
    Combined intelligence engine function:
    Takes soil test data + crop name + location (or a single combined dict),
    runs soil evaluation, crop suitability analysis, and formats the consolidated intelligence report.
    """
    if isinstance(crop_name, dict) and soil_data is None and location is None:
        combined = crop_name
        crop_val = combined.get('crop')
        crop_name = crop_val.get('name') if isinstance(crop_val, dict) else (crop_val or 'Moringa')
        soil_data = combined.get('soil')
        location = combined.get('location')
    crop_profile = get_crop_by_name(crop_name)
    if not crop_profile:
        crops = load_crops()
        crop_profile = crops[0] if crops else None

    # Run soil intelligence engine
    soil_analysis = analyze_soil(soil_data)

    # Run crop suitability evaluation
    if crop_profile:
        suitability = evaluate_crop_suitability(crop_profile, soil_analysis)
    else:
        suitability = {
            "status": "Needs Attention",
            "reasons": [],
            "concerns": ["Crop profile could not be loaded."],
            "priority_actions": [],
            "summary": "Crop profile unavailable."
        }

    clean_loc = {
        'village': location.get('village', 'Kammadikottai') if location else 'Kammadikottai',
        'district': location.get('district', 'Thoothukudi') if location else 'Thoothukudi',
        'state': location.get('state', 'Tamil Nadu') if location else 'Tamil Nadu'
    }

    return {
        "crop": crop_profile,
        "location": clean_loc,
        "soil": soil_data or {},
        "soil_analysis": soil_analysis,
        "suitability": suitability,
        "observations": {
            "strengths": soil_analysis.get('strengths', []),
            "concerns": soil_analysis.get('concerns', [])
        },
        "priority_actions": suitability.get('priority_actions', []),
        "disclaimer": "AgriAI provides preliminary decision-support insights based on the available soil and crop information. For field-level recommendations and input application, consult a qualified agricultural professional or local agricultural extension service."
    }


def get_crop_categories() -> list:
    """Return unique ordered crop categories."""
    return ['All', 'Cereals', 'Pulses', 'Oilseeds', 'Vegetables', 'Commercial / Perennial']


def search_crops(query: str = '', category: str = 'All') -> list:
    """Search and filter crops by text query and category."""
    crops = load_crops()
    results = []
    q = (query or '').strip().lower()
    cat = (category or 'All').strip()

    for crop in crops:
        # Category filter
        if cat != 'All' and crop.get('category', '').lower() != cat.lower():
            continue

        # Text query filter
        if q:
            name = crop.get('name', '').lower()
            sci = crop.get('scientific_name', '').lower()
            desc = crop.get('short_description', '').lower()
            aliases = [a.lower() for a in crop.get('aliases', [])]
            if q not in name and q not in sci and q not in desc and not any(q in a for a in aliases):
                continue

        results.append(crop)
    return results


def evaluate_multiple_crops(crop_names: list, soil_analysis: dict, crop_stages: dict = None) -> list:
    """
    Evaluate multiple crops against a single soil analysis.
    Returns list of evaluated crops with suitability, growth stage, and key factors.
    """
    if not crop_names:
        return []

    stages = crop_stages or {}
    results = []

    for c_name in crop_names:
        crop_profile = get_crop_by_name(c_name)
        if not crop_profile:
            continue

        suitability = evaluate_crop_suitability(crop_profile, soil_analysis)
        stage = stages.get(crop_profile['name']) or stages.get(c_name)
        if not stage:
            stages_list = crop_profile.get('growth_stages', [])
            stage = stages_list[1] if len(stages_list) > 1 else (stages_list[0] if stages_list else 'Active Vegetative Stage')

        results.append({
            'crop': crop_profile,
            'name': crop_profile['name'],
            'id': crop_profile['id'],
            'scientific_name': crop_profile.get('scientific_name', ''),
            'category': crop_profile.get('category', 'Crops'),
            'icon': crop_profile.get('icon', '🌱'),
            'growth_stage': stage,
            'suitability': suitability,
            'score': suitability.get('suitability_score', 80),
            'status': suitability.get('status', 'Suitable'),
            'suitability_status': suitability.get('suitability_status', 'Suitable'),
            'concerns': suitability.get('concerns', []),
            'limiting_factors': suitability.get('limiting_factors', []),
            'reasons': suitability.get('reasons', []),
            'supporting_factors': suitability.get('supporting_factors', []),
            'priority_actions': suitability.get('priority_actions', []),
            'summary': suitability.get('summary', '')
        })

    return results
