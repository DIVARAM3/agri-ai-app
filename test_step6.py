"""
AgriAI - Step 6: Pest & Disease Advisor (IPM) Integration & Regression Test Suite
"""

import unittest
from app import app
from engine.ipm_engine import (
    load_ipm_data,
    get_crop_ipm_issues,
    get_issue_by_id,
    evaluate_risk,
    generate_ipm_plan,
    get_supported_crops
)

class TestStep6PestAdvisor(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_all_8_routes_accessible(self):
        """1 & 2. Verify all 8 routes in the application return 200 OK."""
        routes = [
            '/',
            '/soil',
            '/crop-advisor',
            '/bioboost',
            '/pest-advisor',
            '/weather',
            '/crop-guide',
            '/history'
        ]
        for route in routes:
            with self.subTest(route=route):
                res = self.client.get(route)
                self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")

    def test_scenario_a_no_crop(self):
        """Scenario A: When no crop is selected, display prompt to select a crop first."""
        with self.client.session_transaction() as sess:
            sess.clear()

        res = self.client.get('/pest-advisor')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Select a crop in Crop Advisor first", res.data)
        self.assertIn(b"Go to Crop Advisor", res.data)

    def test_scenario_b_valid_crop(self):
        """Scenario B: When a crop is active, display documented issues for that crop."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Tomato'

        res = self.client.get('/pest-advisor')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Tomato", res.data)
        self.assertIn(b"Tomato Fruit Borer", res.data)
        self.assertIn(b"Early Blight", res.data)
        self.assertIn(b"Tomato Leaf Curl Virus", res.data)

    def test_scenario_c_pest_selection(self):
        """Scenario C: Select a specific pest issue and verify IPM plan generation."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Paddy'

        res = self.client.get('/pest-advisor?crop=Paddy&issue=paddy_stem_borer&severity=MEDIUM')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Yellow Stem Borer", res.data)
        self.assertIn(b"PEST", res.data)
        self.assertIn(b"Deadheart", res.data)
        self.assertIn(b"IPM ACTION PLAN", res.data)
        self.assertIn(b"Trichogramma japonicum", res.data)
        self.assertIn(b"MEDIUM RISK", res.data)

        # Check session storage
        with self.client.session_transaction() as sess:
            self.assertIn('ipm_analysis', sess)
            self.assertEqual(sess['ipm_analysis']['crop'], 'Paddy')
            self.assertEqual(sess['ipm_analysis']['issue_id'], 'paddy_stem_borer')
            self.assertEqual(sess['ipm_analysis']['risk']['level'], 'MEDIUM')

    def test_scenario_d_disease_selection(self):
        """Scenario D: Select a specific disease issue and verify IPM plan generation."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Banana'

        res = self.client.get('/pest-advisor?crop=Banana&issue=banana_panama_wilt&severity=LOW')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Panama Wilt", res.data)
        self.assertIn(b"DISEASE", res.data)
        self.assertIn(b"IPM ACTION PLAN", res.data)
        self.assertIn(b"Trichoderma viride", res.data)
        self.assertIn(b"LOW RISK", res.data)

    def test_scenario_e_low_severity(self):
        """Scenario E: LOW severity evaluates to LOW risk."""
        plan = generate_ipm_plan('Moringa', 'moringa_pod_fly', 'LOW')
        self.assertIsNotNone(plan)
        self.assertEqual(plan['risk']['level'], 'LOW')
        self.assertEqual(plan['risk']['code'], 'success')
        self.assertIn("below economic injury levels", plan['risk']['reason'])

    def test_scenario_f_medium_severity(self):
        """Scenario F: MEDIUM severity evaluates to MEDIUM risk."""
        plan = generate_ipm_plan('Moringa', 'moringa_pod_fly', 'MEDIUM')
        self.assertIsNotNone(plan)
        self.assertEqual(plan['risk']['level'], 'MEDIUM')
        self.assertEqual(plan['risk']['code'], 'warning')
        self.assertIn("Moderate pest presence observed", plan['risk']['reason'])

    def test_scenario_g_high_severity(self):
        """Scenario G: HIGH severity evaluates to HIGH risk."""
        plan = generate_ipm_plan('Moringa', 'moringa_pod_fly', 'HIGH')
        self.assertIsNotNone(plan)
        self.assertEqual(plan['risk']['level'], 'HIGH')
        self.assertEqual(plan['risk']['code'], 'danger')
        self.assertIn("Extensive pest damage reported", plan['risk']['reason'])

    def test_scenario_h_not_sure_uncertainty(self):
        """Scenario H: 'Not sure' severity triggers diagnostic caution rather than confident action."""
        plan = generate_ipm_plan('Cotton', 'cotton_pink_bollworm', 'Not sure')
        self.assertIsNotNone(plan)
        self.assertEqual(plan['risk']['level'], 'UNCERTAIN / MODERATE CAUTION')
        self.assertIn("uncertain", plan['risk']['reason'].lower())
        self.assertIn("Confirm diagnosis locally", plan['risk']['reason'])

        # Verify in browser response
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Cotton'

        res = self.client.get('/pest-advisor?crop=Cotton&issue=cotton_pink_bollworm&severity=Not+sure')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"UNCERTAIN / MODERATE CAUTION", res.data)

    def test_scenario_i_invalid_issue_fallback(self):
        """Scenario I: Requesting an unknown issue ID falls back gracefully to a valid issue."""
        plan = generate_ipm_plan('Chilli', 'completely_fake_issue_id', 'LOW')
        self.assertIsNotNone(plan)
        # Should fallback to the first issue of Chilli (e.g. chilli_thrips)
        self.assertEqual(plan['crop'], 'Chilli')
        self.assertIn(plan['issue_id'], ['chilli_thrips', 'chilli_anthracnose'])

    def test_scenario_j_missing_ipm_crop_data(self):
        """Scenario J: Requesting a crop with no IPM data returns None without crashing."""
        issues = get_crop_ipm_issues('NonExistentCrop123')
        self.assertEqual(issues, [])
        plan = generate_ipm_plan('NonExistentCrop123', 'fake_issue')
        self.assertIsNone(plan)

    def test_scenario_k_dashboard_synchronization(self):
        """Scenario K: Dashboard synchronization reflects IPM status accurately."""
        # 1. Without IPM analysis in session
        with self.client.session_transaction() as sess:
            sess.clear()
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Select a crop and complete an IPM assessment", res.data)

        # 2. With IPM analysis in session
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Maize'
        # Visit pest-advisor to trigger analysis
        self.client.get('/pest-advisor?crop=Maize&issue=maize_fall_armyworm&severity=HIGH')

        # Visit dashboard
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"IPM assessment available", res.data)
        self.assertIn(b"HIGH RISK", res.data)
        self.assertIn(b"Fall Armyworm", res.data)

    def test_scenario_l_session_persistence(self):
        """Scenario L: Verified session persistence across multiple module page requests."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Groundnut'

        self.client.get('/pest-advisor?crop=Groundnut&issue=groundnut_tikka_leaf_spot&severity=MEDIUM')

        with self.client.session_transaction() as sess:
            self.assertIn('ipm_analysis', sess)
            self.assertEqual(sess['ipm_analysis']['issue_id'], 'groundnut_tikka_leaf_spot')

        # Navigate away to another page (e.g., weather) and verify session remains intact
        res = self.client.get('/weather')
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess['ipm_analysis']['crop'], 'Groundnut')

    def test_step1_to_step5_regression(self):
        """End-to-End Regression Test verifying Steps 1–5 continue functioning seamlessly."""
        # Step 2: Soil Lab manual entry
        post_data = {
            'action': 'manual_entry',
            'ph': '6.8',
            'nitrogen': '260',
            'phosphorus': '22',
            'potassium': '320',
            'organic_carbon': '0.9',
            'ec': '0.45'
        }
        res_soil = self.client.post('/soil', data=post_data, follow_redirects=True)
        self.assertEqual(res_soil.status_code, 200)

        # Step 3: Crop Advisor selection
        res_crop = self.client.get('/crop-advisor?crop=Tomato')
        self.assertEqual(res_crop.status_code, 200)

        # Step 4: Soil-Crop Intelligence generation
        res_intel = self.client.post('/crop-advisor', data={'action': 'analyze'}, follow_redirects=True)
        self.assertEqual(res_intel.status_code, 200)

        # Step 5: BioBoost decision support
        res_bio = self.client.get('/bioboost')
        self.assertEqual(res_bio.status_code, 200)
        self.assertIn(b"BIOLOGICAL SOIL HEALTH", res_bio.data)

        # Step 6: Pest Advisor
        res_pest = self.client.get('/pest-advisor')
        self.assertEqual(res_pest.status_code, 200)
        self.assertIn(b"Tomato Fruit Borer", res_pest.data)

        # Dashboard check
        res_dash = self.client.get('/')
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"Tomato", res_dash.data)

if __name__ == '__main__':
    unittest.main()
