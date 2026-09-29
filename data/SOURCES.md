# AgriAI Agricultural References & Methodology Documentation

This document describes the agronomic data sources, evaluation methodologies, and calculation models powering the AgriAI Soil & Crop Intelligence Engine.

---

## 1. Soil Reference Sources

The soil parameter interpretation criteria used in `data/soil_reference.json` are grounded in standard Indian agricultural reference guidelines established by:

1. **ICAR (Indian Council of Agricultural Research)**
   - *Handbook of Agriculture* (Soil Science and Plant Nutrition sections).
   - Operational Guidelines of the *National Soil Health Card Scheme* (Ministry of Agriculture & Farmers Welfare, Govt. of India).
2. **TNAU (Tamil Nadu Agricultural University)**
   - *Crop Production Guide (Agriculture & Horticulture)*, Department of Soil Science and Agricultural Chemistry.
   - Soil fertility rating charts for Tamil Nadu soils (Available N, P, K, OC, and EC).

### Benchmark Agricultural Nutrient Ranges:
- **Soil pH (1:2.5 soil-water suspension)**:
  - Strongly Acidic: < 5.5
  - Moderately Acidic: 5.5 – 6.49
  - Neutral / Optimal: 6.5 – 7.5
  - Moderately Alkaline: 7.51 – 8.49
  - Strongly Alkaline: ≥ 8.5
- **Available Nitrogen (N, Alkaline Permanganate Method)**:
  - Low: < 280 kg/ha (< 125 mg/kg)
  - Medium / Adequate: 280 – 560 kg/ha (125 – 250 mg/kg)
  - High: > 560 kg/ha (> 250 mg/kg)
