"""
AgriAI - Step 9 Test Suite
Validates Crop Guide & Farm Report module, ReportLab PDF generation,
multi-pillar session synthesis, partial/empty data resilience,
dashboard integration, and Steps 1-8 regression.
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import session
import fitz  # PyMuPDF
from app import app
from engine.report_generator import generate_farm_report_pdf


class TestStep9CropGuideAndReport(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    # -------------------------------------------------------------
    # 1. FLASK STARTUP & ALL 9 ROUTES STATUS 200
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
    # 2. CROP GUIDE PAGE & CROP SELECTION
    # -------------------------------------------------------------
    def test_crop_guide_page_rendering(self):
        resp = self.client.get('/crop-guide')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Crop Guide", resp.data)
        self.assertIn(b"Farm Report", resp.data)
        self.assertIn(b"Select Crop Knowledge Profile", resp.data)
        self.assertIn(b"Generate Farm Report (PDF)", resp.data)

    def test_crop_guide_crop_selection_param(self):
        resp = self.client.get('/crop-guide?crop=Tomato')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Tomato", resp.data)
        self.assertIn(b"Solanum lycopersicum", resp.data)

        resp2 = self.client.get('/crop-guide?crop=Paddy')
        self.assertEqual(resp2.status_code, 200)
        self.assertIn(b"Paddy", resp2.data)
        self.assertIn(b"Oryza sativa", resp2.data)

    # -------------------------------------------------------------
    # 3. PDF REPORT GENERATION: ENGINE UNIT TESTS
    # -------------------------------------------------------------
    def test_report_generator_full_data(self):
        full_payload = {
            'location': {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'},
            'selected_crop': 'Moringa',
            'crop_profile': {
                'name': 'Moringa',
                'scientific_name': 'Moringa oleifera',
                'growth_duration': '180 - 240 days',
                'water_requirement': 'Low to Moderate',
                'preferred_ph': {'min': 6.5, 'max': 8.0},
                'preferred_soil': 'Sandy loam to loamy, well-drained',
                'growth_stages': ['Germination', 'Vegetative Branching', 'Flowering', 'Pod Maturation']
            },
            'soil_data': {'ph': 7.1, 'nitrogen': 260, 'phosphorus': 16, 'potassium': 210, 'organic_carbon': 0.65, 'ec': 0.45},
            'soil_analysis': {
                'health_score': 84,
                'health_grade': 'Good',
                'strengths': ['Optimal soil reaction (pH 7.1)'],
                'concerns': ['Available Nitrogen is below target'],
                'priority_actions': ['Incorporate 5 tonnes/ha farmyard manure'],
                'parameters': {}
            },
            'crop_suitability': {
                'suitability_status': 'Suitable',
                'suitability_score': 88,
                'summary': 'Soil pH and drainage favor Moringa establishment.',
                'limiting_factors': ['Marginal Nitrogen availability']
            },
            'bioboost': {
                'priorities': ['Inoculate Azospirillum for atmospheric nitrogen fixation'],
                'biological_practices': [{'practice': 'Compost Enrichment', 'description': 'Apply seasoned compost.'}],
                'soil_management_context': 'Enhance microbial biodiversity.'
            },
            'ipm': {
                'issue_name': 'Moringa Fruit Fly',
                'severity': 'Moderate',
                'symptoms': 'Internal fruit rot and fruit drop.',
                'monitoring_advice': 'Scout pheromone and bait traps weekly.',
                'cultural_mechanical': ['Collect and bury fallen fruits'],
                'biological_control': ['Spray Azadirachtin 10000 ppm'],
                'chemical_control': {'active_ingredients': ['Spinosad 45% SC'], 'disclaimer': 'Follow approved label instructions.'}
            },
            'weather': {
                'success': True,
                'current': {'temperature': 31.2, 'humidity': 68, 'wind_speed': 14.5, 'condition': 'Partly Cloudy'},
                'daily': [{'rainfall': 2.5, 'rain_probability': 40}]
            },
            'monsoon': {
                'status': 'Available',
                'title': 'Official Seasonal Outlook for Northeast Monsoon',
                'summary': 'Rainfall is forecasted in the Normal to Above Normal category.',
                'published_date': '2024-09-30',
                'region': 'Tamil Nadu, Puducherry & Karaikal'
            }
        }

        pdf_stream = generate_farm_report_pdf(full_payload)
        pdf_bytes = pdf_stream.getvalue()
        self.assertTrue(len(pdf_bytes) > 2000)

        # Open and inspect with PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        self.assertTrue(doc.page_count >= 1)

        extracted_text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("AGRIAI FARM REPORT", extracted_text)
        self.assertIn("Moringa", extracted_text)
        self.assertIn("Kammadikottai", extracted_text)
        self.assertIn("Soil Health Index", extracted_text)
        self.assertIn("Suitable", extracted_text)
        self.assertIn("BIOBOOST", extracted_text)
        self.assertIn("Moringa Fruit Fly", extracted_text)
        self.assertIn("Open-Meteo", extracted_text)
        self.assertIn("India Meteorological Department", extracted_text)

    # -------------------------------------------------------------
    # 4. REPORT GENERATOR: RESILIENCE ON EMPTY / PARTIAL DATA
    # -------------------------------------------------------------
    def test_report_generator_empty_payload(self):
        pdf_stream = generate_farm_report_pdf({})
        pdf_bytes = pdf_stream.getvalue()
        self.assertTrue(len(pdf_bytes) > 1000)

        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        self.assertTrue(doc.page_count >= 1)
        extracted_text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("AGRIAI FARM REPORT", extracted_text)
        self.assertIn("Not available", extracted_text)

    # -------------------------------------------------------------
    # 5. FLASK ROUTE: /generate-report
    # -------------------------------------------------------------
    def test_flask_generate_report_route(self):
        resp = self.client.get('/generate-report?crop=Moringa')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/pdf')
        self.assertIn('attachment', resp.headers.get('Content-Disposition', ''))
        self.assertIn('AgriAI_Farm_Report_Moringa.pdf', resp.headers.get('Content-Disposition', ''))

        # Verify stream is readable PDF
        doc = fitz.open(stream=resp.data, filetype='pdf')
        self.assertTrue(doc.page_count >= 1)

    def test_flask_generate_report_no_crop(self):
        resp = self.client.get('/generate-report')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/pdf')
        self.assertIn('AgriAI_Farm_Report', resp.headers.get('Content-Disposition', ''))

    # -------------------------------------------------------------
    # 6. DASHBOARD INTEGRATION
    # -------------------------------------------------------------
    def test_dashboard_crop_guide_action_card(self):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Crop Guide", resp.data)
        self.assertIn(b"Farm Report", resp.data)
        self.assertIn(b"View Crop Guide", resp.data)
        self.assertIn(b"Generate Farm Report", resp.data)
        self.assertIn(b"/generate-report", resp.data)

    # -------------------------------------------------------------
    # 7. REGRESSION: PRESERVE CROP ADVISOR & PREVIOUS STEPS
    # -------------------------------------------------------------
    def test_crop_advisor_route_integrity(self):
        resp = self.client.get('/crop-advisor')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Crop Advisor", resp.data)


if __name__ == '__main__':
    unittest.main()
