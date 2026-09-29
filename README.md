# AgriAI: Smart Agriculture Intelligence Platform

AgriAI is a comprehensive, production-grade agricultural decision-support platform designed for Indian farmers, agronomists, and farm advisors. It consolidates soil fertility diagnostics, crop suitability analysis, biological nutrient management (BioBoost), Integrated Pest Management (IPM), hyperlocal weather forecasting, authoritative IMD monsoon outlooks, and multi-page personalized PDF advisory reports into a unified command center.

---

## 1. Project Overview
AgriAI bridges the gap between laboratory soil test reports, meteorological intelligence, and practical field-level agronomic decisions. Rather than presenting fragmented tools, AgriAI provides a cohesive, end-to-end workflow where a farmer's location, soil parameters, and crop choice persist across every module, culminating in actionable decision support and exportable advisory documentation.

---

## 2. Problem Statement
Smallholder and commercial farmers face critical operational challenges:
- **Opaque Soil Reports:** Standard Soil Health Cards provide laboratory numbers (N-P-K, pH, EC, OC) without contextualizing what they mean for specific target crops.
- **Over-Reliance on Chemical Inputs:** Farmers often lack reliable guidance on biological alternatives, biofertilizers, and organic soil amendments.
- **Reactive Pest Management:** Chemical pesticides are frequently applied unnecessarily or at incorrect stages, increasing input costs and pest resistance risks.
- **Fragmented Meteorological Data:** General weather forecasts fail to connect day-to-day rainfall predictions with immediate field actions such as sowing, spraying, and irrigation.
- **Lack of Archival Records:** Farmers rarely have a centralized history of their soil tests, pest scouting events, and seasonal advisory reports.

---

## 3. Key Features
- **Automated Soil Lab Extraction:** Extracts 6 standard parameters (pH, EC, Organic Carbon, Nitrogen, Phosphorus, Potassium) from Soil Health Card PDFs using PyMuPDF regex pattern recognition, with manual input/correction fallback.
- **Crop Suitability & Intelligence Engine:** Evaluates selected crops against soil test parameters and regional agronomic thresholds, calculating compatibility scores, limiting factors, and priority corrective actions.
- **BioBoost Biological Nutrient Management:** Generates non-chemical biological management plans, biofertilizer inoculants (Rhizobium, Azospirillum, PSB, KMB), and organic amendment schedules matched to crop growth stages.
- **Integrated Pest Management (IPM) Advisor:** Follows the standard IPM hierarchy (Prevent -> Cultural -> Mechanical/Biological -> Threshold-based Chemical as last resort) for major crop pests and diseases.
- **Hyperlocal 7-Day Farm Forecast:** Integrates real-time Open-Meteo weather data (temperature, humidity, wind, 7-day rainfall probability) paired with conservative farm management rules.
- **Official IMD Monsoon Outlook:** Direct integration with India Meteorological Department (IMD) seasonal bulletins for post-monsoon and southwest monsoon periods over peninsular subdivisions.
- **Comprehensive Crop Guide Library:** Structured growth stage timelines, optimal soil requirements, water requirements, and harvesting windows across 8 core Indian crops.
- **Personalized Multi-Page Farm Report (PDF):** Generates downloadable, publication-ready PDF reports via ReportLab, synthesizing all active module findings into one cohesive document.
- **Farmer Activity & History System:** Lightweight SQLite event store tracking soil tests, crop evaluations, pest scouting, and report generations with search, filtering, and de-duplication.

---

## 4. Architecture
AgriAI is built with a clean, decoupled modular architecture:
```
                 ┌──────────────────────────────────────┐
                 │       Flask Web Application          │
                 │   (app.py - Routing & Session Mgmt)  │
                 └──────────────────┬───────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐           ┌──────────────────┐         ┌─────────────────┐
│ Soil Lab     │           │  Agronomic Core  │         │ Weather/Monsoon │
├──────────────┤           ├──────────────────┤         ├─────────────────┤
│soil_extractor│           │crop_engine       │         │weather_service  │
│soil_engine   │           │bioboost_engine   │         │weather_engine   │
└──────────────┘           │ipm_engine        │         │monsoon_service  │
                           └──────────────────┘         │monsoon_engine   │
                                                        └─────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
        ┌──────────────────┐                ┌──────────────────┐
        │ History Manager  │                │ Report Generator │
        ├──────────────────┤                ├──────────────────┤
        │history_manager.py│                │report_generator  │
        │ SQLite (history) │                │ ReportLab PDF    │
        └──────────────────┘                └──────────────────┘
```