- **Available Phosphorus (P, Olsen's Method for neutral/alkaline or Bray-1 for acid soils)**:
  - Low: < 11.0 kg/ha (< 5 mg/kg P)
  - Medium / Adequate: 11.0 – 25.0 kg/ha (5 – 11 mg/kg P)
  - High: > 25.0 kg/ha (> 11 mg/kg P)
- **Available Potassium (K, Neutral Normal Ammonium Acetate Method)**:
  - Low: < 140 kg/ha (< 62.5 mg/kg)
  - Medium / Adequate: 140 – 280 kg/ha (62.5 – 125 mg/kg)
  - High: > 280 kg/ha (> 125 mg/kg)
- **Organic Carbon (OC, Walkley-Black Wet Oxidation Method)**:
  - Low: < 0.50 %
  - Medium: 0.50 – 0.75 %
  - High: > 0.75 %
- **Electrical Conductivity (EC, 1:2 or 1:2.5 soil-water extract)**:
  - Normal / Non-saline: ≤ 1.0 dS/m
  - Critical / Slightly Saline: 1.01 – 2.0 dS/m
  - Injurious / Saline: > 2.0 dS/m

---

## 2. Soil Health Scoring Methodology

The Soil Health Index is a **transparent, deterministic, non-blackbox scoring model** ranging from 0 to 100:

1. **Parameter Weighting**:
   - Each of the 6 evaluated soil parameters contributes equally to a baseline score (up to 16.67 points each, summing to 100 max).
2. **Deterministic Grading per Parameter**:
   - **Optimal / Safe range**: 100% of parameter weight (e.g. Neutral pH, Normal EC, High or Adequate OC, Adequate or High N/P/K).
   - **Moderate / Slight deviation**: 65% of parameter weight (e.g. Moderately acidic or alkaline pH, Medium OC, Low N/P/K without extreme depletion, Mild EC).
   - **Critical / Severe limitation**: 30% of parameter weight (e.g. Strongly acidic/alkaline pH, Severe Salinity EC > 2.0, Depleted OC < 0.30%).
   - **Missing parameters**: Evaluated based on available parameters without penalizing the farmer unfairly for laboratory test gaps.
3. **Qualitative Classification**:
   - **Score 85 – 100**: *Excellent* — Fertile, balanced soil environment.
   - **Score 70 – 84**: *Good* — Healthy foundation with minor optimization opportunities.
   - **Score 50 – 69**: *Moderate* — Several nutrients or physical traits require active management.
   - **Score < 50**: *Needs Improvement* — Significant constraints (e.g. severe salinity, severe acidity/alkalinity, or multi-nutrient deficiency).

---

## 3. Crop Suitability Evaluation Methodology

Crop suitability cross-references the farm's soil profile with the specific physiological tolerances of the selected crop defined in `data/crops.json`:

1. **Soil pH Concordance**:
   - Checks whether the measured pH falls within the crop's `preferred_ph` boundaries (e.g., Moringa 6.5–8.0; Paddy 5.5–7.0).
   - Deviation > 0.8 units triggers a caution or constraint.
2. **Salinity Tolerance**:
   - Compares soil EC with crop salinity sensitivity (e.g. Paddy and Tomato are sensitive to EC > 1.5 dS/m; Moringa and Cotton tolerate moderate salinity).
3. **Organic Carbon & Biological Vitality**:
   - Evaluates moisture buffering and biological resilience.
4. **Macronutrient Reserve**:
   - Reviews N, P, and K availability relative to the crop's nutrient demand.
5. **Multi-Factor Status Assignment**:
   - **Highly Suitable**: All soil parameters align with the crop's preferred conditions.
   - **Suitable**: Soil is broadly favorable with 1–2 minor deficiencies that are easily managed.
   - **Needs Attention**: 1 critical parameter (e.g. pH mismatch or severe nitrogen deficit) requires corrective management.
   - **Not Recommended**: Multiple severe mismatches (e.g. high salinity for a sensitive crop combined with extreme pH).

---

## 4. Priority Action System

- **HIGH**: A parameter directly threatens crop establishment or causes toxicity/osmotic shock (e.g., pH < 5.0 or > 8.8, EC > 2.5 dS/m, severe N deficit).
- **MEDIUM**: Important nutrient or organic matter adjustment that improves seasonal yield and prevents deficiency symptoms.
- **LOW**: Maintenance practice, routine biological enrichment, or seasonal monitoring.

---

## 5. Scope & Agricultural Decision-Support Disclaimer

> [!IMPORTANT]
> AgriAI is designed as an educational and preliminary agricultural decision-support tool. It does **not** prescribe quantitative chemical fertilizer or pesticide dosages. Actual field recommendations depend on micro-climate, soil depth, irrigation water quality, crop variety/hybrid, and seasonal weather patterns. Farmers must consult qualified agricultural extension officers or university farm science centers (KVK) before applying commercial inputs.

---

## 6. BioBoost Biological Soil & Nutrient Management Sources

The biological soil health and nutrient management practices in `data/bioboost.json` and `engine/bioboost_engine.py` are compiled from established agricultural university extension manuals and research guidelines:

1. **ICAR - Indian Institute of Soil Science (IISS), Bhopal**
   - *Biofertilizers and Organic Farming Technology Guidelines*.
   - Research bulletins on microbial inoculation (Azospirillum, Bradyrhizobium, PSB, and VAM/Mycorrhiza).
2. **TNAU (Tamil Nadu Agricultural University)**
   - *Organic Agriculture & Biofertilizer Production Protocols*, Department of Agricultural Microbiology.
   - Stage-specific biological recommendations for South Indian cropping systems (Paddy, Moringa, Groundnut, Tomato, Cotton, Banana, Chilli, Maize).
3. **Ministry of Agriculture & Farmers Welfare, Govt. of India**
   - National Project on Organic Farming (NPOF) standard operational procedures for on-farm compost preparation, green manuring, and biological pest/pathogen antagonists (Trichoderma, Pseudomonas).

### Clear Distinction of Roles:
- **Documented Agricultural Facts**: The biological mechanisms (e.g. atmospheric nitrogen fixation by Azospirillum, biological phosphorus solubilization by PSB, root surface expansion by VAM) are universally established agronomic science.
- **AgriAI Rule-Based Decision Support**: AgriAI applies deterministic logic to map measured soil conditions (such as low Organic Carbon, suboptimal pH, or nutrient deficiencies) to appropriate biological management opportunities, without prescribing proprietary brand products or unverified chemical dosages.

---

## 7. Integrated Pest Management (IPM) Sources & Decision-Support Methodology

The pest and disease diagnostics, symptom descriptions, economic thresholds, and hierarchical IPM action plans in `data/ipm.json` and `engine/ipm_engine.py` are grounded in official Indian agricultural extension guidelines:

1. **ICAR - National Research Centre for Integrated Pest Management (NCIPM), New Delhi**
   - *Crop-Specific Integrated Pest Management (IPM) Packages* (Paddy, Cotton, Maize, Groundnut, Tomato, Chilli, Banana, and Moringa).
   - Standard Economic Threshold Levels (ETL) and field scouting protocols.
2. **TNAU (Tamil Nadu Agricultural University) Agritech Portal**
   - *Crop Protection Guidelines* (Agricultural Entomology and Plant Pathology divisions).
   - Bio-control protocols: release rates for Trichogramma, pheromone trap deployment standards, and entomopathogenic formulations (Beauveria bassiana, Metarhizium anisopliae, Lecanicillium lecanii).
3. **Directorate of Plant Protection, Quarantine & Storage (DPPQ&S), Govt. of India**
   - Central Integrated Pest Management Centers (CIPMCs) Standard Operating Procedures.
   - Central Insecticides Board & Registration Committee (CIBRC) approved registered active ingredients for target pest-crop complexes.

### Chemical-Control Safeguards:
- **Zero Invented Dosages**: AgriAI strictly refrains from generating arbitrary quantitative dosages (e.g., grams or milliliters per liter of water), spray schedules, or proprietary commercial brand endorsements.
- **Active Ingredient & Category Basis**: Where chemical intervention is officially recognized as a secondary or emergency option, AgriAI presents only approved active ingredients (e.g., Azadirachtin, Spinosad, Mancozeb, Copper oxychloride) and their target stages.
- **Threshold-Driven Consideration**: Chemical controls are only presented as conditional options when damage or pest counts cross economic thresholds and non-chemical methods are inadequate.
- **Mandatory Label Adherence**: All chemical references state: *"Follow the current locally approved label and agricultural extension recommendation."*

### Diagnostic Uncertainty & Field Limitations:
- **Symptom-Based Preliminary Guidance**: Foliar yellowing, wilting, curling, and stunting can result from multiple overlapping causes, including viral pathogens, bacterial vascular infections, micronutrient deficiencies (e.g. zinc/iron chlorosis), root-knot nematodes, or soil moisture stress.
- **Diagnostic Caution ("Not sure")**: When the farmer selects "Not sure", AgriAI deliberately refuses to generate a confident diagnosis, instead triggering a cautionary notice advising field sample testing with local extension officers before applying any input.
- **Local Confirmation**: All pest and disease assessments are explicitly labeled as decision-support guidance that requires confirmation by local Assistant Agricultural Officers (AAO) or Krishi Vigyan Kendra (KVK) farm science specialists.

---

## 8. Weather & Farm Forecast Data Sources & Agronomic Methodology

The real-time meteorological conditions, 7-day farm forecasts, and conservative agricultural interpretations in `engine/weather_service.py`, `engine/weather_engine.py`, and `templates/weather.html` utilize open meteorological modeling data and established agricultural meteorology principles:

### 1. Primary Weather API: Open-Meteo
- **Provider**: Open-Meteo (open-meteo.com), providing open-access weather forecasts derived from national weather services (including DWD ICON, NOAA GFS, ECMWF IFS, and Météo-France models).
- **Public Endpoints Used**:
  - **Geocoding API**: `https://geocoding-api.open-meteo.com/v1/search`
    - Resolves farmer's geographic location (Village, District, State) into decimal latitude and longitude coordinates.
    - Fallback cascading resolution strategy: `[village, district, state]` → `[district, state]` → `[district]` → `[state]` ensures localized coordination even when small hamlets are unlisted in international gazetteers.
  - **Forecast API**: `https://api.open-meteo.com/v1/forecast`
    - High-resolution atmospheric forecast queried with parameter metric units: temperature in Celsius (°C), precipitation in millimeters (mm), and wind speed in kilometers per hour (km/h) at standard 10m height. Timezone is resolved automatically (`timezone=auto`).

### 2. Meteorological Variables Retrieved & Normalized:
- **Current Observation**:
  - `temperature_2m`: Air temperature at 2 meters above ground (°C).
  - `relative_humidity_2m`: Relative humidity percentage (%).
  - `precipitation`: Current precipitation accumulation (mm).
  - `wind_speed_10m`: Wind speed at 10 meters above ground (km/h).
  - `weather_code`: WMO (World Meteorological Organization) standard weather interpretation code (0–99).
- **7-Day Daily Forecast**:
  - `weather_code`: Daily dominant WMO weather code mapped to clear human-readable weather descriptions and iconography.
  - `temperature_2m_max` & `temperature_2m_min`: Daily maximum and minimum ambient temperatures (°C).
  - `precipitation_sum`: Predicted cumulative daily precipitation (mm).
  - `precipitation_probability_max`: Probability of precipitation occurrence (%).
  - `sunrise` & `sunset`: Solar day duration timestamps.

### 3. Caching & Performance Architecture:
- **In-Memory Cache TTL**: Weather data is cached in-memory with a 15-minute Time-To-Live (TTL) keyed by geographic coordinates `(latitude, longitude)`.
- **Farmer Transparency**: Templates display whether data is freshly retrieved or cached, showing `"Updated X minutes ago"` to prevent unnecessary API hammering on page refreshes while keeping the farmer informed of data recency.
- **Fail-Safe / Zero-Hardcoding**: If the external weather service is unreachable or network calls timeout (5-second threshold), the application displays `"Weather data is temporarily unavailable"`. AgriAI strictly prohibits injecting fake, simulated, or hard-coded meteorological numbers when the API is down.

### 4. Conservative Rule-Based Agricultural Interpretation:
- **Farm Weather Insights**: Rule-based observations translate raw numerical thresholds into practical field operational notes (e.g., assessing precipitation probabilities against surface drainage needs; evaluating temperature peaks against plant transpiration and field labor safety; flagging winds >20 km/h to prevent foliar bio-spray drift).
- **Weather Alerts**: Strictly justified alerts triggered only when forecast thresholds are crossed:
  - `RAIN`: Elevated rain probability (≥65% or cumulative rain ≥20 mm) — advises checking drainage bunds and postponing broadcast fertilization.
  - `HEAT`: High daytime peak (≥37°C) — advises soil mulching and shifting irrigation to early morning/evening.
  - `WIND`: Gusty airflow (≥25 km/h) — advises checking tree/crop support stakes and suspending spraying.
  - `DRY CONDITIONS`: Negligible rain, low probability (<20%), and daytime highs ≥33°C — advises root-zone moisture inspection.
- **Crop-Weather Water Context**: If a crop is active in the session, its documented water requirement category (Low/Medium/High) is placed in context with the 7-day cumulative rainfall and thermal forecast.

### 5. Weather Interpretation Limitations:
- **Numerical Weather Model Resolution**: Open-Meteo forecasts are based on global and regional numerical weather models; actual micro-climates, valley fog, or localized convective thundershowers can vary from model grid points.
- **No Direct Chemical Prescription**: Weather interpretations do not recommend chemical fungicide or insecticide sprays solely based on atmospheric readings without scouting for actual pest thresholds.

### 6. Transition to Official Monsoon Outlook:
- Initial weather placeholders for the seasonal monsoon transition to the full official module in Section 9.

---

## 9. Monsoon Outlook Data Sources & Agronomic Methodology

The seasonal monsoon intelligence, regional meteorological subdivision classifications, and agricultural decision-support guidance in `engine/monsoon_service.py`, `engine/monsoon_engine.py`, and `templates/monsoon.html` are strictly grounded in official publications from the national meteorological authority of India:

### 1. Authoritative Official Source: India Meteorological Department (IMD)
- **Designation**: India Meteorological Department (IMD), Ministry of Earth Sciences, Government of India.
- **Official Portal**: `https://mausam.imd.gov.in/`
- **Monsoon Bulletins Portal**: `https://mausam.imd.gov.in/responsive/monsoonbulletin.php`
- **Mandate**: Under the Government of India Allocation of Business Rules, IMD is the sole constitutionally authorized statutory agency for issuing official weather forecasts, seasonal monsoon projections, and cyclone/severe weather warnings across the Indian subcontinent.

### 2. Retrieval, Normalization & Publication Handling
- **Retrieval Architecture**:
  - `engine/monsoon_service.py` retrieves verified official seasonal monsoon outlook bulletins published by the National Weather Forecasting Centre (IMD New Delhi) and Regional Meteorological Centres (e.g., RMC Chennai for South Peninsular India).
  - Normalizes official data into structured metadata containing: issuing office, official bulletin ID, seasonal cycle (Southwest Monsoon vs. Northeast Monsoon), publication date, All-India seasonal summary, and regional meteorological subdivision classifications.
- **Seasonality & Subdivisions**:
  - Resolves seasonal relevance dynamically: Southwest Monsoon (June – September) for national summer cultivation (Kharif) and Northeast / Post-Monsoon (October – December) for South Peninsular India (Tamil Nadu, Kerala, Coastal Andhra Pradesh, Rayalaseema, South Interior Karnataka).
  - Subdivision mapping: Matches the farmer's state (e.g. Tamil Nadu, Puducherry & Karaikal) to its official meteorological subdivision without interpolating or fabricating micro-level statistics.
- **Cache Management**:
  - In-memory caching (`_MONSOON_CACHE`) with a 30-minute TTL avoids redundant disk reads and network calls.

### 3. Clear Distinction: Official IMD Information vs. AgriAI Agricultural Interpretation
To safeguard scientific integrity and prevent farmer confusion, AgriAI enforces a strict visual and functional separation:
- **Official IMD Information**:
  - Clearly designated with dedicated styling, national authority badging, official issuance headers, and direct links to `https://mausam.imd.gov.in/`.
  - Content consists strictly of verbatim official summary text and verified category assessments (e.g. "Normal to Above Normal").
  - **Zero Fabrication**: AgriAI never invents or simulates monsoon rainfall percentages, onset dates, withdrawal dates, seasonal rainfall anomalies, or synthetic district rainfall forecasts.
- **AgriAI Farm Interpretation**:
  - Clearly designated as conservative agricultural decision support ("What This Means for Farmers").
  - Translates broad seasonal outlook trends into practical agronomic safeguards:
    1. *Rainfall Monitoring*: Tracking 7-day cumulative precipitation and local rain gauge records against field water infiltration capacity.
    2. *Irrigation Planning*: Delaying scheduled flood or tube-well irrigation when active seasonal pulses are active; conserving farm pond reserves.
    3. *Soil Moisture Consistency*: Checking root-zone (15–30 cm) moisture depth before applying basal fertilizers or biofertilizers.
    4. *Field Drainage Awareness*: Clearing farm boundary furrows, bund spillways, and surplus channels to mitigate localized waterlogging from heavy convective rains.
    5. *Crop-Stage Planning*: Reviewing growth-stage moisture sensitivity to prevent nutrient leaching during intense rainfall bouts.
  - *Farmer Monitoring Checklist*: Actionable reminders (monitoring district agromet bulletins, root-zone moisture, dry spell detection, heavy-rain checks, and growth stage review).

### 4. Integration with Short-Term Weather and Selected Crop
- **Weather Connection**:
  - Current atmospheric readings from Step 7 (temperature, current rainfall, rain probability, and 7-day total rainfall) are displayed alongside the monsoon outlook.
  - An explicit distinction notice is enforced: *"Current weather is separate from the seasonal monsoon outlook. Short-term forecast reflects 7-day atmospheric observations; seasonal monsoon outlook represents broad climatological trends."*
  - The system never combines short-term weather and seasonal monsoon forecasts into a single artificial index.
- **Crop Context**:
  - If a crop is selected (e.g., Moringa, Paddy, Tomato, Groundnut, Cotton, Banana, Chilli, Maize), the system provides general agronomic alignment based on its established water requirement category.
  - Explicit disclaimer: *"Use the seasonal outlook together with crop growth stage, soil moisture and local extension guidance. AgriAI does not invent crop-specific monsoon thresholds."*

### 5. Error Handling & Graceful Degradation
- If official IMD bulletins cannot be retrieved or verified, the module transitions gracefully to an unavailable state:
  - Displays: `"Official IMD monsoon information is currently unavailable."`
  - Provides a direct clickable link to the official IMD portal (`https://mausam.imd.gov.in/`).
  - Ensures the rest of the AgriAI application remains 100% operational without injecting synthetic or hard-coded fallback values.

### 6. Limitations
- **Spatial Resolution**: Official Long Range Forecasts (LRF) describe broad meteorological subdivisions and national trends; they do not predict day-by-day village-level precipitation events months in advance.
- **Local Validation Required**: Sowing and harvesting timing must always be corroborated with bi-weekly district Agromet Advisory Services (GKMS) bulletins and local block-level agricultural extension officers (AAO / KVK).

---

## 10. Crop Guide & Farmer PDF Report Sources and Synthesis Methodology

The Crop Guide and downloadable Farmer PDF Report (`engine/report_generator.py`, `templates/crop_guide.html`, and `/generate-report`) synthesize the multi-pillar intelligence developed across Steps 1 through 8 into a single, cohesive, printable agronomic dossier:

### 1. Documented Source Lineage Across Steps 1–8:
1. **Crop Knowledge Profiles & Growth Stages (Steps 3 & 4)**:
   - *Sources*: ICAR Handbook of Agriculture, TNAU Agritech Portal Crop Production Guides (Horticulture & Agriculture divisions).
   - *Parameters*: Botanical identification, growth duration, water requirement category, optimal soil texture, and preferred pH range.
   - *Strict Missing-Data Rule*: If specific growth duration or pH metrics are absent from `data/crops.json`, AgriAI states *"Information not available in the current AgriAI knowledge base"* rather than inventing unverified values.
2. **Soil Laboratory & Fertility Ratings (Steps 1, 2 & 4)**:
   - *Sources*: ICAR National Soil Health Card operational guidelines and TNAU Soil Science fertility rating benchmarks for pH, Available N (alkaline permanganate), Available P (Olsen/Bray), Available K (neutral ammonium acetate), Walkley-Black Organic Carbon, and Electrical Conductivity.
   - *Safety*: Reports only measured laboratory numbers; missing parameters are left unpenalized and clearly flagged as unmeasured.
3. **BioBoost Biological Nutrient Management (Step 5)**:
   - *Sources*: ICAR-Indian Institute of Soil Science (IISS, Bhopal) and TNAU Agricultural Microbiology biofertilizer protocols (Azospirillum, PSB, VAM/Mycorrhiza, Rhizobium, enriched farmyard manure).
4. **Integrated Pest Management (IPM) Diagnostics & Action Plans (Step 6)**:
   - *Sources*: ICAR-National Research Centre for Integrated Pest Management (NCIPM, New Delhi) and Directorate of Plant Protection, Quarantine & Storage (DPPQ&S, Govt. of India).
   - *Chemical Safety*: Strictly active ingredient-based with no invented spray schedules, commercial trade names, or arbitrary dosages.
5. **Short-Term Weather Observations & 7-Day Forecasts (Step 7)**:
   - *Sources*: Open-Meteo atmospheric forecast models (DWD ICON, NOAA GFS, ECMWF) under WMO Code Table 4677 standards.
6. **Seasonal Monsoon Outlook (Step 8)**:
   - *Sources*: India Meteorological Department (IMD), Ministry of Earth Sciences, Govt. of India (`https://mausam.imd.gov.in/`).

### 2. PDF Architectural & Synthesis Guidelines:
- **No Artificial Recalculation**: The report generator does not create secondary scores, divergent recommendations, or invented dosages. It gathers the exact outputs generated by the verified engine modules.
- **Graceful Partial-Data Handling**: Every section handles missing sessions without crashing:
  - Missing soil data displays: *"Not available — complete Soil Lab analysis to populate this section."*
  - Missing crop selection displays: *"No crop selected. Complete Crop Advisor to populate this section with crop-specific management guidance."*
  - Missing BioBoost displays: *"Not available — complete BioBoost module to include organic microbial and biofertilizer practices."*
  - Missing IPM displays: *"Not available — explore Pest & Disease Advisor to include crop-specific IPM safeguards."*
  - Unavailable weather displays: *"Weather data is temporarily unavailable. Check internet connectivity to refresh live meteorological observations."*
  - Unavailable IMD monsoon displays: *"Official IMD monsoon information is currently unavailable. Source: India Meteorological Department (IMD)."*
- **Advisory Role**: The report concludes with the standard non-commercial agricultural advisory disclaimer reminding farmers to verify field decisions with local Assistant Agricultural Officers (AAO) or Krishi Vigyan Kendra (KVK) farm scientists.

