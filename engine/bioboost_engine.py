"""
AgriAI - BioBoost Intelligence Engine
Generates biological soil health assessments, organic matter guidance,
microbial practices, and stage-specific monitoring checklists based on
ICAR, TNAU, and NPOF biological agriculture standards.
"""

import os
import json
from engine.soil_engine import analyze_soil, safe_float
from engine.crop_engine import get_crop_profile

BIOBOOST_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'bioboost.json')

_BIOBOOST_CACHE = None


def load_bioboost_data() -> dict:
    """Load bioboost crop data from data/bioboost.json with caching."""
    global _BIOBOOST_CACHE
    if _BIOBOOST_CACHE is not None:
        return _BIOBOOST_CACHE

    if not os.path.exists(BIOBOOST_FILE):
        return {}

    try:
        with open(BIOBOOST_FILE, 'r', encoding='utf-8') as f:
            _BIOBOOST_CACHE = json.load(f)
            return _BIOBOOST_CACHE
    except Exception:
        return {}


def evaluate_biological_health(soil_analysis: dict) -> dict:
    """
    Evaluates soil biological health using available soil parameters.
    Transparently states that Organic Carbon is an indicator, not a complete measurement.
    """
    params = soil_analysis.get('parameters', {})
    oc_val = params.get('organic_carbon', {}).get('value')
    ph_val = params.get('ph', {}).get('value')
    ec_val = params.get('ec', {}).get('value')

    observations = []
    
    # Mandatory scientific nuance
    observations.append(
        "Organic carbon is an important indicator related to soil organic matter and biological activity, "
        "but it does not provide a complete measurement of soil microbial health."
    )

    status = "Active & Responsive"
    status_code = "optimal"

    # Organic carbon evaluation
    if oc_val is not None:
        if oc_val >= 0.75:
            observations.append(f"Favorable organic carbon ({oc_val}%) provides sustained energy substrates for beneficial mycorrhiza and rhizobacteria.")
        elif 0.50 <= oc_val < 0.75:
            observations.append(f"Moderate organic carbon ({oc_val}%) maintains standard microbial respiration; periodic organic additions will enhance biological buffer.")
        else:
            status = "Carbon-Depleted"
            status_code = "warning"
            observations.append(f"Low organic carbon ({oc_val}%) indicates restricted biological reserves, reducing microbial biomass and nutrient-cycling efficiency.")
    else:
        observations.append("Organic carbon was not reported; biological assessment is estimated from chemical balance.")

    # pH impact on biology
    if ph_val is not None:
        if ph_val < 5.5:
            status = "Constrained by Acidity"
            status_code = "warning"
            observations.append(f"Strong soil acidity (pH {ph_val}) inhibits beneficial bacteria (e.g. Azotobacter and Rhizobium) and favors fungal dominance.")
        elif ph_val > 8.2:
            status = "Constrained by Alkalinity"
            status_code = "warning"
            observations.append(f"Alkaline reaction (pH {ph_val}) reduces the biological availability of phosphorus and micronutrients like zinc and iron.")
        else:
            observations.append(f"Neutral to near-neutral pH ({ph_val}) creates an optimal rhizosphere environment for diverse beneficial microorganisms.")

    # Salinity impact on biology
    if ec_val is not None:
        if ec_val > 2.0:
            status = "Constrained by Salinity"
            status_code = "warning"
            observations.append(f"Elevated soil salinity (EC {ec_val} dS/m) imposes osmotic stress on soil microbes and plant roots.")
        elif ec_val > 1.0:
            observations.append(f"Slight salinity (EC {ec_val} dS/m) detected; monitor irrigation water to safeguard sensitive biological inoculants.")

    return {
        "status": status,
        "status_code": status_code,
        "observations": observations
    }


