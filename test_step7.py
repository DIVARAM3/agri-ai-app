"""
AgriAI - Step 7 Test Suite
Validates Weather & 7-Day Farm Forecast module, unit tests, mock API scenarios,
error handling, caching, dashboard integration, and Step 1-6 regression.
"""

import unittest
from unittest.mock import patch, MagicMock
from app import app
from engine.weather_service import (
    geocode_location,
    fetch_weather_from_api,
    parse_weather_response,
    get_weather,
    get_condition_from_code,
    _GEOCODE_CACHE,
    _WEATHER_CACHE
)
from engine.weather_engine import (
    generate_weather_insights,
    generate_weather_alerts,
    generate_crop_weather_context
)


class TestStep7Weather(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        # Clear weather caches before tests
        _GEOCODE_CACHE.clear()
        _WEATHER_CACHE.clear()

    # -------------------------------------------------------------
    # 1. FLASK STARTUP & ALL 8 EXISTING ROUTES
    # -------------------------------------------------------------
    def test_routes_status_200(self):
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
        for r in routes:
            response = self.client.get(r)
            self.assertEqual(response.status_code, 200, f"Route {r} failed to load (status {response.status_code})")

    # -------------------------------------------------------------
    # 2. WMO WEATHER CODE MAPPINGS
    # -------------------------------------------------------------
    def test_wmo_code_mapping(self):
        cond, icon = get_condition_from_code(0)
        self.assertEqual(cond, "Clear Sky")
        self.assertEqual(icon, "☀️")

        cond, icon = get_condition_from_code(61)
        self.assertEqual(cond, "Slight Rain")

        cond, icon = get_condition_from_code(95)
        self.assertEqual(cond, "Thunderstorm")

        cond, icon = get_condition_from_code(None)
        self.assertEqual(cond, "Unknown")

        cond, icon = get_condition_from_code(9999)
        self.assertEqual(cond, "Partly Cloudy")

    # -------------------------------------------------------------
    # 3. WEATHER TESTS: VALID, INVALID & MISSING LOCATION
    # -------------------------------------------------------------
    def test_missing_location(self):
        # Empty dict or all blank strings
        res = get_weather({})
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "missing_location")

        res2 = get_weather({"village": "  ", "district": "", "state": ""})
        self.assertFalse(res2["success"])
        self.assertEqual(res2["error"], "missing_location")

    @patch("engine.weather_service.requests.get")
    def test_invalid_location_geocoding_failure(self, mock_get):
        # Mock geocoding returning empty results
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp

        res = get_weather({"village": "NonExistentPlaceXYZ123", "district": "FakeDistrict", "state": "FakeState"})
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "location_not_found")
        self.assertIn("couldn't find this location", res["message"])

    # -------------------------------------------------------------
    # 4. WEATHER TESTS: API SUCCESS & 7-DAY PARSING
    # -------------------------------------------------------------
    @patch("engine.weather_service.fetch_weather_from_api")
    @patch("engine.weather_service.geocode_location")
    def test_api_success_and_forecast_parsing(self, mock_geo, mock_fetch):
        mock_geo.return_value = {
            "latitude": 8.52,
            "longitude": 78.12,
            "resolved_name": "Thoothukudi",
            "admin1": "Tamil Nadu",
            "country": "India"
        }
        mock_fetch.return_value = {
            "current": {
                "temperature_2m": 29.4,
                "relative_humidity_2m": 72,
                "precipitation": 1.2,
                "wind_speed_10m": 16.5,
                "weather_code": 61
            },
            "daily": {
                "time": ["2026-09-24", "2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30"],
                "temperature_2m_max": [31.5, 32.0, 31.0, 33.2, 32.8, 30.5, 31.2],
                "temperature_2m_min": [24.5, 25.0, 24.8, 25.1, 24.9, 24.0, 24.2],
                "precipitation_sum": [2.5, 0.0, 0.0, 5.2, 0.0, 0.0, 1.0],
                "precipitation_probability_max": [45, 10, 15, 60, 20, 10, 30],
                "weather_code": [61, 1, 2, 80, 0, 1, 61],
                "sunrise": ["2026-09-24T06:05", "2026-09-25T06:05"],
                "sunset": ["2026-09-24T18:15", "2026-09-25T18:14"]
            }
        }

        res = get_weather({"village": "Kammadikottai", "district": "Thoothukudi", "state": "Tamil Nadu"})
        self.assertTrue(res["success"])
        self.assertEqual(res["current"]["temperature"], 29.4)
        self.assertEqual(res["current"]["humidity"], 72)
        self.assertEqual(res["current"]["condition"], "Slight Rain")
        self.assertEqual(res["current"]["wind_speed"], 16.5)

        # 7-day forecast
        self.assertEqual(len(res["daily"]), 7)
        first_day = res["daily"][0]
        self.assertEqual(first_day["day"], "Today")
        self.assertEqual(first_day["temperature_max"], 31.5)
        self.assertEqual(first_day["temperature_min"], 24.5)
        self.assertEqual(first_day["rain_probability"], 45)
        self.assertEqual(first_day["rainfall"], 2.5)
        self.assertEqual(first_day["condition"], "Slight Rain")

        second_day = res["daily"][1]
        self.assertEqual(second_day["day"], "Tomorrow")

    # -------------------------------------------------------------
    # 5. WEATHER TESTS: API FAILURE & MALFORMED RESPONSE
    # -------------------------------------------------------------
    @patch("engine.weather_service.fetch_weather_from_api")
    @patch("engine.weather_service.geocode_location")
    def test_api_failure_handling(self, mock_geo, mock_fetch):
        mock_geo.return_value = {"latitude": 8.52, "longitude": 78.12}
        mock_fetch.return_value = None  # Simulates API downtime or timeout

        res = get_weather({"village": "Kammadikottai", "district": "Thoothukudi", "state": "Tamil Nadu"})
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "api_unavailable")
        self.assertIn("Weather data is temporarily unavailable", res["message"])

    @patch("engine.weather_service.fetch_weather_from_api")
    @patch("engine.weather_service.geocode_location")
    def test_malformed_api_response(self, mock_geo, mock_fetch):
        mock_geo.return_value = {"latitude": 8.52, "longitude": 78.12}
        mock_fetch.return_value = {"unexpected": "payload"}  # Missing current & daily

        res = get_weather({"village": "Kammadikottai", "district": "Thoothukudi", "state": "Tamil Nadu"})
        # Should not crash, returns valid normalized structure or graceful failure
        self.assertTrue(res["success"])
        self.assertEqual(res["current"]["temperature"], 0.0)
        self.assertEqual(len(res["daily"]), 0)

    # -------------------------------------------------------------
    # 6. CACHING BEHAVIOR
    # -------------------------------------------------------------
    @patch("engine.weather_service.fetch_weather_from_api")
    @patch("engine.weather_service.geocode_location")
    def test_caching_behavior(self, mock_geo, mock_fetch):
        mock_geo.return_value = {"latitude": 10.0, "longitude": 77.0, "resolved_name": "TestLoc"}
        mock_fetch.return_value = {
            "current": {"temperature_2m": 30.0, "relative_humidity_2m": 60, "weather_code": 0},
            "daily": {"time": ["2026-09-24"], "temperature_2m_max": [32.0], "temperature_2m_min": [24.0]}
        }

        # First call fetches from API
        res1 = get_weather({"district": "TestDistrict", "state": "Tamil Nadu"})
        self.assertTrue(res1["success"])
        self.assertFalse(res1.get("cached", False))
        self.assertEqual(mock_fetch.call_count, 1)

        # Second call should hit in-memory cache without calling fetch_weather_from_api again
        res2 = get_weather({"district": "TestDistrict", "state": "Tamil Nadu"})
        self.assertTrue(res2["success"])
        self.assertTrue(res2.get("cached", True))
        self.assertIn("updated_minutes_ago", res2)
        self.assertEqual(mock_fetch.call_count, 1)

    # -------------------------------------------------------------
    # 7. WEATHER INTELLIGENCE & ALERTS ENGINE
    # -------------------------------------------------------------
    def test_weather_insights_and_alerts(self):
        sample_weather = {
            "success": True,
            "current": {
                "temperature": 38.0,
                "humidity": 82,
                "rain": 5.0,
                "wind_speed": 28.0,
                "condition": "Thunderstorm"
            },
            "daily": [
                {
                    "day": "Today",
                    "date": "2026-09-24",
                    "temperature_max": 39.0,
                    "temperature_min": 26.0,
                    "rain_probability": 75,
                    "rainfall": 25.0,
                    "condition": "Thunderstorm"
                },
                {
                    "day": "Tomorrow",
                    "date": "2026-09-25",
                    "temperature_max": 37.5,
                    "temperature_min": 25.0,
                    "rain_probability": 65,
                    "rainfall": 15.0,
                    "condition": "Moderate Rain"
                }
            ]
        }

        insights = generate_weather_insights(sample_weather)
        self.assertTrue(len(insights) >= 2)
        categories = [i["category"] for i in insights]
        self.assertIn("Rain Expected", categories)
        self.assertIn("Hot Conditions", categories)
        self.assertIn("Breezy / Windy Weather", categories)

        alerts = generate_weather_alerts(sample_weather)
        alert_categories = [a["category"] for a in alerts]
        self.assertIn("RAIN", alert_categories)
        self.assertIn("HEAT", alert_categories)
        self.assertIn("WIND", alert_categories)

    # -------------------------------------------------------------
    # 8. CROP WEATHER CONTEXT
    # -------------------------------------------------------------
    def test_crop_weather_context(self):
        sample_weather = {
            "success": True,
            "current": {"temperature": 32.0},
            "daily": [
                {"day": "Today", "temperature_max": 34.0, "rainfall": 0.0},
                {"day": "Tomorrow", "temperature_max": 33.0, "rainfall": 0.0}
            ]
        }
        ctx = generate_crop_weather_context("Moringa", sample_weather)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["crop"], "Moringa")
        self.assertIn("drainage", ctx["interpretation"].lower())
        self.assertIn("disclaimer", ctx)

        # None crop returns None
        self.assertIsNone(generate_crop_weather_context(None, sample_weather))

    # -------------------------------------------------------------
    # 9. WEATHER PAGE & LOCATION UPDATE VIA POST
    # -------------------------------------------------------------
    def test_weather_page_post_location(self):
        with self.client:
            response = self.client.post('/weather', data={
                'village': 'Kayalpattinam',
                'district': 'Thoothukudi',
                'state': 'Tamil Nadu'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Kayalpattinam", response.data)
            self.assertIn(b"Farm Weather Intelligence", response.data)
            self.assertIn(b"Monsoon Outlook", response.data)
            self.assertIn(b"India Meteorological Department", response.data)

    # -------------------------------------------------------------
    # 10. DASHBOARD SYNCHRONIZATION
    # -------------------------------------------------------------
    def test_dashboard_weather_card(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weather & Forecast", response.data)
        self.assertIn(b"Monsoon Outlook", response.data)
        self.assertIn(b"Source: IMD", response.data)


if __name__ == '__main__':
    unittest.main()