---

## 5. Technology Stack
- **Backend Core:** Python 3.10+ & Flask 3.0.0
- **Session Layer:** Server-Side File-Based Session Interface (bypasses 4KB browser cookie limit for rich agronomic payloads)
- **PDF Extraction Engine:** PyMuPDF (`fitz`) 1.24+
- **PDF Generation Engine:** ReportLab 4.0+
- **Persistence Layer:** SQLite 3 (Built-in standard library)
- **External Meteorological API:** Open-Meteo Public Weather API (via `requests`)
- **Frontend / Styling:** Semantic HTML5, Vanilla CSS3 (Custom Design System with CSS variables, Glassmorphism cards, responsive flex/grid layouts)
- **Testing:** Python `unittest` framework (72 test assertions across unit, integration, and regression suites)

---

## 6. Project Structure
```
AgriAI/
├── app.py                      # Core Flask application, routes, and context handlers
├── requirements.txt            # Python dependencies
├── README.md                   # Complete platform documentation
├── test_final.py               # Step 10 comprehensive 20-point integration test suite
├── test_step5.py               # BioBoost regression tests
├── test_step6.py               # IPM Advisor regression tests
├── test_step7.py               # Weather & Forecast regression tests
├── test_step8.py               # Monsoon Outlook regression tests
├── test_step9.py               # Crop Guide & PDF Report regression tests
│
├── engine/                     # Core computational intelligence engines
│   ├── soil_extractor.py       # PDF text extraction and parameter regex matching
│   ├── soil_engine.py          # Soil fertility scoring and threshold evaluation
│   ├── crop_engine.py          # Crop profiles, soil-crop compatibility analysis
│   ├── bioboost_engine.py      # Biological nutrient planning and biofertilizers
│   ├── ipm_engine.py           # Integrated Pest Management decision rules
│   ├── weather_service.py      # Geocoding and Open-Meteo weather API client
│   ├── weather_engine.py       # Weather risk interpretation and spray/irrigation rules
│   ├── monsoon_service.py      # Official IMD seasonal bulletin loader
│   ├── monsoon_engine.py       # Monsoon seasonal impact interpretation
│   ├── report_generator.py     # Multi-page ReportLab PDF generation
│   └── history_manager.py      # SQLite activity store and deduplication manager
│
├── data/                       # Authoritative reference datasets
│   ├── crops.json              # Crop agronomy, pH ranges, growth stages (8 crops)
│   ├── soil_thresholds.json    # ICAR / TNAU soil parameter ratings and critical limits
│   ├── bioboost_reference.json # Biofertilizers, bio-inoculants, organic amendments
│   ├── ipm_knowledge.json      # Pest & disease biology, non-chemical controls
│   ├── imd_monsoon_bulletin.json # Official IMD seasonal outlook data
│   ├── SOURCES.md              # Agronomic and institutional source documentation
│   └── history.db              # SQLite persistence for farm activity events
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Master layout with responsive sidebar and styling
│   ├── dashboard.html          # Central Command Center & AI Farm Advisor synthesis
│   ├── soil.html               # Soil Lab (upload, extract, manual correction)
│   ├── crop_advisor.html       # Crop selection and suitability matrix
│   ├── bioboost.html           # BioBoost biological nutrient advisor
│   ├── pest_advisor.html       # Pest & Disease Advisor (IPM decision hierarchy)
│   ├── weather.html            # 7-day weather forecast and farm guidance
│   ├── monsoon.html            # Official IMD Monsoon Outlook
│   ├── crop_guide.html         # Detailed agronomic crop guide
│   └── history.html            # Farmer activity log with search & filters
│
├── static/
│   ├── css/
│   │   └── style.css           # Premium AgriAI design tokens, responsive layout
│   └── images/                 # Static brand assets
│
└── uploads/                    # Temporary uploaded Soil Health Cards and session cache
```

---

## 7. Installation
1. Clone or extract the repository:
   ```bash
   cd AgriAI
   ```
