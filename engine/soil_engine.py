"""
AgriAI - Soil Intelligence Engine
Provides transparent, deterministic rule-based evaluation of soil test parameters,
soil health indexing, and priority action generation based on ICAR and TNAU standards.
"""

import os
import json

REFERENCE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'soil_reference.json')

_SOIL_REFERENCE_CACHE = None


def load_soil_reference() -> dict:
    """Load soil reference data from data/soil_reference.json with caching."""
    global _SOIL_REFERENCE_CACHE
    if _SOIL_REFERENCE_CACHE is not None:
        return _SOIL_REFERENCE_CACHE

    if not os.path.exists(REFERENCE_FILE):
        return {}

    try:
        with open(REFERENCE_FILE, 'r', encoding='utf-8') as f:
            _SOIL_REFERENCE_CACHE = json.load(f)
            return _SOIL_REFERENCE_CACHE
    except Exception:
        return {}


def safe_float(val) -> float | None:
    """Safely convert any numeric representation to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        val_str = str(val).strip().replace(',', '')
        if not val_str or val_str.lower() in {'none', 'null', '—', '-', 'nan'}:
            return None
        return float(val_str)
    except (ValueError, TypeError):
        return None


def classify_parameter(param: str, raw_val, ref_data: dict | None = None) -> dict:
    """
    Classify a single soil parameter against benchmark agricultural ranges.
    Returns:
    {
        "value": float or None,
        "status": str,
        "status_code": "optimal" | "moderate" | "warning" | "unknown",
        "message": str,
        "unit": str
    }
    """
    val = safe_float(raw_val)
    if ref_data is None:
        ref_data = load_soil_reference()

    param_ref = ref_data.get(param, {})
    unit = param_ref.get('unit', '')

    if val is None:
        return {
            "value": None,
            "status": "Not Tested / Missing",
            "status_code": "unknown",
            "message": "Parameter was not provided or not detected in report.",
            "unit": unit
        }

    # 1. pH Level Classification
    if param == 'ph':
        if val < 5.5:
            return {
                "value": val,
                "status": "Strongly Acidic",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('acidic', 'Strongly acidic conditions may restrict phosphorus and micronutrient availability.'),
                "unit": unit
            }
        elif 5.5 <= val < 6.5:
            return {
                "value": val,
                "status": "Moderately Acidic",
                "status_code": "moderate",
                "message": "Slightly acidic. Tolerated by many crops, but may require liming for sensitive varieties.",
                "unit": unit
            }
        elif 6.5 <= val <= 7.5:
            return {
                "value": val,
                "status": "Neutral / Optimal",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('neutral', 'Near-neutral pH provides optimal availability of all essential nutrients.'),
                "unit": unit
            }
        elif 7.5 < val <= 8.5:
            return {
                "value": val,
                "status": "Moderately Alkaline",
                "status_code": "moderate",
                "message": "Moderately alkaline. Phosphorus and micronutrient availability (zinc, iron) may need attention.",
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "Strongly Alkaline",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('alkaline', 'Strongly alkaline. High sodium or carbonates may cause nutritional lockup.'),
                "unit": unit
            }

    # 2. Electrical Conductivity (Salinity)
    elif param == 'ec':
        if val <= 1.0:
            return {
                "value": val,
                "status": "Normal / Non-saline",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('normal', 'Soluble salt concentration is low and safe for root establishment.'),
                "unit": unit
            }
        elif 1.0 < val <= 2.0:
            return {
                "value": val,
                "status": "Critical / Slightly Saline",
                "status_code": "moderate",
                "message": param_ref.get('interpretation', {}).get('medium', 'Mild salinity detected. Sensitive crops may experience osmotic hesitation.'),
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "High / Saline Hazard",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('high', 'Elevated soil salinity can severely restrict crop water uptake and growth.'),
                "unit": unit
            }

    # 3. Organic Carbon
    elif param == 'organic_carbon':
        if val < 0.50:
            return {
                "value": val,
                "status": "Low",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('low', 'Low organic carbon limits microbial activity and moisture retention.'),
                "unit": unit
            }
        elif 0.50 <= val <= 0.75:
            return {
                "value": val,
                "status": "Medium / Adequate",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('normal', 'Adequate organic carbon maintaining active soil biology and moisture buffering.'),
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "High / Optimal",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('high', 'Favorable organic carbon fostering superior biological diversity and moisture buffering.'),
                "unit": unit
            }

    # 4. Nitrogen (N)
    elif param == 'nitrogen':
        if val < 280.0:
            return {
                "value": val,
                "status": "Low",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('low', 'Available nitrogen is below sufficiency; vegetative growth may be restricted.'),
                "unit": unit
            }
        elif 280.0 <= val <= 560.0:
            return {
                "value": val,
                "status": "Medium / Adequate",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('normal', 'Adequate available nitrogen supporting balanced vegetative growth.'),
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "High",
                "status_code": "moderate",
                "message": param_ref.get('interpretation', {}).get('high', 'Abundant nitrogen reserves; avoid excess inputs to prevent lodging or disease.'),
                "unit": unit
            }

    # 5. Phosphorus (P)
    elif param == 'phosphorus':
        if val < 11.0:
            return {
                "value": val,
                "status": "Low",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('low', 'Available phosphorus is low; early root growth and flowering may be delayed.'),
                "unit": unit
            }
        elif 11.0 <= val <= 25.0:
            return {
                "value": val,
                "status": "Medium / Adequate",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('normal', 'Phosphorus is adequate for strong root development and energy transfer.'),
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "High",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('high', 'Ample available phosphorus supporting reproductive vigor.'),
                "unit": unit
            }

    # 6. Potassium (K)
    elif param == 'potassium':
        if val < 140.0:
            return {
                "value": val,
                "status": "Low",
                "status_code": "warning",
                "message": param_ref.get('interpretation', {}).get('low', 'Available potassium is low; stress tolerance and fruit quality may suffer.'),
                "unit": unit
            }
        elif 140.0 <= val <= 280.0:
            return {
                "value": val,
                "status": "Medium / Adequate",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('normal', 'Adequate potassium providing stomatal regulation and lodging resistance.'),
                "unit": unit
            }
        else:
            return {
                "value": val,
                "status": "High",
                "status_code": "optimal",
                "message": param_ref.get('interpretation', {}).get('high', 'High potassium reserves supporting superior drought and disease tolerance.'),
                "unit": unit
            }

    return {
        "value": val,
        "status": "Evaluated",
        "status_code": "optimal",
        "message": "Measured value recorded.",
        "unit": unit
    }


def analyze_soil(soil_data: dict | None) -> dict:
    """
    Complete rule-based intelligence analysis on soil test parameters.
    Deterministic, transparent scoring and actionable observations.
    """
    ref_data = load_soil_reference()

    clean_soil = {
        'ph': safe_float(soil_data.get('ph')) if soil_data else None,
        'nitrogen': safe_float(soil_data.get('nitrogen')) if soil_data else None,
        'phosphorus': safe_float(soil_data.get('phosphorus')) if soil_data else None,
        'potassium': safe_float(soil_data.get('potassium')) if soil_data else None,
        'organic_carbon': safe_float(soil_data.get('organic_carbon')) if soil_data else None,
        'ec': safe_float(soil_data.get('ec')) if soil_data else None,
    }

    classified_params = {}
    strengths = []
    concerns = []
    priority_actions = []

    tested_points = []
    total_tested = 0

    for param_key in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']:
        val = clean_soil[param_key]
        eval_res = classify_parameter(param_key, val, ref_data)
        classified_params[param_key] = eval_res

        if val is None:
            continue

        total_tested += 1
        code = eval_res['status_code']

        # Points for transparent deterministic soil health score:
        # optimal = 100%, moderate = 70%, warning = 35%
        if code == 'optimal':
            tested_points.append(100.0)
            if param_key == 'ph':
                strengths.append(f"Optimal soil pH ({val}) supports balanced nutrient absorption.")
            elif param_key == 'ec':
                strengths.append(f"Non-saline Electrical Conductivity ({val} dS/m) ensures safe seedling emergence.")
            elif param_key == 'organic_carbon':
                strengths.append(f"Healthy Organic Carbon ({val}%) supports active soil biology.")
            elif param_key == 'nitrogen':
                strengths.append(f"Adequate Available Nitrogen ({val} kg/ha) supports vegetative vigor.")
            elif param_key == 'phosphorus':
                strengths.append(f"Good Phosphorus reserve ({val} kg/ha) ensures robust root branching.")
            elif param_key == 'potassium':
                strengths.append(f"Substantial Potassium level ({val} kg/ha) provides physiological disease tolerance.")
        elif code == 'moderate':
            tested_points.append(70.0)
            if param_key == 'ph':
                concerns.append(f"Soil pH ({val}) is {eval_res['status'].lower()}; monitor for minor micronutrient lockup.")
            elif param_key == 'ec':
                concerns.append(f"Critical EC level ({val} dS/m) suggests slight soluble salt concentration.")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Salinity & Irrigation Monitoring",
                    "guidance": "Monitor soil salinity and test irrigation water quality to prevent salt accumulation."
                })
            elif param_key == 'nitrogen':
                concerns.append(f"High Nitrogen ({val} kg/ha); avoid over-application of synthetic nitrogen.")
        elif code == 'warning':
            tested_points.append(35.0)
            if param_key == 'ph':
                concerns.append(f"Soil reaction is {eval_res['status'].lower()} ({val}).")
                priority_actions.append({
                    "priority": "HIGH",
                    "title": "Soil Reaction Conditioning",
                    "guidance": "Consult local agricultural extension for soil conditioning (liming for acid soils or gypsum for alkaline soils) based on official soil-test guidelines."
                })
            elif param_key == 'ec':
                concerns.append(f"Elevated soil salinity ({val} dS/m) threatens root water uptake.")
                priority_actions.append({
                    "priority": "HIGH",
                    "title": "Salinity Management & Leaching",
                    "guidance": "Ensure adequate field drainage and leach salts with good quality irrigation water prior to sensitive planting."
                })
            elif param_key == 'organic_carbon':
                concerns.append(f"Low Organic Carbon ({val}%) indicates depleted microbial activity.")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Organic Matter Enrichment",
                    "guidance": "Consider organic-matter management by incorporating well-decomposed farmyard manure, compost, or green manuring."
                })
            elif param_key == 'nitrogen':
                concerns.append(f"Available Nitrogen is low ({val} kg/ha).")
                priority_actions.append({
                    "priority": "HIGH",
                    "title": "Nitrogen Management Planning",
                    "guidance": "Consider an appropriate nutrient-management plan based on local soil-test recommendations to support initial crop vegetative growth."
                })
            elif param_key == 'phosphorus':
                concerns.append(f"Available Phosphorus is low ({val} kg/ha).")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Phosphorus Soil Replenishment",
                    "guidance": "Plan basal phosphorus application as per soil-test recommendations to foster healthy root architecture."
                })
            elif param_key == 'potassium':
                concerns.append(f"Available Potassium is low ({val} kg/ha).")
                priority_actions.append({
                    "priority": "MEDIUM",
                    "title": "Potassium Balance",
                    "guidance": "Incorporate potassium as per soil-test recommendations to enhance drought resilience and harvest quality."
                })

    # Add default general low-priority action if none or few
    if not priority_actions:
        priority_actions.append({
            "priority": "LOW",
            "title": "Routine Nutrient Maintenance",
            "guidance": "Maintain periodic soil testing and regular organic matter recycling to preserve balanced fertility."
        })
    else:
        priority_actions.append({
            "priority": "LOW",
            "title": "Local Agronomic Verification",
            "guidance": "Consult local agricultural extension officers or university specialists before applying commercial soil inputs."
        })

    # Sort actions: HIGH first, then MEDIUM, then LOW
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    priority_actions.sort(key=lambda x: priority_order.get(x["priority"], 3))

    # Calculate deterministic Soil Health Score
    if total_tested == 0:
        health_score = 0
        health_label = "No Data"
        explanation = "Soil parameters have not been tested or entered yet."
    else:
        health_score = int(round(sum(tested_points) / total_tested))
        if health_score >= 85:
            health_label = "Excellent"
            explanation = "Your soil exhibits high fertility, optimal nutrient reserves, and favorable chemical balance."
        elif health_score >= 70:
            health_label = "Good"
            explanation = "Your soil provides a healthy growing environment with only minor nutrient or organic matter adjustments needed."
        elif health_score >= 50:
            health_label = "Moderate"
            explanation = "Your soil has notable deficiencies or limitations that require targeted soil-management actions."
        else:
            health_label = "Needs Improvement"
            explanation = "Significant soil constraints detected (acidity/alkalinity, salinity, or severe nutrient depletion) requiring corrective care."

    return {
        "parameters": classified_params,
        "tested_count": total_tested,
        "missing_count": 6 - total_tested,
        "strengths": strengths,
        "concerns": concerns,
        "priority_actions": priority_actions,
        "soil_health": {
            "score": health_score,
            "label": health_label,
            "explanation": explanation
        }
    }
