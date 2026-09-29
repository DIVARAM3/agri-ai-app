"""
AgriAI - Step 8 Test Suite
Validates Monsoon Outlook module, IMD official bulletin normalization,
conservative agricultural interpretation, location/crop/weather integration,
dashboard synchronization, and Step 1-7 regression.
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import session
from app import app
from engine.monsoon_service import (
    get_official_monsoon_bulletin,
    _MONSOON_CACHE
)
from engine.monsoon_engine import (
    interpret_monsoon_outlook
)


class TestStep8Monsoon(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        _MONSOON_CACHE.clear()

    # -------------------------------------------------------------
    # 1. FLASK STARTUP & ALL 9 ROUTES (INCLUDING /monsoon)
    # -------------------------------------------------------------
    def test_all_routes_status_200(self):
        routes = [
            '/',
            '/soil',
            '/crop-advisor',
            '/bioboost',
            '/pest-advisor',
            '/weather',
            '/monsoon',
            '/crop-guide',
            '/history'
        ]
        for r in routes:
            response = self.client.get(r)
            self.assertEqual(response.status_code, 200, f"Route {r} failed with status {response.status_code}")

    # -------------------------------------------------------------
    # 2. IMD MONSOON SERVICE: AVAILABLE & UNAVAILABLE SCENARIOS
    # -------------------------------------------------------------
    def test_monsoon_service_available(self):
        data = get_official_monsoon_bulletin(state="Tamil Nadu")
        self.assertEqual(data["status"], "Available")
        self.assertEqual(data["source"], "India Meteorological Department")
        self.assertIn("mausam.imd.gov.in", data["source_url"])
        self.assertTrue(len(data["summary"]) > 0)
        self.assertTrue(len(data["title"]) > 0)
        self.assertTrue(len(data["published_date"]) > 0)
        self.assertIn("Tamil Nadu", data["region"])

    def test_monsoon_service_force_unavailable(self):
        data = get_official_monsoon_bulletin(force_unavailable=True)
        self.assertEqual(data["status"], "Unavailable")
        self.assertIn("temporarily unavailable", data["message"])
        self.assertEqual(data["source_url"], "https://mausam.imd.gov.in/")

    # -------------------------------------------------------------
    # 3. MONSOON ENGINE: CONSERVATIVE INTERPRETATION & CHECKLIST
    # -------------------------------------------------------------
    def test_monsoon_interpretation_engine(self):
        sample_bulletin = {
            "status": "Available",
            "source": "India Meteorological Department",
            "source_url": "https://mausam.imd.gov.in/",
            "title": "Seasonal Monsoon Outlook",
            "summary": "Seasonal rainfall projected to be normal across south peninsular India.",
            "season": "Northeast Monsoon",
            "region": "Tamil Nadu, Puducherry & Karaikal",
            "regional_outlook": {
                "subdivision": "Tamil Nadu, Puducherry & Karaikal",
                "category": "Normal to Above Normal",
                "notes": "Episodic rainfall pulses expected."
            }
        }
        res = interpret_monsoon_outlook(sample_bulletin)
        self.assertEqual(res["status"], "Available")
        self.assertEqual(res["source"], "India Meteorological Department (IMD)")
        self.assertEqual(len(res["agri_context"]), 5)
        self.assertEqual(len(res["monitoring_points"]), 5)
        self.assertIn("district rainfall", res["monitoring_points"][0].lower())
        self.assertIn("soil moisture", res["monitoring_points"][1].lower())

    # -------------------------------------------------------------
    # 4. LOCATION CONTEXT: VALID VS MISSING
    # -------------------------------------------------------------
    def test_location_context_valid_and_missing(self):
        monsoon_data = get_official_monsoon_bulletin(state="Tamil Nadu")

        # Valid location
        loc = {"village": "Kammadikottai", "district": "Thoothukudi", "state": "Tamil Nadu"}
        interp = interpret_monsoon_outlook(monsoon_data, location=loc)
        self.assertTrue(interp["location_context"]["has_location"])
        self.assertIn("Kammadikottai", interp["location_context"]["display"])

        # Missing location
        interp_missing = interpret_monsoon_outlook(monsoon_data, location=None)
        self.assertFalse(interp_missing["location_context"]["has_location"])
        self.assertIn("Complete your location in Crop Advisor", interp_missing["location_context"]["note"])

    # -------------------------------------------------------------
    # 5. CROP CONTEXT: SELECTED VS NO CROP
    # -------------------------------------------------------------
    def test_crop_context_selected_and_none(self):
        monsoon_data = get_official_monsoon_bulletin(state="Tamil Nadu")

        # Crop selected: Moringa
        interp_crop = interpret_monsoon_outlook(monsoon_data, crop_name="Moringa")
        self.assertIsNotNone(interp_crop["crop_context"])
        self.assertEqual(interp_crop["crop_context"]["crop"], "Moringa")
        self.assertIn("drain", interp_crop["crop_context"]["agronomic_note"].lower())
        self.assertIn("disclaimer", interp_crop["crop_context"])

        # Crop selected: Paddy
        interp_paddy = interpret_monsoon_outlook(monsoon_data, crop_name="Paddy")
        self.assertIsNotNone(interp_paddy["crop_context"])
        self.assertEqual(interp_paddy["crop_context"]["crop"], "Paddy")

        # No crop selected
        interp_none = interpret_monsoon_outlook(monsoon_data, crop_name=None)
        self.assertIsNone(interp_none["crop_context"])

    # -------------------------------------------------------------
    # 6. WEATHER CONNECTION: WITH WEATHER VS MISSING WEATHER
    # -------------------------------------------------------------
    def test_weather_connection_integration(self):
        monsoon_data = get_official_monsoon_bulletin(state="Tamil Nadu")

        sample_weather = {
            "success": True,
            "current": {"temperature": 29.5, "rain": 0.0, "condition": "Partly Cloudy"},
            "daily": [{"rainfall": 2.0, "rain_probability": 30}, {"rainfall": 0.0, "rain_probability": 10}]
        }
        interp = interpret_monsoon_outlook(monsoon_data, weather_data=sample_weather)
        self.assertIsNotNone(interp["weather_context"])
        self.assertTrue(interp["weather_context"]["available"])
        self.assertEqual(interp["weather_context"]["temperature"], 29.5)
        self.assertIn("Current weather is separate from the seasonal monsoon outlook", interp["weather_context"]["disclaimer"])

        # Missing weather
        interp_no_w = interpret_monsoon_outlook(monsoon_data, weather_data=None)
        self.assertIsNone(interp_no_w["weather_context"])

    # -------------------------------------------------------------
    # 7. ROUTE /monsoon: POST LOCATION & SESSION PERSISTENCE
    # -------------------------------------------------------------
    def test_monsoon_page_and_session_persistence(self):
        with self.client as c:
            # Set up session with crop and location
            with c.session_transaction() as sess:
                sess['selected_crop'] = 'Moringa'
                sess['user_location'] = {'village': 'Eral', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}

            resp = c.get('/monsoon')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Official IMD Information", resp.data)
            self.assertIn(b"What This Means for Farmers", resp.data)
            self.assertIn(b"Farmer Monitoring Checklist", resp.data)
            self.assertIn(b"Crop Context: Moringa", resp.data)
            self.assertIn(b"mausam.imd.gov.in", resp.data)

            # Check session persistence
            self.assertIn('monsoon_outlook', session)
            self.assertEqual(session['monsoon_outlook']['status'], 'Available')

            # Test POST location update
            post_resp = c.post('/monsoon', data={
                'village': 'Alwarthirunagari',
                'district': 'Thoothukudi',
                'state': 'Tamil Nadu'
            }, follow_redirects=True)
            self.assertEqual(post_resp.status_code, 200)
            self.assertIn(b"Alwarthirunagari", post_resp.data)

    # -------------------------------------------------------------
    # 8. DASHBOARD SYNCHRONIZATION WITH MONSOON CARD
    # -------------------------------------------------------------
    def test_dashboard_monsoon_card_synchronization(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Monsoon Outlook", resp.data)
        self.assertIn(b"Official IMD Information Available", resp.data)
        self.assertIn(b"View Monsoon Outlook \xe2\x86\x92", resp.data)  # 'View Monsoon Outlook →'

    # -------------------------------------------------------------
    # 9. MONSOON PAGE UNAVAILABLE STATE GRACEFUL DEGRADATION
    # -------------------------------------------------------------
    @patch("app.get_official_monsoon_bulletin")
    def test_monsoon_page_unavailable_graceful(self, mock_bulletin):
        mock_bulletin.return_value = {
            "status": "Unavailable",
            "message": "Official monsoon information is temporarily unavailable.",
            "source": "India Meteorological Department (IMD)",
            "source_url": "https://mausam.imd.gov.in/"
        }
        resp = self.client.get('/monsoon')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Official IMD Monsoon Information is Currently Unavailable", resp.data)
        self.assertIn(b"https://mausam.imd.gov.in/", resp.data)
        self.assertNotIn(b"traceback", resp.data.lower())


if __name__ == '__main__':
    unittest.main()