2. Create and activate a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 8. Running the Application
Launch the Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5001
```

---

## 9. Main Modules
1. **Dashboard (`/`):** Command center displaying farm identity, Soil Health Index (SHI), active crop profile, live weather KPIs, multi-pillar AI Advisor summary, quick actions, and recent activity timeline.
2. **Soil Lab (`/soil`):** Upload laboratory test reports (PDF/JPG/PNG) or manually enter pH, EC, Organic Carbon, Nitrogen, Phosphorus, and Potassium to receive immediate fertility classifications and Soil Health Index scores.
3. **Crop Advisor (`/crop-advisor`):** Select target crops (Moringa, Paddy, Groundnut, Tomato, Cotton, Banana, Chilli, Maize) to assess soil-crop compatibility, growth durations, and limiting nutrient factors.
4. **BioBoost (`/bioboost`):** Biological soil intelligence delivering tailored organic matter additions, microbial consortia recommendations, and biofertilizer application methods matched to the crop's current stage.
5. **Pest Advisor (`/pest-advisor`):** Integrated Pest Management (IPM) decision tool providing field diagnostic clues, economic injury thresholds, non-chemical preventative measures, and biological biocontrol agents.
6. **Weather & Forecast (`/weather`):** Real-time temperature, humidity, wind speed, precipitation probability, and 7-day forecast with agronomic operational guidelines (spraying conditions, irrigation scheduling).
7. **Monsoon Outlook (`/monsoon`):** Official India Meteorological Department (IMD) seasonal rainfall outlook, subdivision probabilities, and practical dry-spell/drainage management.
8. **Crop Guide (`/crop-guide`):** Agronomic knowledge base detailing lifecycle stages, critical watering stages, and temperature thresholds for each supported crop.
9. **Farm Report (`/generate-report`):** One-click compilation of a multi-page, publication-quality PDF report incorporating all current farm and analytical findings.
10. **Farm History (`/history`):** Chronological activity record showing completed soil analyses, crop suitability checks, pest scouting, and exported reports with type and crop filters.

---

## 10. Data Sources
All agronomic rules and thresholds are grounded in recognized Indian agricultural institutions:
- **ICAR (Indian Council of Agricultural Research):** Standard soil testing guidelines and parameter classification ranges.
- **TNAU (Tamil Nadu Agricultural University):** Agronomy manuals, crop water requirements, and growth timelines.
- **NBAIR (National Bureau of Agricultural Insect Resources):** Biological control agents, parasitoids, and bio-pesticide protocols.
- Detailed citations are maintained in `data/SOURCES.md`.

---

## 11. PDF Report Generation
Reports are generated dynamically on demand using ReportLab:
- Vector-rendered tables and typography adhering to the AgriAI brand aesthetic.
- Includes location metadata, executive summaries, soil health evaluation tables, crop suitability scores, BioBoost biological schedules, IPM action protocols, and 7-day weather outlooks.
- Gracefully handles missing modules with explanatory notices rather than omitting sections or crashing.

---

## 12. Weather Source
- **API Provider:** Open-Meteo (`https://api.open-meteo.com/v1/forecast`)
- **Geocoding:** Open-Meteo Geocoding API (`https://geocoding-api.open-meteo.com/v1/search`)
- **Caching Mechanism:** 30-minute in-memory cache to ensure fast page loads, eliminate redundant API calls, and provide offline fallback during network interruptions.

---

## 13. IMD Monsoon Source
- **Authoritative Meteorological Body:** India Meteorological Department (IMD), Ministry of Earth Sciences, Government of India.
- **Bulletins Handled:** Long-Range Forecast for Southwest Monsoon and Northeast Monsoon (Post-Monsoon) over South Peninsular India.
- **Integrity Rule:** AgriAI explicitly does not fabricate monsoon predictions; seasonal forecasts are strictly attributed to official IMD publications.

---

## 14. Limitations
- **Image OCR:** While PDF text extraction is fully automated, image-based soil reports (scanned photos or low-resolution JPGs) utilize the manual entry fallback form.
- **Pesticide Prescriptions:** AgriAI strictly adheres to IPM decision support and does not dispense commercial brand-name pesticide dosages or tank-mix recommendations.
- **Geocoding Scope:** Rural hamlet names may occasionally require entering the higher-level taluk or district name to resolve geographic coordinates.

---

## 15. Future Improvements
- Multi-lingual localization supporting regional Indian languages (Tamil, Hindi, Telugu, Kannada).
- Offline Progressive Web App (PWA) caching for low-connectivity rural field use.
- Direct integration with Government Soil Health Card portal APIs via farmer authentication.
- Satellite-derived Normalized Difference Vegetation Index (NDVI) field monitoring integration.