def generate_bioboost_guidance(crop_name: str, growth_stage: str | None, soil_data: dict | None, location: dict | None = None, intelligence: dict | None = None) -> dict:
    """
    Main BioBoost engine entrypoint:
    Combines soil parameters, selected crop, growth stage, and Step 4 intelligence
    to produce prioritized biological soil management advice.
    """
    bio_db = load_bioboost_data()
    crop_bio = bio_db.get(crop_name)
    crop_profile = get_crop_profile(crop_name)

    # If crop is not in BioBoost DB, fallback to generic or first
    if not crop_bio and bio_db:
        # Try case-insensitive lookup
        for k, v in bio_db.items():
            if k.lower() == crop_name.lower():
                crop_bio = v
                break
        if not crop_bio:
            crop_bio = list(bio_db.values())[0]

    # Run or retrieve soil analysis
    if intelligence and intelligence.get('soil_analysis'):
        soil_analysis = intelligence['soil_analysis']
    else:
        soil_analysis = analyze_soil(soil_data)

    bio_health = evaluate_biological_health(soil_analysis)

    params = soil_analysis.get('parameters', {})
    oc_val = params.get('organic_carbon', {}).get('value')
    ph_val = params.get('ph', {}).get('value')
    ec_val = params.get('ec', {}).get('value')
    n_val = params.get('nitrogen', {}).get('value')
    p_val = params.get('phosphorus', {}).get('value')
    k_val = params.get('potassium', {}).get('value')

    priorities = []

    # Priority Evaluation Logic
    # HIGH PRIORITIES: Severe constraints threatening biological and plant functions
    if ph_val is not None and (ph_val < 5.5 or ph_val > 8.3):
        priorities.append({
            "priority": "HIGH",
            "title": "Soil Reaction Conditioning for Microbial Survival",
            "reason": f"Measured pH of {ph_val} severely restricts beneficial bacterial populations and locks up soil nutrients.",
            "action": "Consult local agricultural extension for soil conditioning (liming for acid soils or gypsum for alkaline soils) before applying sensitive bio-inoculants."
        })

    if ec_val is not None and ec_val > 2.0:
        priorities.append({
            "priority": "HIGH",
            "title": "Salinity Flushing & Root Zone Leaching",
            "reason": f"High salinity (EC {ec_val} dS/m) generates osmotic stress that suppresses beneficial root colonization.",
            "action": "Ensure active drainage channels and leach excess salts with good-quality irrigation water prior to biofertilizer application."
        })

    if n_val is not None and n_val < 240.0:
        priorities.append({
            "priority": "HIGH",
            "title": "Biological Nitrogen Supplementation",
            "reason": f"Available nitrogen is low ({n_val} kg/ha), requiring biological fixation support alongside standard basal nutrients.",
            "action": "Incorporate nitrogen-fixing bio-inoculants (Azospirillum / Azotobacter / Rhizobium for legumes) blended with organic compost into the root zone."
        })

    # MEDIUM PRIORITIES: Organic matter enrichment, P/K mobilization, moisture management
    if oc_val is not None and oc_val < 0.50:
        priorities.append({
            "priority": "MEDIUM",
            "title": "Organic Matter & Compost Enrichment",
            "reason": f"Soil Organic Carbon ({oc_val}%) is low, limiting microbial energy substrates and moisture buffering.",
            "action": "Incorporate well-cured farmyard manure (FYM), vermicompost, or green manure (Dhaincha/Sunnhemp) to replenish active carbon reserves."
        })

    if p_val is not None and p_val < 15.0:
        priorities.append({
            "priority": "MEDIUM",
            "title": "Phosphate Solubilizing Microbial Application",
            "reason": f"Available Phosphorus is low ({p_val} kg/ha); native soil phosphorus requires microbial solubilization.",
            "action": "Apply Phosphate Solubilizing Bacteria (PSB) with organic compost around root zones to convert insoluble phosphates into plant-available orthophosphates."
        })

    if k_val is not None and k_val < 160.0:
        priorities.append({
            "priority": "MEDIUM",
            "title": "Potassium Mobilizing Bio-amendments & Mulch",
            "reason": f"Available Potassium is low ({k_val} kg/ha), which can affect moisture regulation and disease resistance.",
            "action": "Utilize potash-mobilizing bacteria (KMB) and retain biomass mulch around plant basins to recycle potassium naturally."
        })

    # Growth stage specific priority
    active_stage = growth_stage or (crop_profile.get('growth_stages', ['Vegetative Growth'])[0] if crop_profile else 'Vegetative Growth')
    priorities.append({
        "priority": "LOW",
        "title": f"Growth-Stage Biological Care ({active_stage})",
        "reason": f"During {active_stage}, root metabolic demand requires steady moisture and active aerobic biological respiration.",
        "action": "Maintain soil moisture without waterlogging and inspect root zone health and foliage vigor periodically."
    })

    # General baseline action
    priorities.append({
        "priority": "LOW",
        "title": "Biological Monitoring & Agronomic Verification",
        "reason": "BioBoost offers educational decision support based on benchmark soil guidelines.",
        "action": "Consult a qualified agricultural extension officer or university farm science center (KVK) to confirm specific biological formulations for your area."
    })

    # Sort priorities (HIGH -> MEDIUM -> LOW)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    priorities.sort(key=lambda x: priority_order.get(x["priority"], 3))

    # Relevant biological practices from database
    practices = crop_bio.get('biological_practices', []) if crop_bio else []
    monitoring = crop_bio.get('monitoring_indicators', []) if crop_bio else [
        "Soil moisture consistency in the root zone",
        "Crop canopy vigor and uniform leaf coloration",
        "Absence of waterlogging or surface crusting",
        "Root branching and nodule/mycorrhizal health"
    ]

    loc_dict = location or {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}

    return {
        "crop": crop_name,
        "crop_profile": crop_profile,
        "stage": active_stage,
        "growth_stage": active_stage,
        "location": loc_dict,
        "soil_data": soil_data or {},
        "biological_health": bio_health,
        "priorities": priorities,
        "practices": practices,
        "monitoring": monitoring,
        "disclaimer": "BioBoost provides preliminary decision-support guidance based on available soil, crop and growth-stage information. Application methods and input selection should follow local agricultural recommendations and product labels where applicable."
    }
