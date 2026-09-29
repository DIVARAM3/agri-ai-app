"""
AgriAI - History & Activity Storage Engine
Lightweight, thread-safe SQLite persistence for farmer activities and farm reports.
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
DEFAULT_DB_PATH = os.path.join(DB_DIR, 'history.db')

ACTIVITY_ICONS = {
    'SOIL_ANALYSIS': '🧪',
    'CROP_ANALYSIS': '🌾',
    'BIOBOOST_ANALYSIS': '🌿',
    'IPM_ASSESSMENT': '🐛',
    'WEATHER_LOOKUP': '⛅',
    'MONSOON_LOOKUP': '🌧️',
    'REPORT_GENERATED': '📄'
}

ACTIVITY_TITLES = {
    'SOIL_ANALYSIS': 'Soil Analysis Completed',
    'CROP_ANALYSIS': 'Crop Analysis Completed',
    'BIOBOOST_ANALYSIS': 'BioBoost Analysis Completed',
    'IPM_ASSESSMENT': 'IPM Assessment Completed',
    'WEATHER_LOOKUP': 'Weather Checked',
    'MONSOON_LOOKUP': 'Monsoon Outlook Viewed',
    'REPORT_GENERATED': 'Farm Report Generated'
}

ACTIVITY_BADGES = {
    'SOIL_ANALYSIS': 'badge-primary',
    'CROP_ANALYSIS': 'badge-success',
    'BIOBOOST_ANALYSIS': 'badge-success',
    'IPM_ASSESSMENT': 'badge-warning',
    'WEATHER_LOOKUP': 'badge-info',
    'MONSOON_LOOKUP': 'badge-info',
    'REPORT_GENERATED': 'badge-primary'
}


def get_db_connection(db_path=None):
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initialize the SQLite database with activities table and required columns."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS farm_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_type TEXT NOT NULL,
                    crop TEXT,
                    village TEXT,
                    district TEXT,
                    state TEXT,
                    farmer_name TEXT,
                    survey_number TEXT,
                    description TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_created 
                ON farm_activities(created_at DESC)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_activity_type 
                ON farm_activities(activity_type)
            ''')

            # Ensure columns exist if table was already created
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(farm_activities)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if 'farmer_name' not in existing_cols:
                conn.execute("ALTER TABLE farm_activities ADD COLUMN farmer_name TEXT")
            if 'survey_number' not in existing_cols:
                conn.execute("ALTER TABLE farm_activities ADD COLUMN survey_number TEXT")
    finally:
        conn.close()


def record_activity(activity_type, description="", crop=None, village=None, district=None, state=None, farmer_name=None, survey_number=None, deduplicate_window_sec=60, db_path=None):
    """
    Record a meaningful farmer activity.
    De-duplicates identical activities within deduplicate_window_sec to prevent refresh flooding.
    Supports single crop or multi-crop list.
    """
    if isinstance(crop, list):
        crop = ", ".join(str(c) for c in crop if c)
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            # Check for identical recent activity within deduplication window
            if deduplicate_window_sec and deduplicate_window_sec > 0:
                cursor = conn.execute('''
                    SELECT id, created_at FROM farm_activities
                    WHERE activity_type = ? AND description = ? AND (crop = ? OR (crop IS NULL AND ? IS NULL))
                    ORDER BY id DESC LIMIT 1
                ''', (activity_type, description, crop, crop))
                row = cursor.fetchone()
                if row:
                    try:
                        # SQLite CURRENT_TIMESTAMP is UTC 'YYYY-MM-DD HH:MM:SS'
                        ts_str = row['created_at']
                        if ts_str:
                            last_time = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                            now_time = datetime.now(timezone.utc)
                            if (now_time - last_time).total_seconds() < deduplicate_window_sec:
                                return row['id']  # Skip duplicate, return existing ID
                    except Exception:
                        pass

            cursor = conn.execute('''
                INSERT INTO farm_activities (activity_type, crop, village, district, state, farmer_name, survey_number, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (activity_type, crop, village, district, state, farmer_name, survey_number, description))
            return cursor.lastrowid
    finally:
        conn.close()


def get_recent_activities(limit=50, activity_type=None, crop=None, db_path=None):
    """Retrieve chronologically ordered activities with formatted presentation fields."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        query = 'SELECT * FROM farm_activities'
        params = []
        conditions = []

        if activity_type:
            conditions.append('activity_type = ?')
            params.append(activity_type)
        if crop:
            conditions.append('crop = ?')
            params.append(crop)

        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        query += ' ORDER BY id DESC LIMIT ?'
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            loc_parts = [p for p in [r['village'], r['district'], r['state']] if p]
            loc_str = ', '.join(loc_parts) if loc_parts else None

            # Format created_at nicely
            created_raw = r['created_at'] or ''
            formatted_date = created_raw
            formatted_time = ''
            try:
                dt = datetime.strptime(created_raw, '%Y-%m-%d %H:%M:%S')
                formatted_date = dt.strftime('%d %b %Y')
                formatted_time = dt.strftime('%I:%M %p')
            except Exception:
                pass

            act_type = r['activity_type']
            results.append({
                'id': r['id'],
                'activity_type': act_type,
                'title': ACTIVITY_TITLES.get(act_type, act_type.replace('_', ' ').title()),
                'icon': ACTIVITY_ICONS.get(act_type, '📌'),
                'badge_class': ACTIVITY_BADGES.get(act_type, 'badge-primary'),
                'crop': r['crop'],
                'village': r['village'],
                'district': r['district'],
                'state': r['state'],
                'farmer_name': r['farmer_name'] if 'farmer_name' in r.keys() else None,
                'survey_number': r['survey_number'] if 'survey_number' in r.keys() else None,
                'location': loc_str,
                'description': r['description'],
                'created_at': created_raw,
                'date': formatted_date,
                'time': formatted_time
            })
        return results
    finally:
        conn.close()


def get_activity_stats(db_path=None):
    """Get high-level summary counts for farm activity history."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute('SELECT COUNT(*) as total FROM farm_activities')
        total = cursor.fetchone()['total']

        cursor = conn.execute('SELECT COUNT(DISTINCT crop) as distinct_crops FROM farm_activities WHERE crop IS NOT NULL AND crop != ""')
        distinct_crops = cursor.fetchone()['distinct_crops']

        cursor = conn.execute('SELECT activity_type, COUNT(*) as count FROM farm_activities GROUP BY activity_type')
        type_counts = {r['activity_type']: r['count'] for r in cursor.fetchall()}

        return {
            'total_activities': total,
            'crops_tracked': distinct_crops,
            'type_counts': type_counts
        }
    finally:
        conn.close()


def clear_history(db_path=None):
    """Clear all records from activities table (useful for clean testing)."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute('DELETE FROM farm_activities')
    finally:
        conn.close()


clear_history_for_testing = clear_history
