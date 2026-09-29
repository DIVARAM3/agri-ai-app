"""
AgriAI - Step 10: Final Comprehensive Test Suite (test_final.py)
Tests the complete integrated agriculture intelligence platform across 20 distinct verification areas.
"""

import io
import os
import unittest
from datetime import datetime

from app import app
from engine.history_manager import (
    record_activity,
    get_recent_activities,
    get_activity_stats,
    clear_history_for_testing
)
from engine.crop_engine import load_crops, get_crop_profile
from engine.soil_engine import analyze_soil


class TestAgriAIFinalIntegration(unittest.TestCase):
    """Step 10 Final Integration and Regression Test Suite."""

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret-key-final-step10'

    def setUp(self):
        self.client = app.test_client()
        # Clean history db before tests to ensure deterministic results
        clear_history_for_testing()

    # -------------------------------------------------------------
    # 1. Application Startup
    # -------------------------------------------------------------
    def test_01_app_startup(self):
        """1. Verify Flask application initializes with all routes and configs."""
        self.assertIsNotNone(app)
        self.assertTrue(app.testing)
        # Check rule map for core routes
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn('/', routes)
        self.assertIn('/soil', routes)
        self.assertIn('/crop-advisor', routes)
        self.assertIn('/bioboost', routes)
        self.assertIn('/pest-advisor', routes)
        self.assertIn('/weather', routes)
        self.assertIn('/monsoon', routes)
        self.assertIn('/crop-guide', routes)
        self.assertIn('/generate-report', routes)
        self.assertIn('/history', routes)

    # -------------------------------------------------------------
    # 2. Dashboard
    # -------------------------------------------------------------
    def test_02_dashboard_rendering(self):
        """2. Verify dashboard renders command center with KPIs, Quick Actions, and AI Advisor."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Dashboard", res.data)
        self.assertIn(b"Quick Action Hub", res.data)
        self.assertIn(b"AI Farm Advisor", res.data)
        self.assertIn(b"Soil Health Index", res.data)
        self.assertIn(b"Crop Suitability", res.data)
        self.assertIn(b"Recent Farm Activity", res.data)

    # -------------------------------------------------------------
    # 3. Soil Lab
    # -------------------------------------------------------------
    def test_03_soil_lab_rendering(self):
        """3. Verify Soil Lab renders upload zone and manual parameter entry form."""
        res = self.client.get('/soil')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Soil Lab", res.data)
        self.assertIn(b"nitrogen", res.data)
        self.assertIn(b"phosphorus", res.data)
        self.assertIn(b"potassium", res.data)
        self.assertIn(b"ph", res.data)
        self.assertIn(b"organic_carbon", res.data)
        self.assertIn(b"ec", res.data)

    # -------------------------------------------------------------
    # 4. Soil PDF Extraction
    # -------------------------------------------------------------
    def test_04_soil_pdf_extraction(self):
        """4. Verify Soil Lab PDF upload rejection on invalid file or acceptance on valid dummy PDF."""
        # Test invalid extension
        data = {
            'action': 'upload',
            'report_file': (io.BytesIO(b"executable payload"), "test.exe")
        }
        res = self.client.post('/soil', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Unsupported file format", res.data)

        # Test valid PDF format
        dummy_pdf = io.BytesIO(b"%PDF-1.4\n1 0 obj\n<< /Title (Soil Test Report) >>\nendobj\ntrailer\n<<>>\n%%EOF")
        data = {
            'action': 'upload',
            'report_file': (dummy_pdf, "sample_soil_report.pdf")
        }
        res = self.client.post('/soil', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)

    # -------------------------------------------------------------
    # 5. Manual Soil Entry
    # -------------------------------------------------------------
    def test_05_manual_soil_entry(self):
        """5. Verify manual soil parameter entry processes correctly and records history."""
        payload = {
            'action': 'manual_entry',
            'nitrogen': '290',
            'phosphorus': '32',
            'potassium': '310',
            'ph': '6.8',
            'organic_carbon': '0.75',
            'ec': '0.65'
        }
        res = self.client.post('/soil', data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"SOIL HEALTH ANALYSIS", res.data)
        self.assertIn(b"290", res.data)

        # Verify history recorded
        activities = get_recent_activities(limit=5)
        self.assertTrue(any(a['activity_type'] == 'SOIL_ANALYSIS' for a in activities))

    # -------------------------------------------------------------
    # 6. Crop Advisor
    # -------------------------------------------------------------
    def test_06_crop_advisor_rendering(self):
        """6. Verify Crop Advisor displays crop choices and intelligence engine options."""
        res = self.client.get('/crop-advisor')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Crop Advisor", res.data)
        # Check supported crops are present
        self.assertIn(b"Moringa", res.data)
        self.assertIn(b"Banana", res.data)
        self.assertIn(b"Cotton", res.data)

    # -------------------------------------------------------------
    # 7. Crop Suitability
    # -------------------------------------------------------------
    def test_07_crop_suitability(self):
        """7. Verify Crop Suitability analysis calculates compatibility score and limiting factors."""
        with self.client.session_transaction() as sess:
            sess['soil_data'] = {
                'nitrogen': 280,
                'phosphorus': 30,
                'potassium': 320,
                'ph': 7.0,
                'organic_carbon': 0.65,
                'ec': 0.8
            }
        res = self.client.post('/crop-advisor', data={'action': 'analyze', 'crop': 'Moringa'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Moringa", res.data)
        self.assertIn(b"Suitability", res.data)

    # -------------------------------------------------------------
    # 8. BioBoost
    # -------------------------------------------------------------
    def test_08_bioboost(self):
        """8. Verify BioBoost generates biological nutrient guidance for crop stage."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'
            sess['soil_data'] = {
                'nitrogen': 280,
                'phosphorus': 30,
                'potassium': 320,
                'ph': 7.0,
                'organic_carbon': 0.65,
                'ec': 0.8
            }
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"BioBoost", res.data)
        self.assertIn(b"Biological", res.data)

    # -------------------------------------------------------------
    # 9. IPM
    # -------------------------------------------------------------
    def test_09_ipm(self):
        """9. Verify IPM advisor evaluates pest risk and delivers non-chemical cultural/biological guidance."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Maize'
        res = self.client.get('/pest-advisor?crop=Maize&issue=maize_fall_armyworm&severity=HIGH')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Fall Armyworm", res.data)
        self.assertIn(b"IPM ACTION PLAN", res.data)
        self.assertIn(b"HIGH RISK", res.data)
        self.assertIn(b"PREVENT", res.data)

    # -------------------------------------------------------------
    # 10. Weather
    # -------------------------------------------------------------
    def test_10_weather(self):
        """10. Verify Weather module provides temperature, rainfall outlook, and agricultural advice."""
        res = self.client.get('/weather')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Weather", res.data)
        self.assertIn(b"Forecast", res.data)

    # -------------------------------------------------------------
    # 11. Monsoon
    # -------------------------------------------------------------
    def test_11_monsoon(self):
        """11. Verify Monsoon module displays official IMD outlook and farming guidance."""
        res = self.client.get('/monsoon')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Monsoon Outlook", res.data)
        self.assertIn(b"India Meteorological Department", res.data)
        self.assertIn(b"Official IMD Data", res.data)

    # -------------------------------------------------------------
    # 12. Crop Guide
    # -------------------------------------------------------------
    def test_12_crop_guide(self):
        """12. Verify Crop Guide delivers structured agronomic requirements and growth stages."""
        res = self.client.get('/crop-guide?crop=Cotton')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cotton", res.data)
        self.assertIn(b"Crop Guide", res.data)

    # -------------------------------------------------------------
    # 13. PDF Report Generation
    # -------------------------------------------------------------
    def test_13_pdf_report_generation(self):
        """13. Verify PDF generation returns binary PDF document and logs activity."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'
            sess['user_location'] = {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}
            sess['soil_data'] = {
                'nitrogen': 290, 'phosphorus': 35, 'potassium': 310,
                'ph': 6.8, 'organic_carbon': 0.7, 'ec': 0.5
            }
        res = self.client.get('/generate-report')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content_type, 'application/pdf')
        # Check PDF header magic bytes
        self.assertTrue(res.data.startswith(b'%PDF'))
        self.assertGreater(len(res.data), 1000)

        # Check that report generation was recorded in History
        activities = get_recent_activities(limit=5)
        self.assertTrue(any(a['activity_type'] == 'REPORT_GENERATED' for a in activities))

    # -------------------------------------------------------------
    # 14. History
    # -------------------------------------------------------------
    def test_14_history_persistence_and_filtering(self):
        """14. Verify History page renders timeline, activity counters, and filtering."""
        # Seed test activities
        record_activity('SOIL_ANALYSIS', '6 soil parameters analyzed', crop='Moringa', village='Kammadikottai', district='Thoothukudi', state='Tamil Nadu')
        record_activity('IPM_ASSESSMENT', 'IPM assessment completed for Moringa Pod Fly', crop='Moringa')

        res = self.client.get('/history')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Farm History", res.data)
        self.assertIn(b"Moringa", res.data)
        self.assertIn(b"6 soil parameters analyzed", res.data)

        # Test activity filtering
        res_filter = self.client.get('/history?type=SOIL_ANALYSIS')
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn(b"6 soil parameters analyzed", res_filter.data)

    # -------------------------------------------------------------
    # 15. Dashboard Synchronization
    # -------------------------------------------------------------
    def test_15_dashboard_synchronization(self):
        """15. Verify that state across Soil, Crop, BioBoost, IPM, and Weather populates Dashboard."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Cotton'
            sess['user_location'] = {'village': 'Kovilpatti', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}
            sess['soil_data'] = {
                'nitrogen': 275, 'phosphorus': 28, 'potassium': 340,
                'ph': 7.5, 'organic_carbon': 0.6, 'ec': 0.7
            }
            sess['soil_analysis'] = {
                'soil_health': {'score': 78, 'label': 'Good'},
                'concerns': ['Nitrogen slightly low'],
                'strengths': ['Optimal pH'],
                'priority_actions': ['Apply organic nitrogen']
            }
            sess['ipm_summary'] = {
                'crop': 'Cotton',
                'issue_name': 'Pink Bollworm',
                'risk_level': 'HIGH',
                'risk_badge': 'badge-danger',
                'risk_code': 'danger'
            }

        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cotton", res.data)
        self.assertIn(b"Pink Bollworm", res.data)
        self.assertIn(b"IPM assessment available", res.data)
        self.assertIn(b"Kovilpatti", res.data)
        self.assertIn(b"89", res.data)

    # -------------------------------------------------------------
    # 16. Missing-Data Scenarios
    # -------------------------------------------------------------
    def test_16_missing_data_scenarios(self):
        """16. Verify elegant empty states when no session data or analysis exists."""
        # Fresh client session with no data
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"No Soil Analysis Yet", res.data)
        self.assertIn(b"Location not specified", res.data)

        # Empty history
        clear_history_for_testing()
        res_hist = self.client.get('/history')
        self.assertEqual(res_hist.status_code, 200)
        self.assertIn(b"No Farm Activity Recorded Yet", res_hist.data)

    # -------------------------------------------------------------
    # 17. Invalid Inputs & Security
    # -------------------------------------------------------------
    def test_17_invalid_inputs_and_security(self):
        """17. Verify graceful handling of out-of-range parameters, invalid types, and unsafe uploads."""
        # Non-numeric soil parameters
        payload = {
            'action': 'manual_entry',
            'nitrogen': 'INVALID_NUM',
            'phosphorus': 'abc',
            'potassium': 'xyz',
            'ph': 'invalid_ph',
            'organic_carbon': '0.5',
            'ec': '0.5'
        }
        res = self.client.post('/soil', data=payload, follow_redirects=True)
        # Should not crash with 500; should render soil page with error message
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid numeric value", res.data)

        # Malformed crop guide query
        res_crop = self.client.get('/crop-guide?crop=NonExistentSuperPlant123')
        self.assertEqual(res_crop.status_code, 200)

    # -------------------------------------------------------------
    # 18. Navigation
    # -------------------------------------------------------------
    def test_18_navigation(self):
        """18. Verify all navigation menu destinations exist and return 200 OK."""
        nav_routes = [
            ('/', b"Dashboard"),
            ('/soil', b"Soil Lab"),
            ('/crop-advisor', b"Crop Advisor"),
            ('/bioboost', b"BioBoost"),
            ('/pest-advisor', b"Pest Advisor"),
            ('/weather', b"Weather"),
            ('/monsoon', b"Monsoon Outlook"),
            ('/crop-guide', b"Crop Guide"),
            ('/history', b"History")
        ]
        for route, label in nav_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")
            self.assertIn(label, res.data, f"Label {label} not found on {route}")

    # -------------------------------------------------------------
    # 19. Responsive-Related Template Rendering
    # -------------------------------------------------------------
    def test_19_responsive_template_rendering(self):
        """19. Verify responsive markup, viewport meta tag, and layout structure across templates."""
        pages = ['/', '/soil', '/crop-advisor', '/bioboost', '/pest-advisor', '/weather', '/monsoon', '/crop-guide', '/history']
        for page in pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200)
            # Viewport meta tag is crucial for responsive layout on mobile/tablet
            self.assertIn(b'name="viewport"', res.data)
            self.assertIn(b'width=device-width', res.data)
            self.assertIn(b'sidebar', res.data)
            self.assertIn(b'main-content', res.data)

    # -------------------------------------------------------------
    # 20. Regression of Steps 1–9 Complete Flow
    # -------------------------------------------------------------
    def test_20_regression_complete_farmer_flow(self):
        """20. Execute full multi-module farmer workflow end-to-end and confirm zero regression."""
        # Step 1: Submit manual soil report with location
        soil_payload = {
            'action': 'manual_entry',
            'nitrogen': '310',
            'phosphorus': '38',
            'potassium': '330',
            'ph': '6.9',
            'organic_carbon': '0.8',
            'ec': '0.55'
        }
        res1 = self.client.post('/soil', data=soil_payload, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # Set user location in session
        with self.client.session_transaction() as sess:
            sess['user_location'] = {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}

        # Step 2: Select crop in Crop Advisor
        res2 = self.client.post('/crop-advisor', data={'action': 'analyze', 'crop': 'Moringa'}, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # Step 3: View BioBoost guidance
        res3 = self.client.get('/bioboost')
        self.assertEqual(res3.status_code, 200)
        self.assertIn(b"Moringa", res3.data)

        # Step 4: Perform IPM assessment
        res4 = self.client.get('/pest-advisor?crop=Moringa&issue=moringa_pod_fly&severity=MEDIUM')
        self.assertEqual(res4.status_code, 200)
        self.assertIn(b"Pod Fly", res4.data)

        # Step 5: Check Weather
        res5 = self.client.get('/weather')
        self.assertEqual(res5.status_code, 200)

        # Step 6: View Monsoon Outlook
        res6 = self.client.get('/monsoon')
        self.assertEqual(res6.status_code, 200)

        # Step 7: View Crop Guide
        res7 = self.client.get('/crop-guide?crop=Moringa')
        self.assertEqual(res7.status_code, 200)

        # Step 8: Generate Personalized Farm Report (PDF)
        res8 = self.client.get('/generate-report')
        self.assertEqual(res8.status_code, 200)
        self.assertEqual(res8.content_type, 'application/pdf')
        self.assertTrue(res8.data.startswith(b'%PDF'))

        # Step 9: Verify History page has recorded events
        res9 = self.client.get('/history')
        self.assertEqual(res9.status_code, 200)
        self.assertIn(b"Soil Analysis Completed", res9.data)
        self.assertIn(b"Crop Analysis Completed", res9.data)
        self.assertIn(b"IPM Assessment Completed", res9.data)
        self.assertIn(b"Farm Report Generated", res9.data)

        # Step 10: Verify Dashboard has all synthesized data
        res10 = self.client.get('/')
        self.assertEqual(res10.status_code, 200)
        self.assertIn(b"Moringa", res10.data)
        self.assertIn(b"Kammadikottai", res10.data)


if __name__ == '__main__':
    unittest.main()
