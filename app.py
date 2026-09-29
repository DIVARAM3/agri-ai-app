"""
AgriAI - AI-Powered Agricultural Decision Support Platform
Main Flask Application - Step 10: Final Integration & Polish
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from engine.soil_extractor import extract_soil_parameters_from_pdf, PARAM_DISPLAY, is_valid_param_value
from engine.crop_engine import (
    load_crops, get_crop_by_name, validate_crop, combine_crop_and_soil,
    generate_crop_soil_intelligence, get_crop_profile, evaluate_crop_suitability,
    get_crop_categories, search_crops, evaluate_multiple_crops
)
from engine.soil_engine import analyze_soil
from engine.bioboost_engine import generate_bioboost_guidance
from engine.ipm_engine import load_ipm_data, get_crop_ipm_issues, get_issue_by_id, generate_ipm_plan, get_supported_crops
from engine.weather_service import get_weather
from engine.weather_engine import generate_weather_insights, generate_weather_alerts, generate_crop_weather_context
from engine.monsoon_service import get_official_monsoon_bulletin
from engine.monsoon_engine import interpret_monsoon_outlook
from engine.report_generator import generate_farm_report_pdf
from engine.history_manager import init_db, record_activity, get_recent_activities, get_activity_stats

import json
import uuid
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.environ.get('SECRET_KEY', 'agriai-soil-lab-secret-2024')

# Initialize SQLite History Database
init_db()

# Server-side Session Management (prevents 4KB browser cookie size overflow)
class FileSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None):
        def on_update(self):
            self.modified = True
        super().__init__(initial or {}, on_update)
        self.sid = sid
        self.modified = False

class FileSessionInterface(SessionInterface):
    def __init__(self, session_dir):
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)

    def open_session(self, app, request):
        sid = request.cookies.get(app.config.get('SESSION_COOKIE_NAME', 'session'))
        if not sid:
            return FileSession(sid=str(uuid.uuid4()))
        filepath = os.path.join(self.session_dir, secure_filename(sid))
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return FileSession(json.load(f), sid=sid)
            except Exception:
                pass
        return FileSession(sid=sid)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        if not session:
            if session.modified:
                filepath = os.path.join(self.session_dir, secure_filename(session.sid))
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                response.delete_cookie(app.config.get('SESSION_COOKIE_NAME', 'session'), domain=domain, path=path)
            return

        filepath = os.path.join(self.session_dir, secure_filename(session.sid))
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(dict(session), f)
        except Exception:
            pass

        response.set_cookie(
            app.config.get('SESSION_COOKIE_NAME', 'session'),
            session.sid,
            httponly=self.get_cookie_httponly(app),
            domain=domain,
            path=path,
            secure=self.get_cookie_secure(app),
            samesite=self.get_cookie_samesite(app)
        )

SESSION_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', '.sessions')
app.session_interface = FileSessionInterface(SESSION_DIR)

# Upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'soil_reports')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # 15MB max limit
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Agronomic reference ranges
SOIL_RANGES = {
    'ph': {'optimal': (6.5, 7.5), 'unit': ''},
    'nitrogen': {'optimal': (250, 400), 'unit': 'mg/kg'},
    'phosphorus': {'optimal': (25, 45), 'unit': 'mg/kg'},
    'potassium': {'optimal': (350, 500), 'unit': 'mg/kg'},
    'organic_carbon': {'optimal': (1.0, 2.0), 'unit': '%'},
    'ec': {'optimal': (0.4, 0.8), 'unit': 'dS/m'}
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# 13-Step Farmer Guide Architecture
FARMER_GUIDE_STEPS = [
    {'step': 1, 'id': 'profile', 'title': 'Farmer Profile', 'short_title': 'Profile', 'icon': '👤', 'desc': 'Farmer identity & contact details'},
    {'step': 2, 'id': 'farm_details', 'title': 'Farm Details', 'short_title': 'Farm', 'icon': '🏡', 'desc': 'Field name, survey number & land area'},
    {'step': 3, 'id': 'location', 'title': 'Farm Location', 'short_title': 'Location', 'icon': '📍', 'desc': 'Village, district & state for agro-meteorology'},
    {'step': 4, 'id': 'soil', 'title': 'Soil Lab', 'short_title': 'Soil Lab', 'icon': '🧪', 'desc': 'Soil test analysis & nutrient parameters'},
    {'step': 5, 'id': 'select_crops', 'title': 'Select Crops', 'short_title': 'Crops', 'icon': '🌾', 'desc': 'Multi-crop selection from 30-crop catalog'},
    {'step': 6, 'id': 'growth_stages', 'title': 'Crop Growth Stages', 'short_title': 'Stages', 'icon': '🌱', 'desc': 'Crop-specific phenological growth stages'},
    {'step': 7, 'id': 'crop_intelligence', 'title': 'Crop Intelligence', 'short_title': 'Suitability', 'icon': '📊', 'desc': 'Deterministic soil-crop suitability & comparison'},
    {'step': 8, 'id': 'bioboost', 'title': 'BioBoost Soil Biology', 'short_title': 'BioBoost', 'icon': '🌿', 'desc': 'Microbial inoculants & organic matter fertility'},
    {'step': 9, 'id': 'ipm', 'title': 'Pest & Disease / IPM', 'short_title': 'IPM', 'icon': '🐛', 'desc': 'Diagnostic field symptoms & ecological IPM'},
    {'step': 10, 'id': 'weather', 'title': 'Weather & Forecast', 'short_title': 'Weather', 'icon': '⛅', 'desc': 'Real-time microclimate & 7-day operational windows'},
    {'step': 11, 'id': 'monsoon', 'title': 'Monsoon Outlook', 'short_title': 'Monsoon', 'icon': '🌧️', 'desc': 'Official IMD seasonal meteorological guidance'},
    {'step': 12, 'id': 'action_plan', 'title': 'Farm Action Plan', 'short_title': 'Action Plan', 'icon': '✅', 'desc': 'Consolidated field milestones & monitoring protocol'},
    {'step': 13, 'id': 'report', 'title': 'Generate Farm Report', 'short_title': 'Report', 'icon': '📄', 'desc': 'Official AGRIORA Precision Field Intelligence Dossier'}
]


def get_farmer_guide_status(sess=None):
    """
    Computes completed steps and progress percentage dynamically from session state.
    Optionally accepts a session dictionary for unit testing.
    """
    target_session = sess if sess is not None else session
    loc = target_session.get('user_location') or target_session.get('location') or {}
    farmer_prof = target_session.get('farmer_profile') or {}
    farm_det = target_session.get('farm_details') or {}
    farmer_name = target_session.get('farmer_name') or farmer_prof.get('farmer_name')
    survey_num = target_session.get('survey_number') or farm_det.get('survey_number')

    soil_data = target_session.get('soil_data') or {}
    has_soil = bool(soil_data and any(soil_data.get(k) is not None for k in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']))

    raw_crops = target_session.get('selected_crops') or []
    selected_crops = []
    if isinstance(raw_crops, list):
        for c in raw_crops:
            if isinstance(c, dict) and c.get('name'):
                selected_crops.append(c['name'])
            elif isinstance(c, str) and c.strip():
                selected_crops.append(c.strip())

    if not selected_crops and target_session.get('selected_crop'):
        selected_crops = [target_session.get('selected_crop')]

    stages = target_session.get('crop_growth_stages') or {}
    has_stages = bool(selected_crops and all(stages.get(c) for c in selected_crops))

    step_done = {
        1: bool(farmer_name),
        2: bool(survey_num or target_session.get('farm_name') or farm_det.get('farm_name') or target_session.get('farm_area') or farm_det.get('farm_area')),
        3: bool(loc.get('village') or loc.get('district')),
        4: has_soil,
        5: bool(len(selected_crops) >= 1),
        6: has_stages,
        7: bool(target_session.get('soil_crop_analysis') or target_session.get('multi_crop_analysis') or (has_soil and selected_crops)),
        8: bool(target_session.get('bioboost_analysis') or target_session.get('bioboost_reviewed')),
        9: bool(target_session.get('ipm_analysis') or target_session.get('ipm_reviewed')),
        10: bool(target_session.get('weather_viewed')),
        11: bool(target_session.get('monsoon_viewed')),
        12: bool(target_session.get('action_plan_reviewed')),
        13: bool(target_session.get('report_generated'))
    }

    manual_completed = set(target_session.get('guide_completed_steps') or target_session.get('farmer_guide_completed') or [])
    for s in manual_completed:
        if s in step_done:
            step_done[s] = True

    completed_count = sum(1 for v in step_done.values() if v)
    progress_pct = int(round((completed_count / 13) * 100))

    current_step = target_session.get('farmer_guide_step') or target_session.get('guide_step')
    next_uncompleted = 1
    for s in range(1, 14):
        if not step_done.get(s, False):
            next_uncompleted = s
            break
    else:
        next_uncompleted = 13

    if not current_step or current_step < 1 or current_step > 13:
        current_step = next_uncompleted

    steps_decorated = []
    for item in FARMER_GUIDE_STEPS:
        s_num = item['step']
        is_done = step_done.get(s_num, False)
        is_curr = (s_num == current_step)
        steps_decorated.append({
            **item,
            'is_completed': is_done,
            'is_current': is_curr,
            'is_upcoming': (not is_done and not is_curr),
            'status_class': 'completed' if is_done else ('current' if is_curr else 'upcoming'),
            'icon_status': '✓' if is_done else ('●' if is_curr else '○')
        })

    return {
        'steps': steps_decorated,
        'completed_count': completed_count,
        'total_steps': 13,
        'progress_pct': progress_pct,
        'current_step': current_step,
        'next_uncompleted_step': next_uncompleted,
        'step_done': step_done
    }


def get_farmer_context():
    """Retrieve consistent farmer identity, location, and crop context from session."""
    loc = session.get('user_location') or session.get('location') or {}
    farmer_prof = session.get('farmer_profile') or {}
    farm_det = session.get('farm_details') or {}

    farmer_name = session.get('farmer_name') or farmer_prof.get('farmer_name') or loc.get('farmer_name') or ''
    farm_name = session.get('farm_name') or farm_det.get('farm_name') or loc.get('farm_name') or ''
    survey_number = session.get('survey_number') or farm_det.get('survey_number') or loc.get('survey_number') or ''
    farm_area = session.get('farm_area') or farm_det.get('farm_area') or loc.get('farm_area') or 'Not specified'
    area_unit = session.get('area_unit') or farm_det.get('area_unit') or loc.get('area_unit') or 'Acre'
    mobile_number = session.get('mobile_number') or farmer_prof.get('mobile_number') or ''

    # Multi-crop handling
    raw_crops = session.get('selected_crops')
    selected_crops = []
    if isinstance(raw_crops, list):
        for c in raw_crops:
            if isinstance(c, dict) and c.get('name'):
                selected_crops.append(c['name'])
            elif isinstance(c, str) and c.strip():
                selected_crops.append(c.strip())

    single_crop = session.get('selected_crop')
    if not selected_crops and single_crop:
        selected_crops = [single_crop]
        session['selected_crops'] = selected_crops
    elif selected_crops and not single_crop:
        single_crop = selected_crops[0]
        session['selected_crop'] = single_crop

    crop_stages = session.get('crop_growth_stages') or {}
    growth_stage = session.get('growth_stage') or crop_stages.get(single_crop) or 'Active Vegetative Stage'

    if loc and (loc.get('village') or loc.get('district') or loc.get('state')):
        parts = [p for p in [loc.get('village'), loc.get('district'), loc.get('state')] if p]
        location_str = ", ".join(parts)
    else:
        location_str = "Location not specified"

    guide_status = get_farmer_guide_status()

    return {
        'name': farmer_name if farmer_name else 'Farmer',
        'farmer_name': farmer_name,
        'farm_name': farm_name,
        'survey_number': survey_number,
        'farm_area': farm_area,
        'area_unit': area_unit,
        'mobile_number': mobile_number,
        'growth_stage': growth_stage,
        'crop_growth_stages': crop_stages,
        'location': location_str,
        'has_location': bool(loc and (loc.get('village') or loc.get('district'))),
        'village': loc.get('village'),
        'district': loc.get('district'),
        'state': loc.get('state'),
        'current_crop': single_crop or 'No crop selected',
        'selected_crop': single_crop or 'Moringa',
        'selected_crops': selected_crops,
        'selected_crops_count': len(selected_crops),
        'has_crop': bool(single_crop or selected_crops),
        'has_multiple_crops': len(selected_crops) > 1,
        'guide_step': guide_status['current_step'],
        'guide_completed_count': guide_status['completed_count'],
        'guide_progress_pct': guide_status['progress_pct'],
        'guide_status': guide_status
    }


def get_soil_status(param_name, value):
    """Determine if soil parameter is in optimal range based on reference thresholds."""
    if value is None or param_name not in SOIL_RANGES:
        return 'Unknown'
    
    optimal_range = SOIL_RANGES[param_name]['optimal']
    try:
        val = float(value)
        if optimal_range[0] <= val <= optimal_range[1]:
            return 'Optimal'
        elif val < optimal_range[0]:
            return 'Low'
        else:
            return 'High'
    except (ValueError, TypeError):
        return 'Unknown'


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def dashboard():
    """Main dashboard page - displays live intelligence synthesized from session and persistent modules"""
    user = get_farmer_context()
    raw_soil = session.get('soil_data')
    has_soil = any(v is not None for v in raw_soil.values()) if raw_soil and isinstance(raw_soil, dict) else False

    if has_soil:
        soil_data = dict(raw_soil)
        if 'electrical_conductivity' in soil_data and 'ec' not in soil_data:
            soil_data['ec'] = soil_data['electrical_conductivity']
        if 'ec' in soil_data and 'electrical_conductivity' not in soil_data:
            soil_data['electrical_conductivity'] = soil_data['ec']
        soil_analysis = analyze_soil(soil_data)
        soil_health = soil_analysis['soil_health']['score']
        soil_health_rating = soil_analysis['soil_health'].get('label', 'Good')
        soil_concerns = soil_analysis.get('concerns', [])
        soil_strengths = soil_analysis.get('strengths', [])
        soil_priority_actions = soil_analysis.get('priority_actions', [])
    else:
        soil_data = None
        soil_analysis = None
        soil_health = None
        soil_health_rating = "Not Analyzed"
        soil_concerns = []
        soil_strengths = []
        soil_priority_actions = []

    selected_crop = session.get('selected_crop')
    has_crop = bool(selected_crop)
    crop_profile = get_crop_by_name(selected_crop) if selected_crop else None

    # Crop suitability from Crop Advisor intelligence
    intel = session.get('soil_crop_analysis')
    crop_suitability = None
    crop_status_label = None
    crop_health_score = 0
    advisor_summary = None

    if intel and isinstance(intel, dict) and intel.get('crop') and intel['crop'].get('name') == selected_crop:
        crop_suitability = intel.get('crop_analysis')
    
    if not crop_suitability and has_soil and selected_crop:
        comb = combine_crop_and_soil(selected_crop, soil_data, session.get('user_location'))
        gen_intel = generate_crop_soil_intelligence(comb)
        crop_suitability = gen_intel.get('crop_analysis')

    if crop_suitability:
        crop_status_label = crop_suitability.get('suitability_status', 'Suitable')
        crop_health_score = crop_suitability.get('suitability_score', 80)
        concerns = crop_suitability.get('limiting_factors', [])
        reasons = crop_suitability.get('supporting_factors', [])
        concern_text = f" {concerns[0]}" if concerns else (f" {reasons[0]}" if reasons else " Soil parameters are well-balanced.")
        advisor_summary = f"Selected crop ({selected_crop}) is marked {crop_status_label} for your soil.{concern_text}"
    else:
        if selected_crop and not has_soil:
            advisor_summary = f"Selected crop is {selected_crop}. Soil test analysis is required to evaluate suitability."
        elif has_soil and not selected_crop:
            advisor_summary = "Soil analysis is active. Select a crop in Crop Advisor to evaluate suitability."
        else:
            advisor_summary = None

    # BioBoost dashboard synchronization
    bioboost_analysis = session.get('bioboost_analysis')
    bioboost_summary = None
    if bioboost_analysis and bioboost_analysis.get('priorities'):
        priorities = bioboost_analysis['priorities']
        bioboost_summary = {
            'count': len(priorities),
            'top_item': priorities[0] if priorities else None,
            'crop': bioboost_analysis.get('crop', user['current_crop'])
        }

    # IPM dashboard synchronization
    ipm_analysis = session.get('ipm_analysis') or session.get('ipm_summary')
    ipm_summary = None
    if ipm_analysis:
        risk = ipm_analysis.get('risk') if isinstance(ipm_analysis.get('risk'), dict) else {}
        ipm_summary = {
            'status': 'IPM assessment available',
            'issue_name': ipm_analysis.get('issue_name'),
            'type': ipm_analysis.get('type'),
            'risk_level': risk.get('level') or ipm_analysis.get('risk_level', 'LOW'),
            'risk_code': risk.get('code') or ipm_analysis.get('risk_code', 'success'),
            'risk_badge': risk.get('badge') or ipm_analysis.get('risk_badge', 'badge-success'),
            'crop': ipm_analysis.get('crop', user['current_crop'])
        }

    # Live dynamic weather synchronization
    weather_loc = session.get('user_location') or {
        'village': 'Kammadikottai',
        'district': 'Thoothukudi',
        'state': 'Tamil Nadu'
    }
    weather_data = get_weather(weather_loc)
    if weather_data and weather_data.get('success'):
        curr = weather_data.get('current', {})
        daily = weather_data.get('daily', [])
        weather_temp = curr.get('temperature', '--')
        weather_condition = curr.get('condition', 'Clear')
        humidity = curr.get('humidity', '--')
        wind_speed = curr.get('wind_speed', '--')
        rain_probability = daily[0].get('rain_probability', 0) if daily else 0
        weather_rainfall = curr.get('rain', 0.0)
        weather_forecast = daily[:5]
        weather_available = True
        weather_message = None
    else:
        weather_temp = "--"
        weather_condition = "Unavailable"
        humidity = "--"
        wind_speed = "--"
        rain_probability = 0
        weather_rainfall = "--"
        weather_forecast = []
        weather_available = False
        weather_message = weather_data.get('message', 'Weather data temporarily unavailable') if weather_data else 'Weather data temporarily unavailable'

    # Monsoon Outlook check for dashboard
    monsoon_data = get_official_monsoon_bulletin(state=weather_loc.get('state'), district=weather_loc.get('district'))
    if monsoon_data and monsoon_data.get('status') == 'Available':
        monsoon_available = True
        monsoon_title = monsoon_data.get('title', 'Official Seasonal Monsoon Outlook')
        monsoon_season = monsoon_data.get('season', 'Indian Monsoon')
        monsoon_date = monsoon_data.get('published_date', '')
    else:
        monsoon_available = False
        monsoon_title = 'Official information currently unavailable'
        monsoon_season = 'Monsoon Outlook'
        monsoon_date = ''

    # Multi-pillar AI Advisor Insights (strictly grounded in existing module outputs)
    ai_advisor_insights = []

    # 1. Soil insight
    if has_soil and soil_health:
        top_c = soil_concerns[0] if soil_concerns else "All 6 parameters in optimal range"
        ai_advisor_insights.append({
            'pillar': 'Soil Intelligence',
            'icon': '🧪',
            'status': f'{soil_health_rating} ({soil_health}/100)',
            'badge_class': 'badge-success' if soil_health >= 70 else 'badge-warning',
            'border_color': 'var(--color-primary)',
            'message': f"Soil health scored at {soil_health}/100 ({soil_health_rating}). Primary agronomic focus: {top_c}."
        })
    else:
        ai_advisor_insights.append({
            'pillar': 'Soil Intelligence',
            'icon': '🧪',
            'status': 'Pending Analysis',
            'badge_class': 'badge-warning',
            'border_color': 'var(--color-warning)',
            'message': 'No soil analysis on file. Upload a Soil Health Card or enter lab values in Soil Lab.'
        })

    # 2. Crop suitability insight
    if has_crop and crop_status_label:
        ai_advisor_insights.append({
            'pillar': 'Crop Suitability',
            'icon': '🌾',
            'status': crop_status_label,
            'badge_class': 'badge-success' if 'Suitable' in crop_status_label or 'Optimal' in crop_status_label else 'badge-warning',
            'border_color': 'var(--color-secondary)',
            'message': advisor_summary or f"{selected_crop} suitability evaluated."
        })
    elif has_crop:
        ai_advisor_insights.append({
            'pillar': 'Crop Suitability',
            'icon': '🌾',
            'status': 'Crop Active',
            'badge_class': 'badge-info',
            'border_color': 'var(--color-secondary)',
            'message': f"Selected crop is {selected_crop}. Soil test analysis needed to evaluate exact soil suitability."
        })
    else:
        ai_advisor_insights.append({
            'pillar': 'Crop Suitability',
            'icon': '🌾',
            'status': 'No Crop',
            'badge_class': 'badge-warning',
            'border_color': 'var(--color-border)',
            'message': 'No crop currently selected. Choose a crop in Crop Advisor to view tailored cultivation guidelines.'
        })

    # 3. BioBoost insight
    if bioboost_summary:
        ai_advisor_insights.append({
            'pillar': 'BioBoost Biology',
            'icon': '🌿',
            'status': f"{bioboost_summary['count']} Priorities",
            'badge_class': 'badge-success',
            'border_color': 'var(--color-primary)',
            'message': f"BioBoost identified {bioboost_summary['count']} biological soil priorities. Top action: {bioboost_summary['top_item']['title']} ({bioboost_summary['top_item']['action']})."
        })
    else:
        ai_advisor_insights.append({
            'pillar': 'BioBoost Biology',
            'icon': '🌿',
            'status': 'Pending',
            'badge_class': 'badge-info',
            'border_color': 'var(--color-border)',
            'message': 'Biological nutrient guidance is ready to generate once soil and crop are verified.'
        })

    # 4. IPM insight
    if ipm_summary:
        ai_advisor_insights.append({
            'pillar': 'Integrated Pest Management',
            'icon': '🐛',
            'status': f"{ipm_summary['risk_level']} Risk",
            'badge_class': ipm_summary['risk_badge'],
            'border_color': 'var(--color-warning)',
            'message': f"IPM scouting active for {ipm_summary['issue_name']} on {ipm_summary['crop']}. Implement cultural and biological prevention first."
        })
    else:
        ai_advisor_insights.append({
            'pillar': 'Integrated Pest Management',
            'icon': '🐛',
            'status': 'Pending Scouting',
            'badge_class': 'badge-info',
            'border_color': 'var(--color-border)',
            'message': 'No pest or disease threats currently under active assessment in Pest Advisor.'
        })

    # 5. Weather insight
    if weather_available:
        ai_advisor_insights.append({
            'pillar': 'Weather Context',
            'icon': '⛅',
            'status': f"{weather_temp}°C, {weather_condition}",
            'badge_class': 'badge-success',
            'border_color': '#0284c7',
            'message': f"Current temperature is {weather_temp}°C with {rain_probability}% rain probability. Consult the 5-day forecast before spraying or irrigating."
        })
    else:
        ai_advisor_insights.append({
            'pillar': 'Weather Context',
            'icon': '⛅',
            'status': 'Unavailable',
            'badge_class': 'badge-warning',
            'border_color': 'var(--color-border)',
            'message': 'Live weather service temporarily unreachable. Check local district agromet advisories.'
        })

    # Recent activities from SQLite
    recent_activities = get_recent_activities(limit=5)
    stats = get_activity_stats()
    report_summary = session.get('report_summary')

    context = {
        'user': user,
        'has_soil': has_soil,
        'soil_data': soil_data,
        'soil_ranges': SOIL_RANGES,
        'soil_health': soil_health,
        'soil_health_rating': soil_health_rating,
        'soil_priority_actions': soil_priority_actions,
        'has_crop': has_crop,
        'selected_crop': selected_crop,
        'crop_profile': crop_profile,
        'crop_health': crop_health_score,
        'crop_suitability_status': crop_status_label,
        'advisor_summary': advisor_summary,
        'bioboost_summary': bioboost_summary,
        'ipm_summary': ipm_summary,
        'weather_temp': weather_temp,
        'weather_condition': weather_condition,
        'humidity': humidity,
        'rain_probability': rain_probability,
        'wind_speed': wind_speed,
        'weather_rainfall': weather_rainfall,
        'weather_forecast': weather_forecast,
        'weather_available': weather_available,
        'weather_message': weather_message,
        'monsoon_available': monsoon_available,
        'monsoon_title': monsoon_title,
        'monsoon_season': monsoon_season,
        'monsoon_date': monsoon_date,
        'ai_advisor_insights': ai_advisor_insights,
        'recent_activities': recent_activities,
        'stats': stats,
        'report_summary': report_summary,
        'get_soil_status': get_soil_status,
        'has_intelligence': bool(intel or has_soil)
    }
    return render_template('dashboard.html', **context)


def mark_guide_step_completed(step_num):
    """Mark a specific farmer guide step as completed in session."""
    completed = set(session.get('guide_completed_steps') or [])
    completed.add(int(step_num))
    session['guide_completed_steps'] = list(completed)


@app.route('/farmer-guide', methods=['GET', 'POST'])
def farmer_guide():
    """
    13-Step Guided Farmer Workflow:
    1. Farmer Profile
    2. Farm Details
    3. Farm Location
    4. Soil Lab
    5. Select Crops (Multi-Crop)
    6. Crop Growth Stage
    7. Crop Intelligence
    8. BioBoost
    9. Pest & Disease / IPM
    10. Weather
    11. Monsoon Outlook
    12. Farm Action Plan
    13. Generate Farm Report
    """
    all_crops = load_crops()
    categories = get_crop_categories()
    user = get_farmer_context()
    guide_status = get_farmer_guide_status()

    # Determine current step
    step_arg = request.args.get('step', type=int)
    if step_arg and 1 <= step_arg <= 13:
        current_step = step_arg
        session['farmer_guide_step'] = session['guide_step'] = current_step
    else:
        current_step = session.get('farmer_guide_step') or session.get('guide_step') or guide_status['current_step'] or 1
        if current_step < 1 or current_step > 13:
            current_step = 1

    # Seamless resume: if GET without ?step= parameter, redirect to active current_step
    if request.method == 'GET' and 'step' not in request.args:
        return redirect(url_for('farmer_guide', step=current_step))

    error = None
    success_message = None

    if request.method == 'POST':
        form_step = request.form.get('step', type=int) or current_step

        # STEP 1: Farmer Profile
        if form_step == 1:
            farmer_name = request.form.get('farmer_name', '').strip()
            farm_name = request.form.get('farm_name', '').strip()
            mobile_number = request.form.get('mobile_number', '').strip()
            if not farmer_name:
                error = "Farmer Full Name is required to personalize your dossier."
            else:
                session['farmer_name'] = farmer_name
                session['farmer_profile'] = {
                    'farmer_name': farmer_name,
                    'farm_name': farm_name,
                    'mobile_number': mobile_number
                }
                if farm_name:
                    session['farm_name'] = farm_name
                if mobile_number:
                    session['mobile_number'] = mobile_number
                loc = session.get('user_location') or {}
                loc['farmer_name'] = farmer_name
                if farm_name:
                    loc['farm_name'] = farm_name
                session['user_location'] = loc
                mark_guide_step_completed(1)
                session['farmer_guide_step'] = session['guide_step'] = 2
                return redirect(url_for('farmer_guide', step=2))

        # STEP 2: Farm Details
        elif form_step == 2:
            survey_number = request.form.get('survey_number', '').strip()
            farm_area = request.form.get('farm_area', '').strip()
            area_unit = request.form.get('area_unit', 'Acre').strip()
            farm_name = request.form.get('farm_name', '').strip()
            if not survey_number:
                error = "Survey Number / Field ID is required."
            else:
                session['survey_number'] = survey_number
                session['farm_area'] = farm_area or '2.5'
                session['area_unit'] = area_unit or 'Acre'
                if farm_name:
                    session['farm_name'] = farm_name
                session['farm_details'] = {
                    'farm_name': farm_name or session.get('farm_name', ''),
                    'survey_number': survey_number,
                    'farm_area': session['farm_area'],
                    'area_unit': session['area_unit']
                }
                loc = session.get('user_location') or {}
                loc['survey_number'] = survey_number
                loc['farm_area'] = session['farm_area']
                loc['area_unit'] = session['area_unit']
                if farm_name:
                    loc['farm_name'] = farm_name
                session['user_location'] = loc
                mark_guide_step_completed(2)
                session['farmer_guide_step'] = session['guide_step'] = 3
                return redirect(url_for('farmer_guide', step=3))

        # STEP 3: Farm Location
        elif form_step == 3:
            village = request.form.get('village', '').strip()
            district = request.form.get('district', '').strip()
            state = request.form.get('state', '').strip()
            if not village or not district or not state:
                error = "Village, District, and State are all required to calibrate agro-meteorology."
            else:
                loc = session.get('user_location') or {}
                loc['village'] = village
                loc['district'] = district
                loc['state'] = state
                loc['farmer_name'] = session.get('farmer_name', '')
                loc['survey_number'] = session.get('survey_number', '')
                session['user_location'] = loc
                session['location'] = {'village': village, 'district': district, 'state': state}
                session['farm_location'] = loc
                mark_guide_step_completed(3)
                session['farmer_guide_step'] = session['guide_step'] = 4
                return redirect(url_for('farmer_guide', step=4))

        # STEP 4: Soil Lab
        elif form_step == 4:
            raw_ph = request.form.get('ph', '').strip()
            raw_ec = request.form.get('ec', '').strip()
            raw_oc = request.form.get('organic_carbon', '').strip()
            raw_n = request.form.get('nitrogen', '').strip()
            raw_p = request.form.get('phosphorus', '').strip()
            raw_k = request.form.get('potassium', '').strip()

            soil_data = session.get('soil_data') or {}
            has_input = False
            for k, val in [('ph', raw_ph), ('ec', raw_ec), ('organic_carbon', raw_oc),
                           ('nitrogen', raw_n), ('phosphorus', raw_p), ('potassium', raw_k)]:
                if val != '':
                    try:
                        vnum = float(val)
                        if vnum >= 0:
                            if k in ['nitrogen', 'phosphorus', 'potassium'] and vnum.is_integer():
                                soil_data[k] = int(vnum)
                            else:
                                soil_data[k] = round(vnum, 2)
                            has_input = True
                    except ValueError:
                        pass

            if has_input:
                session['soil_data'] = soil_data
                detected = [k for k, v in soil_data.items() if v is not None]
                session['report_summary'] = {
                    'filename': 'Farmer Guide Entry',
                    'date': datetime.now().strftime('%B %d, %Y, %I:%M %p'),
                    'detected_count': len(detected),
                    'missing_count': 6 - len(detected),
                    'detected_keys': detected,
                    'missing_keys': [k for k in ['ph', 'ec', 'organic_carbon', 'nitrogen', 'phosphorus', 'potassium'] if k not in detected]
                }
                mark_guide_step_completed(4)
                session['farmer_guide_step'] = session['guide_step'] = 5
                return redirect(url_for('farmer_guide', step=5))
            elif any(v is not None for v in (session.get('soil_data') or {}).values()):
                mark_guide_step_completed(4)
                session['farmer_guide_step'] = session['guide_step'] = 5
                return redirect(url_for('farmer_guide', step=5))
            else:
                error = "Please enter soil test values or confirm your Soil Health Card parameters."

        # STEP 5: Select Crops
        elif form_step == 5:
            crops_selected = request.form.getlist('selected_crops') or request.form.getlist('crops')
            if not crops_selected:
                raw_c = request.form.get('selected_crops', '').strip() or request.form.get('crops', '').strip()
                if raw_c:
                    crops_selected = [c.strip() for c in raw_c.split(',') if c.strip()]

            # Deduplicate preserving order
            seen = set()
            valid_selected = []
            for c in crops_selected:
                prof = get_crop_by_name(c)
                if prof and prof['name'] not in seen:
                    seen.add(prof['name'])
                    valid_selected.append(prof['name'])

            if not valid_selected:
                flash("Please select at least one crop from the catalog.", "error")
                return redirect(url_for('farmer_guide', step=5))
            else:
                session['selected_crops'] = valid_selected
                session['selected_crop'] = valid_selected[0]

                # Initialize default growth stages for newly selected crops
                stages_map = session.get('crop_growth_stages') or {}
                for c in valid_selected:
                    if c not in stages_map:
                        cp = get_crop_by_name(c)
                        if cp and cp.get('growth_stages'):
                            stages_map[c] = cp['growth_stages'][1 if len(cp['growth_stages']) > 1 else 0]
                        else:
                            stages_map[c] = "Active Vegetative Stage"
                session['crop_growth_stages'] = stages_map
                session['growth_stage'] = stages_map.get(valid_selected[0], 'Active Vegetative Stage')

                mark_guide_step_completed(5)
                session['farmer_guide_step'] = session['guide_step'] = 6
                return redirect(url_for('farmer_guide', step=6))

        # STEP 6: Crop Growth Stages
        elif form_step == 6:
            crops_list = session.get('selected_crops') or [session.get('selected_crop') or 'Moringa']
            stages_map = session.get('crop_growth_stages') or {}
            for c in crops_list:
                stg = request.form.get(f'stage_{c}') or request.form.get(c)
                if stg:
                    stages_map[c] = stg.strip()
            session['crop_growth_stages'] = stages_map
            if crops_list and crops_list[0] in stages_map:
                session['growth_stage'] = stages_map[crops_list[0]]

            mark_guide_step_completed(6)
            session['farmer_guide_step'] = session['guide_step'] = 7
            return redirect(url_for('farmer_guide', step=7))

        # STEP 7: Crop Intelligence
        elif form_step == 7:
            crops_list = session.get('selected_crops') or [session.get('selected_crop') or 'Moringa']
            loc = session.get('user_location') or {}
            record_activity(
                'CROP_ANALYSIS',
                f"Multi-crop evaluation completed for {', '.join(crops_list)}",
                crop=crops_list,
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state'),
                farmer_name=session.get('farmer_name'),
                survey_number=session.get('survey_number')
            )
            mark_guide_step_completed(7)
            session['farmer_guide_step'] = 8
            return redirect(url_for('farmer_guide', step=8))

        # STEP 8: BioBoost
        elif form_step == 8:
            crops_list = session.get('selected_crops') or [session.get('selected_crop') or 'Moringa']
            loc = session.get('user_location') or {}
            record_activity(
                'BIOBOOST_ANALYSIS',
                f"BioBoost biological nutrient guidance generated for {', '.join(crops_list)}",
                crop=crops_list,
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state'),
                farmer_name=session.get('farmer_name'),
                survey_number=session.get('survey_number')
            )
            mark_guide_step_completed(8)
            session['farmer_guide_step'] = 9
            return redirect(url_for('farmer_guide', step=9))

        # STEP 9: IPM
        elif form_step == 9:
            crops_list = session.get('selected_crops') or [session.get('selected_crop') or 'Moringa']
            loc = session.get('user_location') or {}
            record_activity(
                'IPM_ASSESSMENT',
                f"Integrated Pest Management review completed for {', '.join(crops_list)}",
                crop=crops_list,
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state'),
                farmer_name=session.get('farmer_name'),
                survey_number=session.get('survey_number')
            )
            mark_guide_step_completed(9)
            session['farmer_guide_step'] = 10
            return redirect(url_for('farmer_guide', step=10))

        # STEP 10: Weather
        elif form_step == 10:
            loc = session.get('user_location') or {}
            record_activity(
                'WEATHER_LOOKUP',
                f"7-day farm weather forecast verified for {loc.get('village', 'Farm')}",
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state'),
                farmer_name=session.get('farmer_name'),
                survey_number=session.get('survey_number')
            )
            mark_guide_step_completed(10)
            session['farmer_guide_step'] = 11
            return redirect(url_for('farmer_guide', step=11))

        # STEP 11: Monsoon Outlook
        elif form_step == 11:
            loc = session.get('user_location') or {}
            record_activity(
                'MONSOON_LOOKUP',
                f"Official IMD seasonal monsoon bulletin verified for {loc.get('district', 'District')}",
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state'),
                farmer_name=session.get('farmer_name'),
                survey_number=session.get('survey_number')
            )
            mark_guide_step_completed(11)
            session['farmer_guide_step'] = 12
            return redirect(url_for('farmer_guide', step=12))

        # STEP 12: Action Plan
        elif form_step == 12:
            mark_guide_step_completed(12)
            session['farmer_guide_step'] = 13
            return redirect(url_for('farmer_guide', step=13))

        # STEP 13: Report
        elif form_step == 13:
            mark_guide_step_completed(13)
            return redirect(url_for('generate_report'))

    # GET preparation
    user = get_farmer_context()
    guide_status = get_farmer_guide_status()
    selected_crops = user['selected_crops']

    # Soil Data
    soil_data = session.get('soil_data')
    has_soil = any(v is not None for v in soil_data.values()) if soil_data and isinstance(soil_data, dict) else False
    soil_analysis = analyze_soil(soil_data) if has_soil else None

    soil_health_score = 0
    soil_health_label = "Pending Analysis"
    if soil_analysis and isinstance(soil_analysis, dict):
        sh = soil_analysis.get('soil_health', {})
        soil_health_score = sh.get('score', 0)
        soil_health_label = sh.get('label', 'Not Rated')

    # Step 7: Multi-crop evaluations
    crop_stages = session.get('crop_growth_stages') or {}
    multi_crop_results = []
    if selected_crops and has_soil and soil_analysis:
        multi_crop_results = evaluate_multiple_crops(selected_crops, soil_analysis, crop_stages)
    elif selected_crops:
        for cname in selected_crops:
            cp = get_crop_by_name(cname)
            if cp:
                multi_crop_results.append({
                    'id': cp.get('id', cname.lower()),
                    'name': cp['name'],
                    'scientific_name': cp.get('scientific_name', ''),
                    'category': cp.get('category', 'Field Crop'),
                    'icon': cp.get('icon', '🌱'),
                    'score': 70,
                    'status': 'Soil Test Pending',
                    'growth_stage': crop_stages.get(cname, 'Active Vegetative Stage'),
                    'reasons': [f"Agronomic profile loaded for {cp['name']}."],
                    'concerns': ["Complete Soil Lab to evaluate exact suitability score."]
                })

    # Step 8: BioBoost data by crop
    bioboost_data_by_crop = {}
    if current_step in [8, 13]:
        for cname in selected_crops:
            stg = crop_stages.get(cname, 'Active Vegetative Stage')
            try:
                b_res = generate_bioboost_guidance(cname, stg, soil_data, session.get('user_location'))
                bioboost_data_by_crop[cname] = b_res
            except Exception:
                pass

    # Step 9: IPM data by crop
    ipm_data_by_crop = {}
    if current_step in [9, 13]:
        for cname in selected_crops:
            try:
                cissues = get_crop_ipm_issues(cname)
                ipm_data_by_crop[cname] = cissues
            except Exception:
                ipm_data_by_crop[cname] = []

    # Step 10: Weather
    weather = None
    if current_step in [10, 13]:
        loc = session.get('user_location') or {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}
        weather = get_weather(loc)

    # Step 11: Monsoon
    monsoon = None
    if current_step in [11, 13]:
        loc = session.get('user_location') or {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}
        monsoon = get_official_monsoon_bulletin(state=loc.get('state'), district=loc.get('district'))

    # Step 12: Action Checklist
    action_checklist = session.get('action_plan_completed') or {
        'soil_done': has_soil,
        'crops_done': len(selected_crops) > 0,
        'bioboost_done': False,
        'ipm_done': False,
        'weather_done': False,
        'extension_done': False
    }

    step_info = None
    for s in FARMER_GUIDE_STEPS:
        if s['step'] == current_step:
            step_info = s
            break

    context = {
        'user': user,
        'guide_status': guide_status,
        'current_step': current_step,
        'step_info': step_info,
        'current_step_meta': step_info or {},
        'all_crops': all_crops,
        'all_categories': categories,
        'soil_data': soil_data,
        'has_soil': has_soil,
        'soil_health_score': soil_health_score,
        'soil_health_label': soil_health_label,
        'multi_crop_results': multi_crop_results,
        'bioboost_data_by_crop': bioboost_data_by_crop,
        'ipm_data_by_crop': ipm_data_by_crop,
        'weather': weather,
        'monsoon': monsoon,
        'action_checklist': action_checklist,
        'get_crop_profile': get_crop_by_name,
        'error': error,
        'success_message': success_message
    }
    return render_template('farmer_guide.html', **context)


@app.route('/farmer-guide/toggle-action', methods=['POST'])
def farmer_guide_toggle_action():
    """Persist action plan item states in session."""
    data = request.get_json(silent=True) or {}
    key = data.get('key') or data.get('action_key')
    checked = data.get('checked') if 'checked' in data else data.get('completed', False)

    plan_state = session.get('action_plan_completed') or {}
    if key:
        plan_state[key] = bool(checked)
        session['action_plan_completed'] = plan_state

    return jsonify({
        'success': True,
        'key': key,
        'checked': bool(checked)
    })


@app.route('/api/crops', methods=['GET'])
def api_crops():
    """Search and category filter API for the 30-crop catalog."""
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    results = search_crops(query, category)
    return jsonify({
        'success': True,
        'count': len(results),
        'crops': results
    })


@app.route('/soil', methods=['GET', 'POST'])
def soil_lab():
    """Soil Lab - Upload and analyze soil reports with manual correction support"""
    error = None
    warning = None
    success_message = None
    has_analysis = False

    default_empty = {
        'ph': None,
        'nitrogen': None,
        'phosphorus': None,
        'potassium': None,
        'organic_carbon': None,
        'ec': None
    }
    soil_data = session.get('soil_data', default_empty.copy())
    report_summary = session.get('report_summary', None)
    if report_summary:
        has_analysis = True

    if request.method == 'POST':
        action = request.form.get('action', 'upload')

        # ACTION 1: REPORT FILE UPLOAD (PDF or Image)
        if action == 'upload':
            if 'report_file' not in request.files:
                error = "No file selected. Please choose a soil report to upload."
            else:
                file = request.files['report_file']
                if not file or file.filename.strip() == '':
                    error = "No file selected. Please choose a soil report to upload."
                elif not allowed_file(file.filename):
                    error = "Unsupported file format. Please upload a PDF, PNG, JPG, or JPEG file."
                else:
                    filename = secure_filename(file.filename)
                    if not filename:
                        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    file_ext = filename.rsplit('.', 1)[1].lower()

                    # Image Fallback (PNG, JPG, JPEG)
                    if file_ext in {'png', 'jpg', 'jpeg'}:
                        warning = "Automatic extraction is unavailable for this report. Please enter the values manually."
                        now_str = datetime.now().strftime('%B %d, %Y, %I:%M %p')
                        report_summary = {
                            'filename': file.filename,
                            'date': now_str,
                            'detected_count': 0,
                            'missing_count': 6,
                            'detected_keys': [],
                            'missing_keys': list(PARAM_DISPLAY.keys()),
                            'is_image': True
                        }
                        session['report_summary'] = report_summary
                        has_analysis = True

                    # PDF Extraction with PyMuPDF
                    elif file_ext == 'pdf':
                        extraction = extract_soil_parameters_from_pdf(filepath)
                        if not extraction['success']:
                            error = extraction.get('error', 'Failed to process PDF report.')
                        elif extraction.get('is_scanned_or_empty'):
                            warning = extraction.get('message', "Automatic extraction is unavailable for this report. Please enter the values manually.")
                            now_str = datetime.now().strftime('%B %d, %Y, %I:%M %p')
                            report_summary = {
                                'filename': file.filename,
                                'date': now_str,
                                'detected_count': 0,
                                'missing_count': 6,
                                'detected_keys': [],
                                'missing_keys': list(PARAM_DISPLAY.keys()),
                                'is_scanned': True
                            }
                            session['report_summary'] = report_summary
                            has_analysis = True
                        else:
                            soil_data = extraction['parameters']
                            now_str = datetime.now().strftime('%B %d, %Y, %I:%M %p')
                            report_summary = {
                                'filename': file.filename,
                                'date': now_str,
                                'detected_count': extraction['detected_count'],
                                'missing_count': extraction['missing_count'],
                                'detected_keys': extraction['detected_keys'],
                                'missing_keys': extraction['missing_keys']
                            }
                            session['soil_data'] = soil_data
                            session['report_summary'] = report_summary
                            has_analysis = True
                            success_message = f"Successfully analyzed {file.filename} — {extraction['detected_count']} parameters detected."

                            # Record activity in SQLite history
                            loc = session.get('user_location') or {}
                            record_activity(
                                'SOIL_ANALYSIS',
                                f"Uploaded and analyzed {file.filename} ({extraction['detected_count']} parameters detected)",
                                crop=session.get('selected_crop'),
                                village=loc.get('village'),
                                district=loc.get('district'),
                                state=loc.get('state')
                            )

        # ACTION 2: MANUAL ENTRY / CORRECTION
        elif action == 'manual_entry':
            farmer_name_inp = request.form.get('farmer_name', '').strip()
            survey_number_inp = request.form.get('survey_number', '').strip()
            if farmer_name_inp:
                session['farmer_name'] = farmer_name_inp
            if survey_number_inp:
                session['survey_number'] = survey_number_inp

            updated_data = {}
            validation_errors = []

            for param in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']:
                val_str = request.form.get(param, '').strip()
                if val_str == '':
                    updated_data[param] = None
                else:
                    try:
                        val_num = float(val_str)
                        if val_num < 0:
                            validation_errors.append(f"{PARAM_DISPLAY[param]['name']} cannot be negative.")
                        else:
                            if param in ['nitrogen', 'phosphorus', 'potassium'] and val_num.is_integer():
                                updated_data[param] = int(val_num)
                            else:
                                updated_data[param] = round(val_num, 2)
                    except ValueError:
                        validation_errors.append(f"Invalid numeric value for {PARAM_DISPLAY[param]['name']}: '{val_str}'")

            if validation_errors:
                error = " ".join(validation_errors)
            else:
                soil_data = updated_data
                session['soil_data'] = soil_data
                session['soil_analysis'] = analyze_soil(soil_data)

                detected = [k for k, v in soil_data.items() if v is not None]
                missing = [k for k, v in soil_data.items() if v is None]

                prev_filename = report_summary.get('filename') if report_summary else 'Manual Entry'
                now_str = datetime.now().strftime('%B %d, %Y, %I:%M %p')
                report_summary = {
                    'filename': prev_filename,
                    'date': now_str,
                    'detected_count': len(detected),
                    'missing_count': len(missing),
                    'detected_keys': detected,
                    'missing_keys': missing
                }
                session['report_summary'] = report_summary
                has_analysis = True
                success_message = "Soil parameters updated successfully."

                # Record activity in SQLite history
                loc = session.get('user_location') or {}
                record_activity(
                    'SOIL_ANALYSIS',
                    f"Verified soil fertility parameters ({len(detected)} parameters active)",
                    crop=session.get('selected_crop'),
                    village=loc.get('village'),
                    district=loc.get('district'),
                    state=loc.get('state'),
                    farmer_name=session.get('farmer_name'),
                    survey_number=session.get('survey_number')
                )

    context = {
        'user': get_farmer_context(),
        'page_title': 'Soil Lab',
        'soil_data': soil_data,
        'param_display': PARAM_DISPLAY,
        'report_summary': report_summary,
        'error': error,
        'warning': warning,
        'success_message': success_message,
        'has_analysis': has_analysis
    }
    return render_template('soil.html', **context)


@app.route('/crop-advisor', methods=['GET', 'POST'])
def crop_advisor():
    """Crop Advisor - Crop selection, location management, and soil profile combination"""
    crops = load_crops()

    default_location = {
        'village': 'Kammadikottai',
        'district': 'Thoothukudi',
        'state': 'Tamil Nadu'
    }
    user_location = session.get('user_location', default_location)

    soil_data = session.get('soil_data', None)
    report_summary = session.get('report_summary', None)
    has_soil_data = False
    if soil_data and isinstance(soil_data, dict):
        has_soil_data = any(v is not None for v in soil_data.values())

    selected_crop_name = request.args.get('crop') or request.form.get('crop')
    raw_multi = request.form.getlist('selected_crops') or request.form.getlist('crops')
    if raw_multi:
        valid_multi = [get_crop_by_name(c)['name'] for c in raw_multi if get_crop_by_name(c)]
        if valid_multi:
            session['selected_crops'] = valid_multi
            selected_crop_name = valid_multi[0]

    if not selected_crop_name:
        selected_crop_name = session.get('selected_crop', 'Moringa')

    crop_profile = get_crop_by_name(selected_crop_name)
    if not crop_profile and crops:
        crop_profile = crops[0]
        selected_crop_name = crop_profile['name']

    session['selected_crop'] = crop_profile['name'] if crop_profile else 'Moringa'
    existing_crops = session.get('selected_crops') or []
    if crop_profile and crop_profile['name'] not in existing_crops:
        session['selected_crops'] = [crop_profile['name']] + [c for c in existing_crops if c != crop_profile['name']]

    intelligence = session.get('soil_crop_analysis', None)
    has_intelligence = bool(intelligence and intelligence.get('crop') and intelligence['crop'].get('name') == selected_crop_name)
    error = None
    success_message = None
    notification = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_location':
            farmer_name_inp = request.form.get('farmer_name', '').strip()
            survey_number_inp = request.form.get('survey_number', '').strip()
            if farmer_name_inp:
                session['farmer_name'] = farmer_name_inp
            if survey_number_inp:
                session['survey_number'] = survey_number_inp

            village = request.form.get('village', '').strip()
            district = request.form.get('district', '').strip()
            state = request.form.get('state', '').strip()
            if village or district or state:
                user_location = {
                    'village': village or user_location.get('village', ''),
                    'district': district or user_location.get('district', ''),
                    'state': state or user_location.get('state', 'Tamil Nadu'),
                    'farmer_name': session.get('farmer_name', ''),
                    'survey_number': session.get('survey_number', '')
                }
                session['user_location'] = user_location
                notification = f"Location and farm identity updated for {user_location['village']}."
                if has_soil_data and crop_profile:
                    intelligence = generate_crop_soil_intelligence(crop_profile['name'], soil_data, user_location)
                    session['soil_crop_analysis'] = intelligence
                    has_intelligence = True

        elif action == 'analyze':
            if not has_soil_data:
                error = "Please complete the Soil Lab analysis first."
            elif not crop_profile:
                error = "Please select a crop first."
            elif not user_location.get('village', '').strip() or not user_location.get('district', '').strip() or not user_location.get('state', '').strip():
                error = "Please enter Village, District and State."
            else:
                intelligence = generate_crop_soil_intelligence(crop_profile['name'], soil_data, user_location)
                session['soil_crop_analysis'] = intelligence
                has_intelligence = True
                success_message = f"Intelligence report generated for {crop_profile['name']} at {user_location['village']}."

                # Record activity in SQLite history
                crop_suit = intelligence.get('crop_analysis', {})
                suit_status = crop_suit.get('suitability_status', 'Evaluated')
                record_activity(
                    'CROP_ANALYSIS',
                    f"Evaluated {crop_profile['name']} suitability: {suit_status} for current soil",
                    crop=crop_profile['name'],
                    village=user_location.get('village'),
                    district=user_location.get('district'),
                    state=user_location.get('state'),
                    farmer_name=session.get('farmer_name'),
                    survey_number=session.get('survey_number')
                )

    combined_data = combine_crop_and_soil(
        crop_profile['name'] if crop_profile else selected_crop_name,
        soil_data,
        user_location
    )
    session['combined_analysis'] = combined_data

    context = {
        'user': get_farmer_context(),
        'page_title': 'Crop Advisor',
        'crops': crops,
        'selected_crop': crop_profile['name'] if crop_profile else selected_crop_name,
        'crop_profile': crop_profile,
        'location': user_location,
        'soil_data': soil_data,
        'has_soil_data': has_soil_data,
        'report_summary': report_summary,
        'intelligence': intelligence,
        'has_intelligence': has_intelligence,
        'error': error,
        'success_message': success_message,
        'notification': notification,
        'param_display': PARAM_DISPLAY,
        'combined_data': combined_data
    }
    return render_template('crop_advisor.html', **context)


@app.route('/bioboost', methods=['GET', 'POST'])
def bioboost():
    """BioBoost - Biological nutrient management and soil health decision support"""
    selected_crop = session.get('selected_crop')
    soil_data = session.get('soil_data')
    user_location = session.get('user_location', {
        'village': 'Kammadikottai',
        'district': 'Thoothukudi',
        'state': 'Tamil Nadu'
    })
    intelligence = session.get('soil_crop_analysis')

    has_crop = bool(selected_crop)
    has_soil = any(v is not None for v in soil_data.values()) if (soil_data and isinstance(soil_data, dict)) else False

    no_crop_selected = not has_crop
    no_soil_data = not has_soil

    crop_profile = None
    growth_stages = []
    selected_stage = None
    bioboost_analysis = None

    if has_crop and has_soil:
        crop_profile = get_crop_profile(selected_crop)
        if not crop_profile:
            crops = load_crops()
            crop_profile = crops[0] if crops else None
            selected_crop = crop_profile['name'] if crop_profile else 'Moringa'

        growth_stages = crop_profile.get('growth_stages', ['Vegetative Growth']) if crop_profile else ['Vegetative Growth']
        
        selected_stage = request.args.get('stage') or request.form.get('stage') or session.get('bioboost_stage') or growth_stages[0]
        if selected_stage not in growth_stages:
            selected_stage = growth_stages[0]

        session['bioboost_stage'] = selected_stage

        bioboost_analysis = generate_bioboost_guidance(
            selected_crop,
            selected_stage,
            soil_data,
            user_location,
            intelligence
        )
        session['bioboost_analysis'] = bioboost_analysis

        # Record activity in SQLite history
        record_activity(
            'BIOBOOST_ANALYSIS',
            f"Generated biological nutrient guidance for {selected_crop} ({selected_stage})",
            crop=selected_crop,
            village=user_location.get('village'),
            district=user_location.get('district'),
            state=user_location.get('state')
        )

    context = {
        'user': get_farmer_context(),
        'page_title': 'BioBoost',
        'has_crop': has_crop,
        'has_soil': has_soil,
        'no_crop_selected': no_crop_selected,
        'no_soil_data': no_soil_data,
        'selected_crop': selected_crop,
        'crop_profile': crop_profile,
        'growth_stages': growth_stages,
        'selected_stage': selected_stage,
        'location': user_location,
        'soil_data': soil_data,
        'bioboost': bioboost_analysis
    }
    return render_template('bioboost.html', **context)


@app.route('/pest-advisor', methods=['GET', 'POST'])
def pest_advisor():
    """Pest & Disease Advisor - Integrated Pest Management Decision Support"""
    crops = load_crops()
    selected_crop = request.args.get('crop') or request.form.get('crop') or session.get('selected_crop')
    
    no_crop_selected = not bool(selected_crop)
    issues = []
    selected_issue_id = None
    selected_issue = None
    selected_severity = request.args.get('severity') or request.form.get('severity') or 'Not sure'
    ipm_analysis = None

    if not no_crop_selected:
        issues = get_crop_ipm_issues(selected_crop)
        
        selected_issue_id = request.args.get('issue') or request.form.get('issue')
        if not selected_issue_id:
            saved_ipm = session.get('ipm_analysis')
            if saved_ipm and saved_ipm.get('crop') == selected_crop:
                selected_issue_id = saved_ipm.get('issue_id')
                if not request.args.get('severity') and not request.form.get('severity'):
                    selected_severity = saved_ipm.get('severity', 'Not sure')
            elif issues:
                selected_issue_id = issues[0].get('id')

        if selected_issue_id:
            selected_issue = get_issue_by_id(selected_crop, selected_issue_id)
            if not selected_issue and issues:
                selected_issue = issues[0]
                selected_issue_id = selected_issue.get('id')

        if selected_issue:
            ipm_analysis = generate_ipm_plan(selected_crop, selected_issue_id, selected_severity)
            session['ipm_analysis'] = ipm_analysis

            # Record activity in SQLite history
            loc = session.get('user_location') or {}
            record_activity(
                'IPM_ASSESSMENT',
                f"Assessed {selected_issue['name']} ({selected_severity}) with IPM protocol",
                crop=selected_crop,
                village=loc.get('village'),
                district=loc.get('district'),
                state=loc.get('state')
            )

    context = {
        'user': get_farmer_context(),
        'page_title': 'Pest & Disease Advisor',
        'crops': crops,
        'selected_crop': selected_crop,
        'no_crop_selected': no_crop_selected,
        'issues': issues,
        'selected_issue_id': selected_issue_id,
        'selected_issue': selected_issue,
        'selected_severity': selected_severity,
        'ipm': ipm_analysis
    }
    return render_template('pest_advisor.html', **context)


@app.route('/weather', methods=['GET', 'POST'])
def weather():
    """Weather & Farm Forecast - Real-time and 7-day weather intelligence"""
    if request.method == 'POST':
        village = request.form.get('village', '').strip()
        district = request.form.get('district', '').strip()
        state = request.form.get('state', '').strip()
        if village or district or state:
            user_location = {
                'village': village,
                'district': district,
                'state': state or 'Tamil Nadu'
            }
            session['user_location'] = user_location

            # Record weather search activity
            loc_str = f"{village}, {district}".strip(', ')
            record_activity(
                'WEATHER_LOOKUP',
                f"Checked real-time weather and 7-day forecast for {loc_str or 'Farm'}",
                crop=session.get('selected_crop'),
                village=village,
                district=district,
                state=state
            )

    user_location = session.get('user_location', {
        'village': 'Kammadikottai',
        'district': 'Thoothukudi',
        'state': 'Tamil Nadu'
    })

    selected_crop = session.get('selected_crop')
    weather_data = get_weather(user_location)

    insights = []
    alerts = []
    crop_context = None

    if weather_data and weather_data.get('success'):
        insights = generate_weather_insights(weather_data)
        alerts = generate_weather_alerts(weather_data)
        if selected_crop:
            crop_context = generate_crop_weather_context(selected_crop, weather_data)

    context = {
        'user': get_farmer_context(),
        'page_title': 'Weather & Forecast',
        'location': user_location,
        'selected_crop': selected_crop,
        'weather': weather_data,
        'insights': insights,
        'alerts': alerts,
        'crop_context': crop_context
    }
    return render_template('weather.html', **context)


@app.route('/monsoon', methods=['GET', 'POST'])
def monsoon():
    """Monsoon Outlook - Official IMD Meteorological Guidance & Farm Decision Support"""
    if request.method == 'POST':
        village = request.form.get('village', '').strip()
        district = request.form.get('district', '').strip()
        state = request.form.get('state', '').strip()
        if village or district or state:
            user_location = {
                'village': village,
                'district': district,
                'state': state or 'Tamil Nadu'
            }
            session['user_location'] = user_location

            # Record monsoon lookup activity
            loc_str = f"{district}, {state}".strip(', ')
            record_activity(
                'MONSOON_LOOKUP',
                f"Consulted official IMD seasonal monsoon bulletin for {loc_str or 'Region'}",
                crop=session.get('selected_crop'),
                village=village,
                district=district,
                state=state
            )

    user_location = session.get('user_location')
    selected_crop = session.get('selected_crop')

    weather_data = None
    if user_location:
        weather_data = get_weather(user_location)

    state_for_monsoon = user_location.get('state') if user_location else 'Tamil Nadu'
    district_for_monsoon = user_location.get('district') if user_location else None
    monsoon_data = get_official_monsoon_bulletin(state=state_for_monsoon, district=district_for_monsoon)

    interpretation = interpret_monsoon_outlook(
        monsoon_data,
        crop_name=selected_crop,
        location=user_location,
        weather_data=weather_data
    )

    session['monsoon_outlook'] = {
        'status': monsoon_data.get('status', 'Unavailable'),
        'season': monsoon_data.get('season', 'Monsoon'),
        'title': monsoon_data.get('title', 'Official Seasonal Outlook'),
        'published_date': monsoon_data.get('published_date', '')
    }

    context = {
        'user': get_farmer_context(),
        'page_title': 'Monsoon Outlook',
        'location': user_location,
        'selected_crop': selected_crop,
        'monsoon': monsoon_data,
        'interpretation': interpretation,
        'weather': weather_data
    }
    return render_template('monsoon.html', **context)


@app.route('/crop-guide')
def crop_guide():
    """Crop Guide - Comprehensive crop information and personalized farm report center"""
    all_crops = load_crops()
    
    requested_crop = request.args.get('crop', '').strip()
    if requested_crop and validate_crop(requested_crop):
        selected_crop = requested_crop
        session['selected_crop'] = selected_crop
    else:
        selected_crop = session.get('selected_crop') or (all_crops[0]['name'] if all_crops else 'Moringa')

    crop_profile = get_crop_profile(selected_crop) or (all_crops[0] if all_crops else {})
    user_location = session.get('user_location')
    soil_data = session.get('soil_data')
    has_soil = bool(soil_data and any(soil_data.get(k) is not None for k in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']))

    soil_analysis = None
    crop_suitability = None
    existing_intel = session.get('soil_crop_analysis')
    if existing_intel and isinstance(existing_intel, dict):
        soil_analysis = existing_intel.get('soil_analysis')
        if existing_intel.get('crop') and existing_intel['crop'].get('name') == selected_crop:
            crop_suitability = existing_intel.get('crop_analysis')

    if not soil_analysis and has_soil:
        soil_analysis = analyze_soil(soil_data)

    if not crop_suitability and has_soil and selected_crop:
        combined = combine_crop_and_soil(selected_crop, soil_data, user_location)
        intel = generate_crop_soil_intelligence(combined)
        crop_suitability = intel.get('crop_analysis')

    bioboost = session.get('bioboost_analysis')
    ipm = session.get('ipm_analysis')

    weather_data = None
    if user_location:
        weather_data = get_weather(user_location)

    monsoon_data = None
    monsoon_interp = None
    if user_location:
        monsoon_data = get_official_monsoon_bulletin(state=user_location.get('state'), district=user_location.get('district'))
        monsoon_interp = interpret_monsoon_outlook(monsoon_data, crop_name=selected_crop, location=user_location, weather_data=weather_data)

    context = {
        'user': get_farmer_context(),
        'page_title': 'Crop Guide & Farm Report',
        'crops': all_crops,
        'selected_crop': selected_crop,
        'crop_profile': crop_profile,
        'location': user_location,
        'soil_data': soil_data,
        'has_soil': has_soil,
        'soil_analysis': soil_analysis,
        'crop_suitability': crop_suitability,
        'bioboost': bioboost,
        'ipm': ipm,
        'weather': weather_data,
        'monsoon': monsoon_data,
        'monsoon_interpretation': monsoon_interp
    }
    return render_template('crop_guide.html', **context)


@app.route('/generate-report')
def generate_report():
    """Generate and download a comprehensive, professional farmer PDF report"""
    # 1. Capture Identity & Query Overrides
    req_farmer = request.args.get('farmer_name', '').strip()
    req_survey = request.args.get('survey_number', '').strip()
    req_stage = request.args.get('growth_stage', '').strip()

    if req_farmer:
        session['farmer_name'] = req_farmer
    if req_survey:
        session['survey_number'] = req_survey
    if req_stage:
        session['growth_stage'] = req_stage

    # 2. Selected Crop
    requested_crop = request.args.get('crop', '').strip()
    if requested_crop and validate_crop(requested_crop):
        selected_crop = requested_crop
        session['selected_crop'] = selected_crop
    else:
        selected_crop = session.get('selected_crop') or 'Moringa'

    crop_profile = get_crop_profile(selected_crop) if selected_crop else None

    # 3. Location & Identity
    user_location = session.get('user_location') or {
        'village': 'Kammadikottai',
        'district': 'Thoothukudi',
        'state': 'Tamil Nadu'
    }
    farmer_name = session.get('farmer_name') or user_location.get('farmer_name') or ''
    survey_number = session.get('survey_number') or user_location.get('survey_number') or ''
    growth_stage = session.get('growth_stage') or user_location.get('growth_stage') or 'Active Vegetative Stage'

    # 4. Soil Data & Analysis
    soil_data = session.get('soil_data')
    if soil_data and isinstance(soil_data, dict):
        if 'electrical_conductivity' in soil_data and 'ec' not in soil_data:
            soil_data['ec'] = soil_data['electrical_conductivity']
        if 'ec' in soil_data and 'electrical_conductivity' not in soil_data:
            soil_data['electrical_conductivity'] = soil_data['ec']

    has_soil = bool(soil_data and any(soil_data.get(k) is not None for k in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']))

    soil_analysis = None
    if has_soil:
        soil_analysis = analyze_soil(soil_data)
    elif session.get('soil_crop_analysis'):
        existing_intel = session.get('soil_crop_analysis')
        soil_analysis = existing_intel.get('soil_analysis')

    # 5. Crop Suitability
    crop_suitability = None
    if has_soil and selected_crop and crop_profile and soil_analysis:
        crop_suitability = evaluate_crop_suitability(crop_profile, soil_analysis)
    elif session.get('soil_crop_analysis'):
        existing_intel = session.get('soil_crop_analysis')
        if existing_intel.get('crop') and existing_intel['crop'].get('name') == selected_crop:
            crop_suitability = existing_intel.get('suitability') or existing_intel.get('crop_analysis')

    # 6. BioBoost
    bioboost = session.get('bioboost_analysis')
    if not bioboost or (bioboost.get('crop') and bioboost.get('crop') != selected_crop):
        try:
            bioboost = generate_bioboost_guidance(selected_crop, growth_stage, soil_data, user_location)
        except Exception:
            pass

    # 7. IPM
    ipm = session.get('ipm_analysis')
    if not ipm or (ipm.get('crop') and ipm.get('crop') != selected_crop):
        try:
            issues = get_crop_ipm_issues(selected_crop)
            if issues:
                ipm = generate_ipm_plan(selected_crop, issues[0].get('id', issues[0].get('name', '')), 'LOW')
        except Exception:
            pass

    # 8. Weather & Monsoon
    weather_data = None
    if user_location:
        weather_data = get_weather(user_location)

    monsoon_data = None
    if user_location:
        monsoon_data = get_official_monsoon_bulletin(state=user_location.get('state'), district=user_location.get('district'))

    user_context = get_farmer_context()
    selected_crops = user_context.get('selected_crops') or [selected_crop]
    crop_stages = user_context.get('crop_growth_stages') or {}

    report_payload = {
        'farmer_name': farmer_name,
        'survey_number': survey_number,
        'growth_stage': growth_stage,
        'location': user_location,
        'selected_crop': selected_crop,
        'selected_crops': selected_crops,
        'crop_growth_stages': crop_stages,
        'crop_profile': crop_profile,
        'soil_data': soil_data,
        'soil_analysis': soil_analysis,
        'crop_suitability': crop_suitability,
        'bioboost': bioboost,
        'ipm': ipm,
        'weather': weather_data,
        'monsoon': monsoon_data
    }

    try:
        pdf_stream = generate_farm_report_pdf(report_payload)
        
        # Record report generation activity in SQLite history
        loc = user_location or {}
        crop_desc = ", ".join(selected_crops) if len(selected_crops) > 1 else (selected_crop or 'general farm')
        record_activity(
            'REPORT_GENERATED',
            f"Generated comprehensive agricultural PDF report for {crop_desc}",
            crop=selected_crops if len(selected_crops) > 1 else selected_crop,
            village=loc.get('village'),
            district=loc.get('district'),
            state=loc.get('state'),
            farmer_name=farmer_name,
            survey_number=survey_number
        )
    except Exception as e:
        app.logger.error(f"Error in generate_farm_report_pdf: {e}")
        pdf_stream = generate_farm_report_pdf({})

    if selected_crop:
        filename = f"AgriAI_Farm_Report_{secure_filename(selected_crop)}.pdf"
    else:
        filename = "AgriAI_Farm_Report.pdf"

    return send_file(
        pdf_stream,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@app.route('/history')
def history():
    """History - View chronological farmer activities, reports, and recommendations"""
    filter_type = request.args.get('type', '').strip() or None
    filter_crop = request.args.get('crop', '').strip() or None
    
    activities = get_recent_activities(limit=50, activity_type=filter_type, crop=filter_crop)
    stats = get_activity_stats()
    all_crops = [c['name'] for c in load_crops()]

    context = {
        'user': get_farmer_context(),
        'page_title': 'Farm History',
        'activities': activities,
        'stats': stats,
        'filter_type': filter_type,
        'filter_crop': filter_crop,
        'all_crops': all_crops
    }
    return render_template('history.html', **context)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors with friendly UI"""
    return render_template('base.html', error='The requested page could not be found. Please use the navigation menu to return to your farm dashboard.'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors with friendly UI without stack traces"""
    return render_template('base.html', error='An unexpected error occurred while processing your request. Please try again or return to the dashboard.'), 500


# ============================================================================
# TEMPLATE CONTEXT PROCESSORS
# ============================================================================

@app.context_processor
def inject_user():
    """Make farmer context available to all templates"""
    return dict(user=get_farmer_context())


if __name__ == '__main__':
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/images', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    os.makedirs('uploads/soil_reports', exist_ok=True)
    
    app.run(debug=True, port=5001)
