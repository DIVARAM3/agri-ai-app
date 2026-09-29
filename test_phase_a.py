"""
AGRIORA - Phase A Comprehensive Test Suite (test_phase_a.py)
Verifies all 20 required points for Phase A: Farmer Guide + Multi-Crop Architecture.
"""

import io
import json
import unittest
from datetime import datetime

from app import app, get_farmer_guide_status
from engine.crop_engine import (
    load_crops,
    get_crop_categories,
    search_crops,
    get_crop_profile,
    evaluate_multiple_crops,
    evaluate_crop_suitability,
)
from engine.bioboost_engine import generate_bioboost_guidance
from engine.ipm_engine import get_crop_ipm_issues
from engine.soil_engine import analyze_soil
from engine.history_manager import (
    record_activity,
    get_recent_activities,
    clear_history_for_testing,
)
from engine.report_generator import generate_farm_report_pdf


class TestPhaseAFarmerGuideMultiCrop(unittest.TestCase):
    """Test suite covering the 20 requirements of Phase A."""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-phase-a-agriora'

    def setUp(self):
        self.client = app.test_client()
        clear_history_for_testing()

    # -------------------------------------------------------------------------
    # 1. 30 Crop Catalog Loads
    # -------------------------------------------------------------------------
    def test_01_crop_catalog_loads_30_crops(self):
        """1. Verify catalog contains at least 30 crops with required agronomic fields."""
        crops = load_crops()
        self.assertGreaterEqual(len(crops), 30)

        required_crops = [
            "Rice", "Maize", "Sorghum", "Pearl Millet", "Finger Millet",
            "Chickpea", "Black Gram", "Green Gram", "Pigeon Pea", "Cowpea",
            "Groundnut", "Sesame", "Sunflower", "Soybean",
            "Tomato", "Chilli", "Brinjal", "Okra", "Onion",
            "Cabbage", "Cauliflower", "Carrot", "Radish",
            "Bitter Gourd", "Bottle Gourd", "Cucumber", "Pumpkin",
            "Moringa", "Banana", "Sugarcane"
        ]
        crop_names = [c['name'] for c in crops]
        for rc in required_crops:
            self.assertIn(rc, crop_names, f"Required crop '{rc}' must be in catalog")

        # Check required fields
        for c in crops:
            self.assertIn('name', c)
            self.assertIn('category', c)
            self.assertIn('growth_duration', c)
            self.assertIn('water_requirement', c)
            self.assertIn('preferred_ph', c)
            self.assertIn('growth_stages', c)

    # -------------------------------------------------------------------------
    # 2. Crop Categories
    # -------------------------------------------------------------------------
    def test_02_crop_categories(self):
        """2. Verify standard categories: Cereals, Pulses, Oilseeds, Vegetables, Commercial / Perennial."""
        cats = get_crop_categories()
        expected = ["Cereals", "Pulses", "Oilseeds", "Vegetables", "Commercial / Perennial"]
        for exp in expected:
            self.assertIn(exp, cats)

        # Ensure each category has valid crops
        for exp in expected:
            matches = search_crops("", category=exp)
            self.assertGreater(len(matches), 0, f"Category '{exp}' should contain crops")

    # -------------------------------------------------------------------------
    # 3. Crop Search & Filtering
    # -------------------------------------------------------------------------
    def test_03_crop_search_and_api(self):
        """3. Verify crop search by query, category, and JSON API endpoint."""
        # Function search
        moringa_results = search_crops("moring")
        self.assertEqual(len(moringa_results), 1)
        self.assertEqual(moringa_results[0]['name'], "Moringa")

        veg_results = search_crops("", category="Vegetables")
        self.assertGreaterEqual(len(veg_results), 10)

        # API search endpoint
        res = self.client.get('/api/crops?q=tom&cat=Vegetables')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data.get('success'))
        self.assertGreaterEqual(len(data.get('crops', [])), 1)
        self.assertEqual(data['crops'][0]['name'], "Tomato")

    # -------------------------------------------------------------------------
    # 4. Single Crop Selection
    # -------------------------------------------------------------------------
    def test_04_single_crop_selection(self):
        """4. Verify selecting 1 crop persists in session."""
        with self.client.session_transaction() as sess:
            sess['farmer_profile'] = {'farmer_name': 'Murugan'}
            sess['farm_details'] = {'farm_name': 'Kammadikottai Field'}
            sess['guide_step'] = 5

        res = self.client.post('/farmer-guide?step=5', data={
            'crops': ['Moringa']
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('selected_crops'), ['Moringa'])
            self.assertEqual(sess.get('selected_crop'), 'Moringa')
            self.assertEqual(sess.get('guide_step'), 6)

    # -------------------------------------------------------------------------
    # 5. Multiple Crop Selection
    # -------------------------------------------------------------------------
    def test_05_multiple_crop_selection(self):
        """5. Verify selecting 3 crops persists correctly in session context."""
        with self.client.session_transaction() as sess:
            sess['guide_step'] = 5

        res = self.client.post('/farmer-guide?step=5', data={
            'crops': ['Moringa', 'Tomato', 'Chilli']
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('selected_crops'), ['Moringa', 'Tomato', 'Chilli'])
            # Primary crop is first selected
            self.assertEqual(sess.get('selected_crop'), 'Moringa')

    # -------------------------------------------------------------------------
    # 6. Removing Selected Crop
    # -------------------------------------------------------------------------
    def test_06_removing_selected_crop(self):
        """6. Verify user can deselect/remove a crop by posting updated list."""
        with self.client.session_transaction() as sess:
            sess['selected_crops'] = ['Moringa', 'Tomato', 'Chilli']
            sess['guide_step'] = 5

        # Farmer removes Chilli
        res = self.client.post('/farmer-guide?step=5', data={
            'crops': ['Moringa', 'Tomato']
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('selected_crops'), ['Moringa', 'Tomato'])

    # -------------------------------------------------------------------------
    # 7. Empty Crop Selection Validation
    # -------------------------------------------------------------------------
    def test_07_empty_crop_selection_validation(self):
        """7. Verify empty crop submission is rejected and stays on step 5."""
        with self.client.session_transaction() as sess:
            sess['guide_step'] = 5

        res = self.client.post('/farmer-guide?step=5', data={}, follow_redirects=False)
        # Should redirect back to step 5
        self.assertEqual(res.status_code, 302)
        self.assertIn('step=5', res.location)

    # -------------------------------------------------------------------------
    # 8. Multiple Growth Stages
    # -------------------------------------------------------------------------
    def test_08_multiple_growth_stages(self):
        """8. Verify distinct growth stages can be set and stored for each crop."""
        with self.client.session_transaction() as sess:
            sess['selected_crops'] = ['Moringa', 'Tomato', 'Chilli']
            sess['guide_step'] = 6

        res = self.client.post('/farmer-guide?step=6', data={
            'stage_Moringa': 'Vegetative Growth',
            'stage_Tomato': 'Flowering',
            'stage_Chilli': 'Fruiting'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            stages = sess.get('crop_growth_stages', {})
            self.assertEqual(stages.get('Moringa'), 'Vegetative Growth')
            self.assertEqual(stages.get('Tomato'), 'Flowering')
            self.assertEqual(stages.get('Chilli'), 'Fruiting')

    # -------------------------------------------------------------------------
    # 9. Farm Context Persistence
    # -------------------------------------------------------------------------
    def test_09_farm_context_persistence(self):
        """9. Verify farm profile, details, and location persist seamlessly."""
        # Step 1: Farmer Profile
        self.client.post('/farmer-guide?step=1', data={
            'farmer_name': 'Sundararajan',
            'farm_name': 'Green Horizons',
            'mobile_number': '9876543210'
        }, follow_redirects=True)

        # Step 2: Farm Details
        self.client.post('/farmer-guide?step=2', data={
            'farm_name': 'Green Horizons',
            'survey_number': 'SY-402/B',
            'farm_area': '3.5',
            'area_unit': 'Acre'
        }, follow_redirects=True)

        # Step 3: Location
        self.client.post('/farmer-guide?step=3', data={
            'village': 'Kammadikottai',
            'district': 'Thoothukudi',
            'state': 'Tamil Nadu'
        }, follow_redirects=True)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('farmer_profile', {}).get('farmer_name'), 'Sundararajan')
            self.assertEqual(sess.get('farm_details', {}).get('survey_number'), 'SY-402/B')
            self.assertEqual(sess.get('location', {}).get('district'), 'Thoothukudi')

    # -------------------------------------------------------------------------
    # 10. Farmer Guide Progress Calculation
    # -------------------------------------------------------------------------
    def test_10_farmer_guide_progress(self):
        """10. Verify progress calculation: step count, completion count, percentage."""
        with self.client.session_transaction() as sess:
            sess['guide_step'] = 5
            sess['guide_completed_steps'] = [1, 2, 3, 4]

        with self.client as c:
            c.get('/farmer-guide?step=5')
            from flask import session
            status = get_farmer_guide_status(session)
            self.assertEqual(status['current_step'], 5)
            self.assertEqual(status['completed_count'], 4)
            self.assertEqual(status['total_steps'], 13)
            self.assertAlmostEqual(status['progress_pct'], 30.76, delta=0.5)

    # -------------------------------------------------------------------------
    # 11. Resume Workflow
    # -------------------------------------------------------------------------
    def test_11_resume_workflow(self):
        """11. Verify visiting /farmer-guide without step params redirects to current progress."""
        with self.client.session_transaction() as sess:
            sess['guide_step'] = 4

        res = self.client.get('/farmer-guide')
        self.assertEqual(res.status_code, 302)
        self.assertIn('step=4', res.location)

    # -------------------------------------------------------------------------
    # 12. Multi-Crop Suitability
    # -------------------------------------------------------------------------
    def test_12_multi_crop_suitability(self):
        """12. Verify evaluate_multiple_crops evaluates crops against soil context independently."""
        soil_analysis = {
            'soil_health_index': 78,
            'soil_status': 'Good',
            'classification': 'Neutral Loam',
            'data': {'ph': 6.8, 'nitrogen': 240, 'phosphorus': 18, 'potassium': 210, 'organic_carbon': 0.65}
        }
        crops = ['Moringa', 'Tomato', 'Chickpea']
        stages = {'Moringa': 'Vegetative', 'Tomato': 'Flowering', 'Chickpea': 'Vegetative'}

        results = evaluate_multiple_crops(crops, soil_analysis, stages)
        self.assertEqual(len(results), 3)

        for r in results:
            self.assertIn('name', r)
            self.assertIn('score', r)
            self.assertIn('status', r)
            self.assertIn('category', r)
            self.assertIn('growth_stage', r)
            self.assertIn('concerns', r)
            self.assertIn('reasons', r)
            self.assertIsInstance(r['score'], (int, float))

    # -------------------------------------------------------------------------
    # 13. Multi-Crop BioBoost
    # -------------------------------------------------------------------------
    def test_13_multi_crop_bioboost(self):
        """13. Verify BioBoost generates crop-specific biological fertility guidance."""
        soil_data = {'ph': 6.8, 'nitrogen': 240, 'phosphorus': 18, 'potassium': 210, 'organic_carbon': 0.65}
        crops = ['Moringa', 'Tomato', 'Groundnut']

        for crop in crops:
            bio_res = generate_bioboost_guidance(crop, 'Vegetative', soil_data)
            self.assertIsNotNone(bio_res)
            self.assertIn('practices', bio_res)
            self.assertIn('biological_health', bio_res)
            self.assertIn('priorities', bio_res)

    # -------------------------------------------------------------------------
    # 14. Multi-Crop IPM
    # -------------------------------------------------------------------------
    def test_14_multi_crop_ipm(self):
        """14. Verify IPM provides verified pest/disease entries for each selected crop."""
        crops = ['Moringa', 'Tomato', 'Chilli', 'Rice']
        for crop in crops:
            issues = get_crop_ipm_issues(crop)
            self.assertIsInstance(issues, list)
            if issues:
                issue = issues[0]
                self.assertIn('name', issue)
                self.assertIn('symptoms', issue)
                self.assertIn('monitoring', issue)
                self.assertIn('cultural_control', issue)
                self.assertIn('biological_control', issue)

    # -------------------------------------------------------------------------
    # 15. Multi-Crop Report Generation
    # -------------------------------------------------------------------------
    def test_15_multi_crop_report_generation(self):
        """15. Verify PDF Farm Report generates for multiple crops with 8 pages and valid header."""
        payload = {
            'farmer_name': 'Murugan Farm Owner',
            'survey_number': 'SF-217/A',
            'selected_crops': ['Moringa', 'Tomato', 'Chilli'],
            'crop_growth_stages': {
                'Moringa': 'Vegetative Growth',
                'Tomato': 'Flowering',
                'Chilli': 'Pod Development'
            },
            'location': {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'},
            'soil_data': {'ph': 6.8, 'nitrogen': 240, 'phosphorus': 18, 'potassium': 210, 'organic_carbon': 0.65, 'ec': 0.45},
            'soil_analysis': {
                'soil_health_index': 80,
                'soil_status': 'Optimal',
                'classification': 'Neutral Loam',
                'ratings': {'ph': 'Optimal', 'nitrogen': 'Medium', 'phosphorus': 'Medium', 'potassium': 'High'}
            },
            'weather': {
                'current': {'temperature': 31.5, 'humidity': 65, 'wind_speed': 11.2, 'rain': 0.0},
                'daily': []
            },
            'monsoon': {'available': True, 'season': 'Southwest Monsoon 2026', 'summary': 'Normal expected rainfall.'}
        }

        buf = generate_farm_report_pdf(payload)
        self.assertIsInstance(buf, io.BytesIO)
        pdf_bytes = buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 10000)

        # Verify page count is exactly 8
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        self.assertEqual(len(reader.pages), 8)

    # -------------------------------------------------------------------------
    # 16. History with Multiple Crops
    # -------------------------------------------------------------------------
    def test_16_history_with_multiple_crops(self):
        """16. Verify history recording and formatting for multi-crop activities."""
        record_activity(
            activity_type='MULTI_CROP_ANALYSIS',
            description='3 crops evaluated for Kharif season',
            crop=['Moringa', 'Tomato', 'Chilli'],
            village='Kammadikottai',
            district='Thoothukudi',
            state='Tamil Nadu',
            farmer_name='Kandasamy',
            survey_number='SY-108'
        )

        activities = get_recent_activities(limit=5)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]['crop'], 'Moringa, Tomato, Chilli')
        self.assertEqual(activities[0]['farmer_name'], 'Kandasamy')

    # -------------------------------------------------------------------------
    # 17. Existing Single-Crop Compatibility
    # -------------------------------------------------------------------------
    def test_17_existing_single_crop_compatibility(self):
        """17. Verify backward compatibility: single selected_crop converted to list."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'

        res = self.client.get('/farmer-guide?step=5')
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('selected_crops'), ['Moringa'])

        # Report generation with single crop still produces exact 8-page report
        single_payload = {
            'farmer_name': 'Single Crop Farmer',
            'selected_crop': 'Moringa',
            'growth_stage': 'Vegetative Stage',
            'location': {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'},
            'soil_data': {'ph': 7.0, 'nitrogen': 260, 'phosphorus': 22, 'potassium': 230, 'organic_carbon': 0.70, 'ec': 0.35},
            'weather': {},
            'monsoon': {}
        }
        buf = generate_farm_report_pdf(single_payload)
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(buf.getvalue()))
        self.assertEqual(len(reader.pages), 8)

    # -------------------------------------------------------------------------
    # 18. Existing Routes Remain Functional
    # -------------------------------------------------------------------------
    def test_18_existing_routes(self):
        """18. Verify existing routes return 200 OK without errors."""
        routes = [
            '/',
            '/soil',
            '/crop-advisor',
            '/bioboost',
            '/pest-advisor',
            '/weather',
            '/monsoon',
            '/crop-guide',
            '/history',
            '/farmer-guide?step=1',
        ]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route '{r}' should return 200 OK")

    # -------------------------------------------------------------------------
    # 19. Existing Soil Workflow
    # -------------------------------------------------------------------------
    def test_19_existing_soil_workflow(self):
        """19. Verify soil manual submission and analysis calculation."""
        res = self.client.post('/soil', data={
            'action': 'manual_entry',
            'ph': '6.8',
            'nitrogen': '240',
            'phosphorus': '18',
            'potassium': '210',
            'organic_carbon': '0.65',
            'ec': '0.45'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            soil_analysis = sess.get('soil_analysis')
            self.assertIsNotNone(soil_analysis)
            self.assertIn('soil_health', soil_analysis)
            self.assertGreater(soil_analysis['soil_health']['score'], 0)

    # -------------------------------------------------------------------------
    # 20. Existing Weather & Monsoon Workflow
    # -------------------------------------------------------------------------
    def test_20_existing_weather_monsoon_workflow(self):
        """20. Verify weather and monsoon modules render with official status and attribution."""
        with self.client.session_transaction() as sess:
            sess['location'] = {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}

        res_w = self.client.get('/weather')
        self.assertEqual(res_w.status_code, 200)
        self.assertIn(b'Thoothukudi', res_w.data)

        res_m = self.client.get('/monsoon')
        self.assertEqual(res_m.status_code, 200)
        self.assertIn(b'India Meteorological Department', res_m.data)


if __name__ == '__main__':
    unittest.main()
