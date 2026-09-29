"""
AgriAI - Integrated Pest Management (IPM) Engine
Provides structured decision support for crop pests and diseases based on
ICAR, TNAU, and DPPQ&S IPM guidelines.
"""

import os
import json
from typing import Dict, List, Optional, Any

IPM_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ipm.json')

_IPM_CACHE: Optional[Dict[str, Any]] = None


def load_ipm_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load IPM database from data/ipm.json with in-memory caching."""
    global _IPM_CACHE
    if _IPM_CACHE is not None:
        return _IPM_CACHE

    if not os.path.exists(IPM_FILE):
        return {}

    try:
        with open(IPM_FILE, 'r', encoding='utf-8') as f:
            _IPM_CACHE = json.load(f)
            return _IPM_CACHE
    except Exception:
        return {}


def get_supported_crops() -> List[str]:
    """Return list of crops with IPM datasets."""
    data = load_ipm_data()
    return list(data.keys())


def get_crop_ipm_issues(crop_name: str) -> List[Dict[str, Any]]:
    """Return all pest and disease entries for a specific crop."""
    data = load_ipm_data()
    if not crop_name:
        return []

    # Case-insensitive crop lookup
    for key, issues in data.items():
        if key.strip().lower() == crop_name.strip().lower():
            return issues
    return []


def get_issue_by_id(crop_name: str, issue_id: str) -> Optional[Dict[str, Any]]:
    """Find a specific pest or disease entry by crop name and issue ID."""
    issues = get_crop_ipm_issues(crop_name)
    if not issues:
        return None

    for issue in issues:
        if issue.get('id') == issue_id:
            return issue

    # If issue_id is matching name instead of id
    for issue in issues:
        if issue.get('name', '').lower() == issue_id.lower():
            return issue

    return None


def evaluate_risk(severity: str, issue_type: str, issue_name: str) -> Dict[str, str]:
    """
    Deterministically evaluate risk level and rationale based on observed severity.
    'Not sure' triggers diagnostic caution rather than confident action.
    """
    sev_clean = (severity or '').strip().upper()

    if sev_clean == 'HIGH':
        return {
            'level': 'HIGH',
            'code': 'danger',
            'badge': 'badge-danger',
            'reason': f"Extensive {issue_type.lower()} damage reported. Field action threshold is crossed; immediate non-chemical and targeted intervention is warranted to prevent economic crop failure."
        }
    elif sev_clean == 'MEDIUM':
        return {
            'level': 'MEDIUM',
            'code': 'warning',
            'badge': 'badge-warning',
            'reason': f"Moderate {issue_type.lower()} presence observed. Population or lesions are expanding; implement cultural and biological controls promptly and scout field every 2–3 days."
        }
    elif sev_clean == 'LOW':
        return {
            'level': 'LOW',
            'code': 'success',
            'badge': 'badge-success',
            'reason': f"Isolated or early-stage symptoms. Current damage is below economic injury levels; focus on preventive practices, beneficial insect conservation, and routine weekly monitoring."
        }
    else:
        # 'Not sure' or unrecognized input
        return {
            'level': 'UNCERTAIN / MODERATE CAUTION',
            'code': 'warning',
            'badge': 'badge-warning',
            'reason': f"Symptom severity is uncertain. Many physiological disorders and nutritional deficiencies mimic {issue_type.lower()} symptoms. Confirm diagnosis locally before applying any chemical intervention."
        }


def generate_ipm_plan(crop_name: str, issue_id: str, severity: str = 'Not sure') -> Optional[Dict[str, Any]]:
    """
    Generate an Integrated Pest Management action plan for a selected crop and issue.
    """
    issues = get_crop_ipm_issues(crop_name)
    if not issues:
        return None

    issue = get_issue_by_id(crop_name, issue_id)
    if not issue:
        # Fallback to first available issue for the crop
        issue = issues[0]

    risk_info = evaluate_risk(severity, issue.get('type', 'Pest'), issue.get('name', 'Issue'))

    # Format chemical control safely
    raw_chem = issue.get('chemical_control', {})
    if isinstance(raw_chem, dict) and raw_chem.get('supported'):
        chemical_control = {
            'supported': True,
            'active_ingredients': raw_chem.get('active_ingredients', []),
            'target': raw_chem.get('target', 'Target pest or pathogen stage'),
            'consideration_criteria': raw_chem.get('consideration_criteria', 'Consider only when non-chemical controls fail to curb spread.'),
            'safety_notes': raw_chem.get('safety_notes', 'Follow current locally approved label and agricultural extension recommendation.')
        }
    else:
        chemical_control = {
            'supported': False,
            'active_ingredients': [],
            'target': 'Not applicable for this issue or established chemical cures are unproven.',
            'consideration_criteria': 'Chemical sprays are not recommended for this problem.',
            'safety_notes': 'Use only locally approved products according to the current product label and agricultural extension guidance.'
        }

    return {
        'crop': crop_name,
        'issue_id': issue.get('id'),
        'issue_name': issue.get('name'),
        'type': issue.get('type', 'Pest'),
        'description': issue.get('description', ''),
        'severity': severity if severity in ['LOW', 'MEDIUM', 'HIGH', 'Not sure'] else 'Not sure',
        'risk': risk_info,
        'symptoms': issue.get('symptoms', []),
        'risk_conditions': issue.get('risk_conditions', []),
        'monitoring': issue.get('monitoring', []),
        'prevention': issue.get('prevention', []),
        'cultural_control': issue.get('cultural_control', []),
        'mechanical_control': issue.get('mechanical_control', []),
        'biological_control': issue.get('biological_control', []),
        'chemical_control': chemical_control,
        'severity_levels': issue.get('severity_levels', []),
        'when_to_seek_help': [
            "Symptoms are rapidly worsening or spreading across adjacent blocks",
            "Severe leaf defoliation, stem breakage, or fruit rot exceeding economic thresholds",
            "Uncertain diagnosis or overlapping pest and pathogen symptoms on the same plant",
            "Beneficial biological or mechanical practices fail to reduce damage within 5–7 days"
        ],
        'extension_contacts': [
            "Local Assistant Agricultural Officer (AAO) / Block Agricultural Extension Office",
            "District Krishi Vigyan Kendra (KVK) Farm Science Center",
            "State Agricultural University Plant Clinic (e.g. TNAU / ICAR Research Stations)"
        ],
        'disclaimer': (
            "AgriAI provides preliminary IPM decision-support guidance based on the selected crop, "
            "reported observations and available reference information. Pest or disease identification "
            "should be confirmed when uncertain. Follow current local agricultural recommendations "
            "and product labels for any input application."
        )
    }
