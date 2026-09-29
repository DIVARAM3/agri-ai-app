"""
Comprehensive Step 5: BioBoost Integration and Regression Tests
"""
import unittest
from app import app
from engine.bioboost_engine import generate_bioboost_guidance, load_bioboost_data, evaluate_biological_health
from engine.crop_engine import load_crops, get_crop_profile

class TestStep5BioBoost(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_all_routes_accessible(self):
        """Ensure all 8 routes are active and return 200 OK."""
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

    def test_bioboost_prerequisites(self):
        """Test prerequisite behavior: no crop, no soil data."""
        # Clean session
        with self.client.session_transaction() as sess:
            sess.clear()

        # 1. No crop and no soil
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Select a crop in Crop Advisor", res.data)

        # 2. Soil data only, no crop
        with self.client.session_transaction() as sess:
            sess['soil_data'] = {'ph': 6.5, 'nitrogen': 280, 'phosphorus': 22, 'potassium': 290, 'organic_carbon': 0.85, 'ec': 0.5}
            sess['selected_crop'] = None
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Select a crop in Crop Advisor", res.data)

        # 3. Crop only, no soil
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'
            sess['soil_data'] = None
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Complete the Soil Lab analysis", res.data)

    def test_bioboost_with_valid_crop_and_soil(self):
        """Test full BioBoost generation with valid crop and soil data."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Groundnut'
            sess['soil_data'] = {
                'ph': 6.2,
                'nitrogen': 210,
                'phosphorus': 14,
                'potassium': 280,
                'organic_carbon': 0.45,
                'ec': 0.35
            }
            sess['user_location'] = {'village': 'Alwarthirunagari', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}

        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        # Check that page contains key BioBoost sections
        self.assertIn(b"BIOLOGICAL SOIL HEALTH", res.data)
        self.assertIn(b"TOP PRIORITIES", res.data)
        self.assertIn(b"BIOLOGICAL PRACTICES", res.data)
        self.assertIn(b"WHAT TO MONITOR", res.data)
        self.assertIn(b"Decision Support Notice", res.data)
        # Check Groundnut-specific practice (Rhizobium)
        self.assertIn(b"Rhizobium", res.data)
        # Check session storage
        with self.client.session_transaction() as sess:
            self.assertIn('bioboost_analysis', sess)
            self.assertEqual(sess['bioboost_analysis']['crop'], 'Groundnut')
            self.assertTrue(len(sess['bioboost_analysis']['priorities']) > 0)

    def test_bioboost_growth_stage_selection_and_invalid_fallback(self):
        """Test changing growth stage via query parameter and invalid stage fallback."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Tomato'
            sess['soil_data'] = {'ph': 6.8, 'nitrogen': 290, 'phosphorus': 30, 'potassium': 340, 'organic_carbon': 1.1, 'ec': 0.5}

        # Valid stage selection (using query_string for proper URL encoding of '&')
        target_stage = 'Flowering & Fruit Setting (60 - 90 days)'
        res = self.client.get('/bioboost', query_string={'stage': target_stage})
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['bioboost_stage'], target_stage)
            self.assertEqual(sess['bioboost_analysis']['stage'], target_stage)

        # Invalid stage fallback to default first stage
        res = self.client.get('/bioboost', query_string={'stage': 'InvalidStageNameXYZ'})
        self.assertEqual(res.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['bioboost_stage'], 'Nursery & Transplanting (25 - 35 days)')

    def test_bioboost_missing_soil_parameters(self):
        """Test BioBoost handles partial/missing soil parameters gracefully (e.g. no OC or no EC)."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Paddy'
            sess['soil_data'] = {
                'ph': 7.2,
                'nitrogen': 260,
                'phosphorus': 20,
                'potassium': None,
                'organic_carbon': None, # Missing OC
                'ec': None              # Missing EC
            }
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Organic carbon was not reported", res.data)
        with self.client.session_transaction() as sess:
            self.assertIsNotNone(sess.get('bioboost_analysis'))

    def test_dashboard_bioboost_sync(self):
        """Verify dashboard displays BioBoost summary when analysis exists in session."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'
            sess['soil_data'] = {'ph': 7.0, 'nitrogen': 260, 'phosphorus': 22, 'potassium': 310, 'organic_carbon': 0.9, 'ec': 0.4}

        # Visit bioboost to populate session
        self.client.get('/bioboost')

        # Visit dashboard
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"BioBoost has identified", res.data)
        self.assertIn(b"Top Priority:", res.data)

    def test_regression_step1_to_step4(self):
        """End-to-end integration test from Soil Lab -> Crop Advisor -> BioBoost -> Dashboard."""
        # Step 2: Soil Lab manual entry
        post_data = {
            'action': 'manual_entry',
            'ph': '6.4',
            'nitrogen': '230',
            'phosphorus': '18',
            'potassium': '300',
            'organic_carbon': '0.55',
            'ec': '0.45'
        }
        res = self.client.post('/soil', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Step 3: Crop Advisor selection via query param
        res = self.client.get('/crop-advisor?crop=Cotton')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cotton", res.data)

        # Step 4: Generate Crop-Soil Intelligence (action='analyze')
        res = self.client.post('/crop-advisor', data={'action': 'analyze'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cotton", res.data)

        # Step 5: BioBoost decision support
        res = self.client.get('/bioboost')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"BIOBOOST", res.data)
        self.assertIn(b"Cotton", res.data)

        # Dashboard check (reflects analyzed crop Cotton)
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Cotton", res.data)

if __name__ == '__main__':
    unittest.main()
