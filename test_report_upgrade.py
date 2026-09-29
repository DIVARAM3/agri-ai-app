"""
Test Suite for Upgraded AGRIORA Farm Report PDF Generator
Tests farmer & field identity, 8-page structure, visual report components,
special character safety, and data synchronization.
"""

import unittest
import os
import io
import fitz  # PyMuPDF
from app import app
from engine.report_generator import generate_farm_report_pdf
from engine.history_manager import get_recent_activities, record_activity


class TestReportUpgrade(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_01_farmer_name_and_survey_persistence_in_crop_advisor(self):
        """Test farmer_name and survey_number are captured and persisted via Crop Advisor."""
        resp = self.client.post('/crop-advisor', data={
            'action': 'update_location',
            'farmer_name': 'Murugan K.',
            'survey_number': 'SF-142/B',
            'village': 'Kammadikottai',
            'district': 'Thoothukudi',
            'state': 'Tamil Nadu',
            'crop': 'Moringa'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('farmer_name'), 'Murugan K.')
            self.assertEqual(sess.get('survey_number'), 'SF-142/B')

    def test_02_farmer_name_and_survey_persistence_in_soil_lab(self):
        """Test farmer_name and survey_number are captured and persisted via Soil Lab manual entry."""
        resp = self.client.post('/soil', data={
            'action': 'manual_entry',
            'farmer_name': 'Annamalai S.',
            'survey_number': 'SF-88/1',
            'ph': '6.8',
            'ec': '0.45',
            'nitrogen': '290',
            'phosphorus': '32',
            'potassium': '310',
            'organic_carbon': '0.75'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('farmer_name'), 'Annamalai S.')
            self.assertEqual(sess.get('survey_number'), 'SF-88/1')
            self.assertEqual(sess.get('soil_data', {}).get('nitrogen'), 290)

    def test_03_pdf_generation_exact_8_pages_full_payload(self):
        """Test PDF generation produces an exact 8-page document for full agricultural data."""
        payload = {
            'farmer_name': 'Murugan K.',
            'survey_number': 'SF-142/B',
            'growth_stage': 'Flowering & Pod Formation',
            'location': {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'},
            'selected_crop': 'Moringa',
            'crop_profile': {
                'name': 'Moringa',
                'scientific_name': 'Moringa oleifera',
                'growth_duration': '150 - 180 days',
                'water_requirement': 'Semi-arid (300 - 450 mm)',
                'preferred_soil': 'Well-drained sandy loam',
                'preferred_ph': {'min': 6.0, 'max': 7.5},
                'growth_stages': ['Germination (1-15d)', 'Vegetative (16-60d)', 'Flowering (61-120d)', 'Harvest (121-180d)']
            },
            'soil_data': {'ph': 6.8, 'nitrogen': 290, 'phosphorus': 35, 'potassium': 310, 'organic_carbon': 0.70, 'ec': 0.50},
            'soil_analysis': {
                'soil_health': {'score': 82, 'label': 'Good'},
                'parameters': {
                    'ph': {'status': 'Optimal', 'status_code': 'optimal'},
                    'nitrogen': {'status': 'Medium', 'status_code': 'optimal'},
                    'phosphorus': {'status': 'Medium', 'status_code': 'optimal'},
                    'potassium': {'status': 'Medium', 'status_code': 'optimal'},
                    'organic_carbon': {'status': 'Moderate', 'status_code': 'moderate'},
                    'ec': {'status': 'Optimal', 'status_code': 'optimal'}
                },
                'strengths': ['Optimal pH supports nutrient availability', 'Non-saline EC ensures healthy seedlings'],
                'concerns': ['Organic carbon is slightly below threshold'],
                'priority_actions': [{'priority': 'HIGH', 'title': 'Organic Carbon Buffering', 'guidance': 'Apply 5 tonnes/ha well-decomposed FYM.'}]
            },
            'crop_suitability': {
                'suitability_status': 'Highly Suitable',
                'suitability_score': 88,
                'summary': 'Soil test indicates ideal conditions for Moringa.',
                'reasons': ['Optimal pH aligns with Moringa preferences', 'Good drainage prevents waterlogging'],
                'concerns': ['Maintain soil organic reserves'],
                'priority_actions': [{'priority': 'HIGH', 'title': 'Basal Compost Incorporation', 'guidance': 'Incorporate compost before sowing.'}]
            },
            'bioboost': {
                'priorities': [{'priority': 'HIGH', 'title': 'Azospirillum Inoculation', 'guidance': 'Seed treatment with Azospirillum.'}]
            },
            'ipm': {
                'issue_name': 'Moringa Fruit Fly (Gitona distigma)',
                'type': 'Insect Pest',
                'risk': {'level': 'LOW RISK • PREVENTIVE'},
                'symptoms': 'Maggots feed inside tender pods causing premature rotting and drying.',
                'monitoring': 'Install 5 methyl eugenol traps per acre.',
                'cultural_control': 'Collect and destroy fallen pods; clean cultivation.',
                'biological_control': 'Spray 5% Neem Seed Kernel Extract (NSKE).'
            },
            'weather': {
                'current': {'temperature': 31.5, 'humidity': 65, 'wind_speed': 12.0, 'rain': 0.0},
                'daily': [
                    {'date': '2026-09-25', 'temp_min': 24, 'temp_max': 33, 'rain_probability': 10, 'rain': 0.0, 'wind_speed': 12}
                ]
            },
            'monsoon': {
                'status': 'Available',
                'published_date': '2026-09-24',
                'season': 'Northeast Monsoon Season',
                'region': 'South Peninsular India',
                'summary': 'Rainfall is expected to be within the Normal to Above Normal range.'
            }
        }

        pdf_stream = generate_farm_report_pdf(payload)
        pdf_bytes = pdf_stream.getvalue()
        self.assertGreater(len(pdf_bytes), 3000)

        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        self.assertEqual(doc.page_count, 8)

        text = "".join([doc[i].get_text() for i in range(doc.page_count)])

        # 1. Identity & Headers
        self.assertIn("AGRIORA", text)
        self.assertIn("AGRIAI FARM REPORT", text)
        self.assertIn("Murugan K.", text)
        self.assertIn("SF-142/B", text)
        self.assertIn("Kammadikottai", text)

        # 2. Soil Health Index (actual score, not --/100)
        self.assertIn("Soil Health Index: 82/100", text)
        self.assertNotIn("Soil Health Index: --/100", text)

        # 3. Crop Suitability (actual status, not select a crop instruction)
        self.assertIn("Highly Suitable", text)
        self.assertNotIn("select a crop in Crop Advisor", text)

        # 4. BioBoost separated sections
        self.assertIn("SOIL FINDING & NUTRIENT STATUS", text)
        self.assertIn("BIOLOGICAL RECOMMENDATIONS", text)
        self.assertIn("ORGANIC MATTER & SOIL HEALTH MANAGEMENT", text)
        self.assertIn("AGRONOMIC VERIFICATION & DOSAGE SAFETY POLICY", text)

        # 5. IPM sections
        self.assertIn("Moringa Fruit Fly", text)
        self.assertIn("HIERARCHICAL IPM INTERVENTION PROTOCOL", text)
        self.assertIn("STATUTORY CHEMICAL CONTROL", text)

        # 6. Weather & NWP attribution
        self.assertIn("Open-Meteo", text)
        self.assertIn("31.5", text)

        # 7. Monsoon & IMD source
        self.assertIn("India Meteorological Department", text)
        self.assertIn("South Peninsular India", text)
        self.assertIn("2026-09-24", text)

        # 8. Action Plan & Provenance
        self.assertIn("FARMER ACTION PLAN", text)
        self.assertIn("PRIORITY 1: IMMEDIATE INTERVENTION", text)
        self.assertIn("TECHNICAL SPECIFICATIONS", text)
        self.assertIn("PROVENANCE", text)
        self.assertIn("AGRIORA — SCIENCE-DRIVEN FARM PROSPERITY", text)

    def test_04_pdf_generation_exact_8_pages_empty_payload(self):
        """Test PDF generation handles empty payload gracefully with clean fallback cards and exact 8 pages."""
        pdf_stream = generate_farm_report_pdf({})
        pdf_bytes = pdf_stream.getvalue()
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        self.assertEqual(doc.page_count, 8)

        text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("AGRIORA", text)
        self.assertIn("Soil Laboratory Data Unavailable", text)
        self.assertIn("Crop Intelligence Unavailable", text)
        self.assertIn("Latest verified IMD outlook unavailable", text)

    def test_05_monsoon_unavailable_explicit_warning(self):
        """Test that when official IMD outlook is unavailable, explicit warning is shown."""
        payload = {
            'monsoon': {'status': 'Unavailable'}
        }
        pdf_stream = generate_farm_report_pdf(payload)
        doc = fitz.open(stream=pdf_stream.getvalue(), filetype='pdf')
        text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("Latest verified IMD outlook unavailable", text)

    def test_06_special_characters_safety(self):
        """Test special character inputs in farmer name and survey number do not cause crash or XSS issues."""
        payload = {
            'farmer_name': "O'Connor & Co. <script>alert(1)</script>",
            'survey_number': "SF#104/A & B (North-East)",
            'location': {'village': "St. Mary's Town", 'district': "Thoothukudi", 'state': "Tamil Nadu"}
        }
        pdf_stream = generate_farm_report_pdf(payload)
        doc = fitz.open(stream=pdf_stream.getvalue(), filetype='pdf')
        self.assertEqual(doc.page_count, 8)
        text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("O'Connor", text)
        self.assertIn("SF#104/A", text)

    def test_07_flask_generate_report_endpoint_with_params(self):
        """Test Flask /generate-report endpoint with farmer query parameters and session sync."""
        with self.client.session_transaction() as sess:
            sess['selected_crop'] = 'Moringa'
            sess['user_location'] = {'village': 'Kammadikottai', 'district': 'Thoothukudi', 'state': 'Tamil Nadu'}
            sess['soil_data'] = {'ph': 6.8, 'nitrogen': 290, 'phosphorus': 35, 'potassium': 310, 'organic_carbon': 0.70, 'ec': 0.50}

        resp = self.client.get('/generate-report?crop=Moringa&farmer_name=Ramasamy+M&survey_number=SF-99/1A')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'application/pdf')
        self.assertIn('attachment', resp.headers.get('Content-Disposition', ''))
        self.assertIn('AgriAI_Farm_Report_Moringa.pdf', resp.headers.get('Content-Disposition', ''))

        # Inspect generated PDF
        doc = fitz.open(stream=resp.data, filetype='pdf')
        self.assertEqual(doc.page_count, 8)
        text = "".join([doc[i].get_text() for i in range(doc.page_count)])
        self.assertIn("Ramasamy M", text)
        self.assertIn("SF-99/1A", text)
        self.assertIn("Moringa", text)
        self.assertIn("Soil Health Index", text)

        # Check history recorded with farmer name and survey number
        activities = get_recent_activities(limit=5)
        recent_rep = next((a for a in activities if a['activity_type'] == 'REPORT_GENERATED'), None)
        self.assertIsNotNone(recent_rep)
        self.assertEqual(recent_rep.get('farmer_name'), 'Ramasamy M')
        self.assertEqual(recent_rep.get('survey_number'), 'SF-99/1A')


if __name__ == '__main__':
    unittest.main()
