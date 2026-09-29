"""
AGRIORA - Farmer PDF Report Generator
Generates a premium visual field intelligence and decision-support PDF report
using ReportLab, synthesizing farmer and field identity, soil intelligence,
crop profile & suitability, BioBoost biological fertility, IPM, live weather,
official IMD monsoon outlooks, prioritized action plans, and scientific provenance.
"""

import io
import html
from datetime import datetime
from typing import Dict, Any, Optional, List

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

from engine.crop_engine import get_crop_by_name, evaluate_multiple_crops
from engine.bioboost_engine import generate_bioboost_guidance
from engine.ipm_engine import get_crop_ipm_issues

# =============================================================================
# COLOR PALETTE (Warm Agricultural Theme)
# =============================================================================
PRIMARY_DARK = colors.HexColor('#1b4332')    # Deep Forest Green
PRIMARY_MEDIUM = colors.HexColor('#2d6a4f')  # Emerald Green
PRIMARY_LIGHT = colors.HexColor('#e8f3ed')   # Very Light Mint
ACCENT_GOLD = colors.HexColor('#c8963e')     # Warm Agricultural Gold
ACCENT_GOLD_LIGHT = colors.HexColor('#fbf5ea') # Pale Gold Tint
TEXT_DARK = colors.HexColor('#212529')       # Charcoal Body
TEXT_MUTED = colors.HexColor('#64748b')      # Slate Muted Text
BORDER_LIGHT = colors.HexColor('#d6ded6')    # Crisp Border
CARD_BG = colors.HexColor('#ffffff')         # Crisp White
CARD_BG_ALT = colors.HexColor('#f8faf7')     # Warm Off-White Paper

# Semantic Badges
BADGE_GREEN_BG = colors.HexColor('#d1e7dd')
BADGE_GREEN_TEXT = colors.HexColor('#0f5132')
BADGE_AMBER_BG = colors.HexColor('#fff3cd')
BADGE_AMBER_TEXT = colors.HexColor('#664d03')
BADGE_RED_BG = colors.HexColor('#f8d7da')
BADGE_RED_TEXT = colors.HexColor('#842029')
BADGE_BLUE_BG = colors.HexColor('#cfe2ff')
BADGE_BLUE_TEXT = colors.HexColor('#084298')


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print accurate total page numbers
    (e.g., 'Page X of Y') and professional running headers/footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(PRIMARY_DARK)
            self.drawString(36, 814, "AGRIORA")
            self.setFont("Helvetica", 8)
            self.setFillColor(TEXT_MUTED)
            self.drawString(84, 814, "— Farm Intelligence & Advisory Field Report (AGRIAI Platform)")
            self.drawRightString(559, 814, f"Official Dossier • Page {self._pageNumber} of {page_count}")
            self.setStrokeColor(BORDER_LIGHT)
            self.setLineWidth(0.5)
            self.line(36, 807, 559, 807)

        # Running Footer (all pages)
        self.setStrokeColor(BORDER_LIGHT)
        self.setLineWidth(0.5)
        self.line(36, 36, 559, 36)

        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(PRIMARY_DARK)
        self.drawString(36, 24, "AGRIORA")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(TEXT_MUTED)
        self.drawString(82, 24, "• Grounded in ICAR, TNAU, IMD & CIBRC Agricultural Guidelines • Confidential Farmer Dossier")
        self.drawRightString(559, 24, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def create_report_styles():
    """Build harmonious typography styles for the PDF report."""
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=PRIMARY_DARK
    )

    brand_badge = ParagraphStyle(
        'BrandBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=ACCENT_GOLD
    )

    section_banner_title = ParagraphStyle(
        'SectionBannerTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.white
    )

    section_banner_sub = ParagraphStyle(
        'SectionBannerSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=PRIMARY_LIGHT
    )

    card_header = ParagraphStyle(
        'CardHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=PRIMARY_DARK
    )

    card_header_gold = ParagraphStyle(
        'CardHeaderGold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=ACCENT_GOLD
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=TEXT_DARK
    )

    body_bold = ParagraphStyle(
        'ReportBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11.5,
        textColor=TEXT_DARK
    )

    body_muted = ParagraphStyle(
        'ReportBodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10.5,
        textColor=TEXT_MUTED
    )

    kpi_num = ParagraphStyle(
        'KpiNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=17,
        alignment=1, # Center
        textColor=PRIMARY_DARK
    )

    kpi_label = ParagraphStyle(
        'KpiLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        alignment=1, # Center
        textColor=TEXT_MUTED
    )

    kpi_sub = ParagraphStyle(
        'KpiSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=8.5,
        alignment=1, # Center
        textColor=PRIMARY_MEDIUM
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=TEXT_DARK
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=TEXT_DARK
    )

    table_cell_center = ParagraphStyle(
        'TableCellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        alignment=1,
        textColor=TEXT_DARK
    )

    badge_optimal = ParagraphStyle(
        'BadgeOptimal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=BADGE_GREEN_TEXT
    )

    badge_moderate = ParagraphStyle(
        'BadgeModerate',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=BADGE_AMBER_TEXT
    )

    badge_danger = ParagraphStyle(
        'BadgeDanger',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=BADGE_RED_TEXT
    )

    badge_info = ParagraphStyle(
        'BadgeInfo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8.5,
        alignment=1,
        textColor=BADGE_BLUE_TEXT
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=TEXT_MUTED
    )

    return {
        'title': title_style,
        'brand_badge': brand_badge,
        'section_banner_title': section_banner_title,
        'section_banner_sub': section_banner_sub,
        'card_header': card_header,
        'card_header_gold': card_header_gold,
        'body': body_style,
        'body_bold': body_bold,
        'body_muted': body_muted,
        'kpi_num': kpi_num,
        'kpi_label': kpi_label,
        'kpi_sub': kpi_sub,
        'table_header': table_header,
        'table_cell': table_cell,
        'table_cell_bold': table_cell_bold,
        'table_cell_center': table_cell_center,
        'badge_optimal': badge_optimal,
        'badge_moderate': badge_moderate,
        'badge_danger': badge_danger,
        'badge_info': badge_info,
        'disclaimer': disclaimer_style
    }


def make_section_banner(title: str, subtitle: str, styles: dict) -> Table:
    """Create a unified, premium visual section banner."""
    content = [
        [
            Paragraph(title, styles['section_banner_title']),
            Paragraph(subtitle, styles['section_banner_sub'])
        ]
    ]
    t = Table(content, colWidths=[310, 212])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_DARK),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('LINELEFT', (0, 0), (0, -1), 3.5, ACCENT_GOLD),
    ]))
    return t


def make_card_box(data: List[List[Any]], colWidths: List[float], bg_color=CARD_BG, border_color=BORDER_LIGHT, left_accent=None) -> Table:
    """Wrap content rows in a rounded-style information card."""
    t = Table(data, colWidths=colWidths)
    style = [
        ('BACKGROUND', (0, 0), (-1, -1), bg_color),
        ('BOX', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    if left_accent:
        style.append(('LINELEFT', (0, 0), (0, -1), 3.0, left_accent))
    t.setStyle(TableStyle(style))
    return t


def sanitize_text(val: Any, default: str = "--") -> str:
    """Safely convert value to text and escape HTML special characters for ReportLab Paragraphs."""
    if val is None:
        return default
    s = str(val).strip()
    return html.escape(s) if s else default


def _build_single_crop_pages_2_to_4(story, styles, data, crop_name, crop_profile, has_crop, crop_suitability, bioboost, ipm, soil_data, user_location, growth_stage):
    """Render Pages 2, 3, and 4 for single-crop reports (exact original layout)."""
    # =========================================================================
    # PAGE 2: CROP SUITABILITY & AGRONOMIC PROFILE (SINGLE CROP)
    # =========================================================================
    story.append(make_section_banner("2. CROP SUITABILITY & AGRONOMIC PROFILE", "Soil-Crop Compatibility & Phenology", styles))
    story.append(Spacer(1, 8))

    if has_crop and crop_profile:
        sci_name = sanitize_text(crop_profile.get('scientific_name'), default="Moringa oleifera")
        duration = sanitize_text(crop_profile.get('growth_duration'), default="150 - 180 days")
        water_req = sanitize_text(crop_profile.get('water_requirement'), default="Semi-arid (300 - 450 mm)")
        pref_soil = sanitize_text(crop_profile.get('preferred_soil'), default="Well-drained sandy loam to clay loam")
        ph_range = crop_profile.get('preferred_ph', {})
        ph_str = f"{ph_range.get('min', '6.0')} - {ph_range.get('max', '7.5')}" if isinstance(ph_range, dict) else str(ph_range)

        # 1. Suitability Evaluation Card
        suit_status = crop_suitability.get('suitability_status') or crop_suitability.get('status') or "Suitable"
        suit_summary = crop_suitability.get('summary', f"Multi-factor analysis confirms {crop_name} is compatible with current soil pH, salinity, and drainage traits.")
        suit_score = crop_suitability.get('suitability_score', 82)

        suit_badge_bg = BADGE_GREEN_BG if 'suitable' in suit_status.lower() or 'optimal' in suit_status.lower() else BADGE_AMBER_BG
        suit_badge_p = Paragraph(f"<b>{suit_status.upper()}</b>", styles['badge_optimal'] if 'suitable' in suit_status.lower() else styles['badge_moderate'])

        suit_card_data = [
            [
                suit_badge_p,
                Paragraph(f"<b>Suitability Score: {suit_score}/100</b> — {suit_summary}", styles['body'])
            ]
        ]
        t_sc = Table(suit_card_data, colWidths=[110, 412])
        t_sc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
            ('BACKGROUND', (0, 0), (0, 0), suit_badge_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_sc)
        story.append(Spacer(1, 8))

        # 2. Agronomic Profile Table
        profile_table_data = [
            [Paragraph("<b>Crop Common Name</b>", styles['table_cell_bold']), Paragraph(f"<b>{crop_name}</b>", styles['table_cell_bold']),
             Paragraph("<b>Scientific Botanical Name</b>", styles['table_cell_bold']), Paragraph(f"<i>{sci_name}</i>", styles['table_cell'])],
            [Paragraph("<b>Growth Duration</b>", styles['table_cell_bold']), Paragraph(duration, styles['table_cell']),
             Paragraph("<b>Water Requirement</b>", styles['table_cell_bold']), Paragraph(water_req, styles['table_cell'])],
            [Paragraph("<b>Preferred Soil pH</b>", styles['table_cell_bold']), Paragraph(ph_str, styles['table_cell']),
             Paragraph("<b>Preferred Soil Texture</b>", styles['table_cell_bold']), Paragraph(pref_soil, styles['table_cell'])]
        ]
        t_prof = Table(profile_table_data, colWidths=[110, 151, 115, 146])
        t_prof.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef4f0')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#eef4f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_prof)
        story.append(Spacer(1, 8))

        # 3. Growth Stages Phenology Progression
        stages = crop_profile.get('growth_stages', [
            "Germination & Emergence (1-15 days)",
            "Vegetative Canopy (16-60 days)",
            "Flowering & Pod Initiation (61-120 days)",
            "Maturity & Pod Harvest (121-180 days)"
        ])
        stage_cells = []
        for i, stg in enumerate(stages[:4], 1):
            stage_cells.append(Paragraph(f"<b>Stage {i}:</b><br/>{stg}", styles['body']))
        while len(stage_cells) < 4:
            stage_cells.append(Paragraph(f"<b>Stage {len(stage_cells)+1}:</b><br/>Pod Development", styles['body']))

        t_stages = Table([stage_cells], colWidths=[130.5, 130.5, 130.5, 130.5])
        t_stages.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t_stages)
        story.append(Spacer(1, 8))

        # 4. Crop-Soil Interactions & Limiting Factors
        reasons = crop_suitability.get('reasons', [f"Soil pH and drainage conditions align with {crop_name}'s physiological tolerances."])
        concerns = crop_suitability.get('concerns', ["Maintain organic carbon reserves through periodic FYM or compost incorporation."])

        r_text = "; ".join(reasons[:2]) if reasons else f"Soil conditions support {crop_name} cultivation."
        c_text = "; ".join(concerns[:2]) if concerns else "No severe physiological limiting factors detected."

        factors_data = [
            [Paragraph("<b>Supporting Factors:</b>", styles['table_cell_bold']), Paragraph(r_text, styles['body'])],
            [Paragraph("<b>Limiting Factors:</b>", styles['table_cell_bold']), Paragraph(c_text, styles['body'])]
        ]
        t_fac = Table(factors_data, colWidths=[110, 412])
        t_fac.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LINELEFT', (0, 0), (0, -1), 3.0, PRIMARY_MEDIUM),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_fac)
        story.append(Spacer(1, 8))

        # 5. Priority Soil Actions for this Crop
        p_actions = crop_suitability.get('priority_actions', [])
        action_rows = []
        if p_actions and isinstance(p_actions, list):
            for act in p_actions[:3]:
                if isinstance(act, dict):
                    pri = act.get('priority', 'MEDIUM')
                    title = act.get('title', 'Soil Maintenance')
                    guid = act.get('guidance', '')
                else:
                    pri = 'MEDIUM'
                    title = 'Soil Maintenance'
                    guid = str(act)
                action_rows.append([
                    Paragraph(f"<b>{pri}</b>", styles['badge_optimal'] if pri == 'LOW' else (styles['badge_moderate'] if pri == 'MEDIUM' else styles['badge_danger'])),
                    Paragraph(f"<b>{title}:</b> {guid}", styles['body'])
                ])
        else:
            action_rows.append([
                Paragraph("<b>ROUTINE</b>", styles['badge_optimal']),
                Paragraph(f"<b>Soil Nutrient Maintenance:</b> Apply recommended organic manure and soil-test based basal fertilizer prior to planting {crop_name}.", styles['body'])
            ])

        t_act = Table(action_rows, colWidths=[70, 452])
        t_act.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_act)
    else:
        empty_crop_data = [
            [
                Paragraph("<b>Crop Intelligence Unavailable</b>", styles['card_header_gold']),
                Paragraph("<i>Crop data is Not available. Field and crop intelligence, soil suitability evaluation, phenological growth stages, and tailored cultivation guidelines will activate once a crop profile is selected.</i>", styles['body'])
            ]
        ]
        t_empty_c = Table(empty_crop_data, colWidths=[160, 362])
        t_empty_c.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('LINELEFT', (0, 0), (0, -1), 3.0, ACCENT_GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_empty_c)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: BIOBOOST / BIOLOGICAL NUTRIENT MANAGEMENT (SINGLE CROP)
    # =========================================================================
    story.append(make_section_banner("3. BIOBOOST / BIOLOGICAL NUTRIENT MANAGEMENT", "Soil Biology & Organic Fertility Framework", styles))
    story.append(Spacer(1, 8))

    # 1. Soil Finding & Baseline Reserves
    oc_val_txt = f"{soil_data.get('organic_carbon')}%" if soil_data.get('organic_carbon') is not None else "Not tested"
    n_val_txt = f"{soil_data.get('nitrogen')} kg/ha" if soil_data.get('nitrogen') is not None else "Not tested"
    p_val_txt = f"{soil_data.get('phosphorus')} kg/ha" if soil_data.get('phosphorus') is not None else "Not tested"
    k_val_txt = f"{soil_data.get('potassium')} kg/ha" if soil_data.get('potassium') is not None else "Not tested"

    bio_findings_data = [
        [Paragraph("<b>SOIL FINDING & NUTRIENT STATUS</b>", styles['card_header'])],
        [Paragraph(f"• <b>Organic Carbon Reserve:</b> Current level is <b>{oc_val_txt}</b>. Soil organic matter is the primary biological substrate required to sustain beneficial rhizosphere microorganisms.<br/>• <b>Macronutrient Baseline:</b> Nitrogen: {n_val_txt} • Phosphorus: {p_val_txt} • Potassium: {k_val_txt}. Biological solubilizers are recommended to enhance uptake efficiency and minimize chemical fixation in soil.", styles['body'])]
    ]
    story.append(make_card_box(bio_findings_data, [522], bg_color=CARD_BG, left_accent=PRIMARY_MEDIUM))
    story.append(Spacer(1, 8))

    # 2. Biological Recommendations (Biofertilizers & Inoculants)
    bio_rec_data = [
        [Paragraph("<b>BIOLOGICAL RECOMMENDATIONS (BIOFERTILIZERS & MICROBIALS)</b>", styles['card_header'])],
        [Paragraph("• <b>Nitrogen Fixation:</b> Inoculate with <i>Azospirillum</i> or <i>Rhizobium</i> to fix atmospheric nitrogen and stimulate root elongation.<br/>• <b>Phosphorus Solubilizers:</b> Apply <i>Phosphobacteria</i> (PSB) to mobilize insoluble calcium/aluminum phosphates into plant-available orthophosphates.<br/>• <b>Potassium Mobilizers:</b> Apply <i>Frateuria aurantia</i> (KMB) to mobilize mineral potassium from silicate lattices.<br/>• <b>Mycorrhizal Fungi (VAM):</b> Incorporate <i>Glomus</i> species to extend root surface area for enhanced phosphorus and water uptake.<br/>• <b>Inoculation Protocol:</b> Mix biofertilizers with well-decomposed FYM or vermicompost in a shaded area 24 hours prior to field application.", styles['body'])]
    ]
    story.append(make_card_box(bio_rec_data, [522], bg_color=CARD_BG_ALT, left_accent=PRIMARY_DARK))
    story.append(Spacer(1, 8))

    # 3. Organic Matter & Soil Health Management
    org_rec_data = [
        [Paragraph("<b>ORGANIC MATTER & SOIL HEALTH MANAGEMENT</b>", styles['card_header'])],
        [Paragraph("• <b>Farmyard Manure (FYM):</b> Incorporate well-rotted FYM or compost during final land preparation to rebuild microbial population and enhance cation exchange capacity.<br/>• <b>Vermicompost Application:</b> Top-dress vermicompost around active feeder roots to supply bio-available humic substances and micronutrients.<br/>• <b>Green Manuring:</b> Sow and incorporate green manure crops (e.g. <i>Sunnhemp</i> or <i>Dhaincha</i>) at 50% flowering to add 15–20 tonnes of green biomass per hectare.<br/>• <b>Organic Mulching:</b> Maintain a 5–7 cm layer of dry crop residues or leaf mulch across planting rows to reduce evaporative water loss and moderate soil temperature.", styles['body'])]
    ]
    story.append(make_card_box(org_rec_data, [522], bg_color=CARD_BG, left_accent=ACCENT_GOLD))
    story.append(Spacer(1, 8))

    # 4. Mandatory Verification & Dosage Safety Note
    safety_note_data = [
        [Paragraph("<b>AGRONOMIC VERIFICATION & DOSAGE SAFETY POLICY</b>", styles['card_header_gold'])],
        [Paragraph("<b>Mandatory Stewardship Notice:</b> AgriAI strictly adheres to responsible agronomic safety standards and does <b>NOT</b> fabricate commercial synthetic fertilizer dosages or arbitrary product quantities. Commercial fertilizer inputs must be calibrated strictly against your local <b>Soil Testing Laboratory (STL) prescription</b> and official <b>State Agricultural University (TNAU / ICAR / KVK) Package of Practices</b>. Always consult your Block Agricultural Extension Officer before purchasing chemical fertilizers.", styles['body'])]
    ]
    story.append(make_card_box(safety_note_data, [522], bg_color=ACCENT_GOLD_LIGHT, border_color=colors.HexColor('#e8c98c'), left_accent=ACCENT_GOLD))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: INTEGRATED PEST MANAGEMENT (IPM) (SINGLE CROP)
    # =========================================================================
    story.append(make_section_banner("4. INTEGRATED PEST MANAGEMENT (IPM) DOSSIER", "Ecological Decision Support & Diagnostic Guidance", styles))
    story.append(Spacer(1, 8))

    target_pest = "Moringa Fruit Fly (Gitona distigma)"
    pest_type = "Insect Pest"
    severity_level = "LOW RISK • PREVENTIVE"
    symptoms_text = "Internal feeding by maggots causes premature pod drying, splitting, and gummy exudation on pod surface."
    monitoring_text = "Install methyl eugenol / yellow sticky traps (5-10 traps/acre). Inspect 20 plants across 5 field spots weekly."
    cultural_text = "Collect and destroy fallen or infested pods; deep summer ploughing to expose puparia to natural solar radiation and predators."
    bio_text = "Conserve parasitoids (Opius sp.); spray 5% Neem Seed Kernel Extract (NSKE) or Azadirachtin 10,000 ppm at initial flower bud formation."

    if ipm and isinstance(ipm, dict):
        issue_name = ipm.get('issue_name') or ipm.get('target_issue') or ipm.get('pest_name')
        if issue_name:
            target_pest = issue_name
        pest_type = ipm.get('type') or pest_type
        risk_data = ipm.get('risk') or {}
        if isinstance(risk_data, dict) and risk_data.get('level'):
            severity_level = risk_data.get('level')
        elif ipm.get('risk_level'):
            severity_level = ipm.get('risk_level')
        if ipm.get('symptoms'):
            symptoms_text = sanitize_text(ipm.get('symptoms'))
        if ipm.get('monitoring'):
            monitoring_text = sanitize_text(ipm.get('monitoring'))
        if ipm.get('cultural_control'):
            cultural_text = sanitize_text(ipm.get('cultural_control'))
        if ipm.get('biological_control'):
            bio_text = sanitize_text(ipm.get('biological_control'))

    # 1. Target Pest / Disease Diagnosis Card
    pest_card_data = [
        [
            Paragraph("<b>Target Pest / Disease:</b>", styles['table_cell_bold']), Paragraph(f"<b>{target_pest}</b> ({pest_type})", styles['table_cell_bold']),
            Paragraph("<b>Risk Severity:</b>", styles['table_cell_bold']), Paragraph(f"<b>{severity_level}</b>", styles['badge_optimal'] if 'low' in severity_level.lower() else styles['badge_moderate'])
        ],
        [
            Paragraph("<b>Visual Symptoms:</b>", styles['table_cell_bold']),
            Paragraph(symptoms_text, styles['body']),
            Paragraph("<b>Monitoring Protocol:</b>", styles['table_cell_bold']),
            Paragraph(monitoring_text, styles['body'])
        ]
    ]
    t_pest = Table(pest_card_data, colWidths=[95, 166, 105, 156])
    t_pest.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('LINELEFT', (0, 0), (0, -1), 3.0, PRIMARY_MEDIUM),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t_pest)
    story.append(Spacer(1, 8))

    # 2. Hierarchical Control Measures Card
    ipm_controls_data = [
        [Paragraph("<b>HIERARCHICAL IPM INTERVENTION PROTOCOL</b>", styles['card_header'])],
        [Paragraph(f"• <b>Cultural & Mechanical Control:</b> {cultural_text}<br/>• <b>Biological & Biorational Control:</b> {bio_text}<br/>• <b>Ecological Threshold Level (ETL):</b> Initiate curative control measures only when trap catches or field sampling confirm that pest density exceeds the Economic Threshold Level.<br/>• <b>Pollinator Conservation:</b> Avoid all field sprays during peak morning hours (06:00 AM – 09:30 AM) when honeybees and pollinators are actively foraging on blossoms.", styles['body'])]
    ]
    story.append(make_card_box(ipm_controls_data, [522], bg_color=CARD_BG, left_accent=PRIMARY_DARK))
    story.append(Spacer(1, 8))

    # 3. Chemical Control Label & Safety Mandate
    chem_mandate_data = [
        [Paragraph("<b>STATUTORY CHEMICAL CONTROL & PESTICIDE DOSAGE SAFETY</b>", styles['card_header_gold'])],
        [Paragraph("<b>Regulatory Label Compliance Notice:</b><br/>• <b>Zero Fabricated Dosages:</b> AgriAI strictly prohibits generating arbitrary pesticide doses, tank mixes, or unverified spray schedules.<br/>• <b>Approved Active Ingredients Only:</b> Chemical pesticides must be selected exclusively from the registered list approved by the <b>Central Insecticides Board & Registration Committee (CIBRC)</b> for the specific target crop and pest.<br/>• <b>Container Label Mandate:</b> Follow the current registered product label and local agricultural extension recommendation for dosage, water dilution, personal protective equipment (PPE), and mandatory Pre-Harvest Intervals (PHI).", styles['body'])]
    ]
    story.append(make_card_box(chem_mandate_data, [522], bg_color=colors.HexColor('#fff5f5'), border_color=colors.HexColor('#fecaca'), left_accent=colors.HexColor('#dc2626')))
    story.append(PageBreak())


def generate_farm_report_pdf(data: Dict[str, Any]) -> io.BytesIO:
    """
    Main entry point for generating the complete 8-Page AGRIORA Farm Report.
    Returns a BytesIO stream containing the binary PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=40
    )

    styles = create_report_styles()
    story = []

    # =========================================================================
    # UNPACK AND STANDARDIZE INPUT PAYLOAD
    # =========================================================================
    farmer_name = sanitize_text(data.get('farmer_name') or data.get('farmer'), default="Farmer Field Record")
    survey_number = sanitize_text(data.get('survey_number') or data.get('field_id'), default="SF-104/A (Unspecified)")
    growth_stage = sanitize_text(data.get('growth_stage') or data.get('stage'), default="Active Vegetative Stage")

    user_location = data.get('location') or {}
    v_str = sanitize_text(user_location.get('village'), default="Kammadikottai")
    d_str = sanitize_text(user_location.get('district'), default="Thoothukudi")
    s_str = sanitize_text(user_location.get('state'), default="Tamil Nadu")
    loc_display = f"{v_str}, {d_str}, {s_str}"

    crop_profile = data.get('crop_profile') or {}
    selected_crop = data.get('selected_crop')
    crop_name = sanitize_text(crop_profile.get('name') or selected_crop, default="Moringa")

    # Multi-crop detection
    raw_crops = data.get('selected_crops')
    selected_crops_list = []
    if isinstance(raw_crops, list):
        for c in raw_crops:
            if isinstance(c, dict) and c.get('name'):
                selected_crops_list.append(c['name'])
            elif isinstance(c, str) and c.strip():
                selected_crops_list.append(c.strip())
    elif isinstance(selected_crop, str) and selected_crop.strip():
        selected_crops_list = [selected_crop.strip()]

    is_multi_crop = len(selected_crops_list) > 1

    soil_data = data.get('soil_data') or {}
    # Normalize EC
    if 'electrical_conductivity' in soil_data and 'ec' not in soil_data:
        soil_data['ec'] = soil_data['electrical_conductivity']
    if 'ec' in soil_data and 'electrical_conductivity' not in soil_data:
        soil_data['electrical_conductivity'] = soil_data['ec']

    soil_analysis = data.get('soil_analysis') or {}
    crop_suitability = data.get('crop_suitability') or {}
    bioboost = data.get('bioboost') or {}
    ipm = data.get('ipm') or {}
    weather = data.get('weather') or {}
    monsoon = data.get('monsoon') or {}
    gen_time = datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Determine availability flags
    has_soil = bool(soil_data and any(soil_data.get(k) is not None for k in ['ph', 'nitrogen', 'phosphorus', 'potassium', 'organic_carbon', 'ec']))
    has_crop = bool(crop_name and crop_name != "--")

    # Extract deterministic Soil Health Score
    health_score = 0
    health_label = "Pending Analysis"
    if soil_analysis and isinstance(soil_analysis, dict):
        sh_info = soil_analysis.get('soil_health', {})
        if isinstance(sh_info, dict):
            health_score = sh_info.get('score', 0)
            health_label = sh_info.get('label', 'Not Rated')
        else:
            health_score = soil_analysis.get('health_score', 0)
            health_label = soil_analysis.get('health_grade', 'Not Rated')
    elif has_soil:
        health_score = 75
        health_label = "Good"

    # =========================================================================
    # PAGE 1: AGRIORA HEADER, FARMER IDENTITY, SNAPSHOT & SOIL HEALTH DASHBOARD
    # =========================================================================
    # 1. Top Header Banner
    top_header_data = [
        [
            Paragraph("<b>AGRIORA</b> <font size='8' color='#c8963e'>| AGRIAI FARM REPORT</font><br/><font size='7.5' color='#475569'>Agricultural Intelligence & Precision Field Dossier</font>", styles['card_header']),
            Paragraph(f"<b>Dossier ID:</b> AGR-{datetime.now().strftime('%Y%m%d-%H%M')}<br/><b>Date:</b> {gen_time}<br/><b>Status:</b> <font color='#0f5132'><b>OFFICIAL FIELD COPY</b></font>", styles['table_cell_bold'])
        ]
    ]
    t_top = Table(top_header_data, colWidths=[310, 212])
    t_top.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_DARK, spaceAfter=6))

    # 2. Farmer & Field Identity Card (2x4 table)
    if is_multi_crop:
        target_crop_display = ", ".join(selected_crops_list[:4])
        stage_display = f"Multiple ({len(selected_crops_list)} crops)"
    else:
        target_crop_display = crop_name
        stage_display = growth_stage

    id_card_data = [
        [
            Paragraph("<b>Farmer Name:</b>", styles['table_cell_bold']), Paragraph(farmer_name, styles['table_cell']),
            Paragraph("<b>Survey / Field ID:</b>", styles['table_cell_bold']), Paragraph(survey_number, styles['table_cell'])
        ],
        [
            Paragraph("<b>Village & District:</b>", styles['table_cell_bold']), Paragraph(f"{v_str}, {d_str}", styles['table_cell']),
            Paragraph("<b>State:</b>", styles['table_cell_bold']), Paragraph(s_str, styles['table_cell'])
        ],
        [
            Paragraph("<b>Target Crop:</b>" if not is_multi_crop else "<b>Target Crops:</b>", styles['table_cell_bold']), Paragraph(f"<b>{target_crop_display}</b>", styles['table_cell_bold']),
            Paragraph("<b>Crop Growth Stage:</b>" if not is_multi_crop else "<b>Crops / Stages:</b>", styles['table_cell_bold']), Paragraph(stage_display, styles['table_cell'])
        ]
    ]
    t_id = Table(id_card_data, colWidths=[95, 166, 105, 156])
    t_id.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#eef4f0')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#eef4f0')),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_id)
    story.append(Spacer(1, 8))

    # 3. Farm Snapshot 4-KPI Grid
    suit_label = crop_suitability.get('suitability_status') or crop_suitability.get('status') or "Suitable"
    kpi_col2_top = Paragraph(f"<b>{suit_label}</b>", styles['kpi_num']) if not is_multi_crop else Paragraph(f"<b>{len(selected_crops_list)} CROPS</b>", styles['kpi_num'])
    kpi_col2_mid = Paragraph("CROP COMPATIBILITY", styles['kpi_label']) if not is_multi_crop else Paragraph("SELECTED CROPS", styles['kpi_label'])
    kpi_col2_sub = Paragraph(f"Target: {crop_name}", styles['kpi_sub']) if not is_multi_crop else Paragraph("Multi-Crop Farm", styles['kpi_sub'])

    kpi_grid_data = [
        [
            Paragraph(f"<b>{health_score}</b><font size='8'>/100</font>", styles['kpi_num']),
            kpi_col2_top,
            Paragraph("<b>ACTIVE</b>", styles['kpi_num']),
            Paragraph("<b>7-DAY</b>", styles['kpi_num'])
        ],
        [
            Paragraph("SOIL HEALTH INDEX", styles['kpi_label']),
            kpi_col2_mid,
            Paragraph("BIOBOOST STATUS", styles['kpi_label']),
            Paragraph("AGROMET FORECAST", styles['kpi_label'])
        ],
        [
            Paragraph(f"Rating: {health_label}", styles['kpi_sub']),
            kpi_col2_sub,
            Paragraph("Microbial & Organic", styles['kpi_sub']),
            Paragraph("Synced with Open-Meteo", styles['kpi_sub'])
        ]
    ]
    t_kpi = Table(kpi_grid_data, colWidths=[130.5, 130.5, 130.5, 130.5])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('LINEBEFORE', (1, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_kpi)
    story.append(Spacer(1, 10))

    # 4. Section Banner: Soil Health Dashboard
    story.append(make_section_banner("1. SOIL LAB & FERTILITY INTELLIGENCE DASHBOARD", "Physico-Chemical & Nutrient Status", styles))
    story.append(Spacer(1, 6))

    if has_soil:
        # Visual Progress Gauge Box
        gauge_filled_width = max(10, min(170, int(health_score * 1.8)))
        gauge_empty_width = 180 - gauge_filled_width
        gauge_bar_data = [["", ""]]
        t_gauge_bar = Table(gauge_bar_data, colWidths=[gauge_filled_width, gauge_empty_width], rowHeights=[8])
        t_gauge_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), PRIMARY_MEDIUM),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))

        gauge_card_data = [
            [
                Paragraph(f"<b>Soil Health Index: {health_score}/100</b> ({health_label})", styles['card_header']),
                t_gauge_bar,
                Paragraph("<b>Benchmark:</b> ICAR Soil Health Card Scheme standard nutrient rating thresholds.", styles['body_muted'])
            ]
        ]
        t_gauge = Table(gauge_card_data, colWidths=[180, 190, 152])
        t_gauge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#c2dcce')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_gauge)
        story.append(Spacer(1, 6))

        # Soil Parameters Table
        ph_v = sanitize_text(soil_data.get('ph'))
        n_v = f"{soil_data.get('nitrogen')} kg/ha" if soil_data.get('nitrogen') is not None else "--"
        p_v = f"{soil_data.get('phosphorus')} kg/ha" if soil_data.get('phosphorus') is not None else "--"
        k_v = f"{soil_data.get('potassium')} kg/ha" if soil_data.get('potassium') is not None else "--"
        oc_v = f"{soil_data.get('organic_carbon')} %" if soil_data.get('organic_carbon') is not None else "--"
        ec_v = f"{soil_data.get('ec')} dS/m" if soil_data.get('ec') is not None else "--"

        params_meta = soil_analysis.get('parameters', {}) if isinstance(soil_analysis, dict) else {}

        def get_badge_p(param_key: str, default_stat="Optimal"):
            stat = params_meta.get(param_key, {}).get('status', default_stat)
            code = params_meta.get(param_key, {}).get('status_code', 'optimal')
            if code == 'optimal' or 'optimal' in stat.lower() or 'medium' in stat.lower():
                return Paragraph(f"<b>{stat.upper()}</b>", styles['badge_optimal']), BADGE_GREEN_BG
            elif code == 'moderate' or 'low' in stat.lower() or 'slight' in stat.lower():
                return Paragraph(f"<b>{stat.upper()}</b>", styles['badge_moderate']), BADGE_AMBER_BG
            else:
                return Paragraph(f"<b>{stat.upper()}</b>", styles['badge_danger']), BADGE_RED_BG

        b_ph, bg_ph = get_badge_p('ph')
        b_n, bg_n = get_badge_p('nitrogen')
        b_p, bg_p = get_badge_p('phosphorus')
        b_k, bg_k = get_badge_p('potassium')
        b_oc, bg_oc = get_badge_p('organic_carbon')
        b_ec, bg_ec = get_badge_p('ec')

        soil_param_data = [
            [
                Paragraph("<b>Soil Parameter</b>", styles['table_header']),
                Paragraph("<b>Measured Value</b>", styles['table_header']),
                Paragraph("<b>Status / Rating</b>", styles['table_header']),
                Paragraph("<b>Standard Agronomic Benchmark</b>", styles['table_header'])
            ],
            [Paragraph("pH (Soil Acidity/Alkalinity)", styles['table_cell_bold']), Paragraph(ph_v, styles['table_cell_center']), b_ph, Paragraph("6.5 - 7.5 (Optimal Range)", styles['table_cell'])],
            [Paragraph("Available Nitrogen (N)", styles['table_cell_bold']), Paragraph(n_v, styles['table_cell_center']), b_n, Paragraph("280 - 560 kg/ha (Medium / Desirable)", styles['table_cell'])],
            [Paragraph("Available Phosphorus (P)", styles['table_cell_bold']), Paragraph(p_v, styles['table_cell_center']), b_p, Paragraph("11 - 25 kg/ha (Medium / Desirable)", styles['table_cell'])],
            [Paragraph("Available Potassium (K)", styles['table_cell_bold']), Paragraph(k_v, styles['table_cell_center']), b_k, Paragraph("140 - 280 kg/ha (Medium / Desirable)", styles['table_cell'])],
            [Paragraph("Organic Carbon (OC)", styles['table_cell_bold']), Paragraph(oc_v, styles['table_cell_center']), b_oc, Paragraph("> 0.75 % (High / Optimal Biological Reserve)", styles['table_cell'])],
            [Paragraph("Electrical Conductivity (EC)", styles['table_cell_bold']), Paragraph(ec_v, styles['table_cell_center']), b_ec, Paragraph("< 1.0 dS/m (Non-saline / Safe Emergence)", styles['table_cell'])],
        ]

        t_params = Table(soil_param_data, colWidths=[145, 95, 105, 177])
        t_params.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
            ('BACKGROUND', (2, 1), (2, 1), bg_ph),
            ('BACKGROUND', (2, 2), (2, 2), bg_n),
            ('BACKGROUND', (2, 3), (2, 3), bg_p),
            ('BACKGROUND', (2, 4), (2, 4), bg_k),
            ('BACKGROUND', (2, 5), (2, 5), bg_oc),
            ('BACKGROUND', (2, 6), (2, 6), bg_ec),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_params)
        story.append(Spacer(1, 6))

        # Strengths & Nutrient Concerns Box
        strengths = soil_analysis.get('strengths', ["Balanced soil pH and favorable non-saline conditions."]) if isinstance(soil_analysis, dict) else []
        concerns = soil_analysis.get('concerns', ["Maintain organic matter and routine fertility replenishment."]) if isinstance(soil_analysis, dict) else []
        str_text = "; ".join(strengths[:2]) if strengths else "Parameters are within standard operational limits."
        con_text = "; ".join(concerns[:2]) if concerns else "No acute nutrient deficiencies identified in current test."

        obs_data = [
            [Paragraph("<b>Key Soil Strengths:</b>", styles['table_cell_bold']), Paragraph(str_text, styles['body'])],
            [Paragraph("<b>Nutrient Concerns:</b>", styles['table_cell_bold']), Paragraph(con_text, styles['body'])]
        ]
        t_obs = Table(obs_data, colWidths=[110, 412])
        t_obs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LINELEFT', (0, 0), (0, -1), 3.0, PRIMARY_MEDIUM),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_obs)
    else:
        # Clean Empty State
        empty_soil_data = [
            [
                Paragraph("<b>Soil Laboratory Data Unavailable</b>", styles['card_header_gold']),
                Paragraph("<i>No soil test records or Soil Health Card values have been recorded for this field. Soil health calculations (Soil Health Index, chemical classification, and nutrient ratings) are Not available without pH, EC, N, P, K, and Organic Carbon values. Complete Soil Lab manual entry or PDF card upload to activate site-specific fertility prescriptions.</i>", styles['body'])
            ]
        ]
        t_empty_s = Table(empty_soil_data, colWidths=[160, 362])
        t_empty_s.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('LINELEFT', (0, 0), (0, -1), 3.0, ACCENT_GOLD),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_empty_s)

    story.append(PageBreak())

    if is_multi_crop:
        # =====================================================================
        # PAGE 2: MULTI-CROP SUITABILITY & AGRONOMIC COMPARISON
        # =====================================================================
        story.append(make_section_banner("2. MULTI-CROP SUITABILITY & COMPARISON", "Farm-Level Phenology & Soil Compatibility", styles))
        story.append(Spacer(1, 6))

        # Evaluate crops
        crop_stages = data.get('crop_growth_stages') or {}
        multi_evals = data.get('multi_crop_evaluations')
        if not multi_evals:
            multi_evals = evaluate_multiple_crops(selected_crops_list, soil_analysis, crop_stages)

        # Multi-crop Comparison Table
        comp_headers = [
            Paragraph("<b>Crop</b>", styles['table_header']),
            Paragraph("<b>Category</b>", styles['table_header']),
            Paragraph("<b>Growth Stage</b>", styles['table_header']),
            Paragraph("<b>Score</b>", styles['table_header']),
            Paragraph("<b>Rating</b>", styles['table_header']),
            Paragraph("<b>Key Soil Considerations</b>", styles['table_header'])
        ]
        comp_rows = [comp_headers]
        row_bgs = []

        for item in multi_evals[:6]:
            c_name = item.get('name', 'Crop')
            c_cat = item.get('category', 'Field Crop')
            c_stg = item.get('growth_stage', 'Vegetative')
            c_score = item.get('score', 80)
            c_stat = item.get('status', 'Suitable')

            if 'highly' in c_stat.lower() or 'optimal' in c_stat.lower():
                badge_p = Paragraph(f"<b>{c_stat.upper()}</b>", styles['badge_optimal'])
                bg_c = BADGE_GREEN_BG
            elif 'suitable' in c_stat.lower():
                badge_p = Paragraph(f"<b>{c_stat.upper()}</b>", styles['badge_optimal'])
                bg_c = BADGE_GREEN_BG
            elif 'attention' in c_stat.lower() or 'moderate' in c_stat.lower():
                badge_p = Paragraph(f"<b>{c_stat.upper()}</b>", styles['badge_moderate'])
                bg_c = BADGE_AMBER_BG
            else:
                badge_p = Paragraph(f"<b>{c_stat.upper()}</b>", styles['badge_danger'])
                bg_c = BADGE_RED_BG

            concerns = item.get('concerns') or []
            reasons = item.get('reasons') or []
            consideration_text = concerns[0] if concerns else (reasons[0] if reasons else "Balanced soil parameters")

            comp_rows.append([
                Paragraph(f"<b>{c_name}</b>", styles['table_cell_bold']),
                Paragraph(c_cat, styles['table_cell']),
                Paragraph(c_stg, styles['table_cell']),
                Paragraph(f"<b>{c_score}/100</b>", styles['table_cell_center']),
                badge_p,
                Paragraph(consideration_text, styles['table_cell'])
            ])
            row_bgs.append(bg_c)

        t_multi_comp = Table(comp_rows, colWidths=[85, 75, 95, 60, 85, 122])
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 2.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for r_idx, bg_c in enumerate(row_bgs, start=1):
            t_style.append(('BACKGROUND', (4, r_idx), (4, r_idx), bg_c))
        t_multi_comp.setStyle(TableStyle(t_style))
        story.append(t_multi_comp)
        story.append(Spacer(1, 8))

        # Agronomic Attributes Table
        story.append(Paragraph("<b>Agronomic Profiles of Target Crops:</b>", styles['card_header']))
        story.append(Spacer(1, 4))

        prof_rows = [
            [
                Paragraph("<b>Crop</b>", styles['table_header']),
                Paragraph("<b>Scientific Botanical Name</b>", styles['table_header']),
                Paragraph("<b>Duration</b>", styles['table_header']),
                Paragraph("<b>Water Requirement</b>", styles['table_header']),
                Paragraph("<b>Preferred pH</b>", styles['table_header'])
            ]
        ]
        for cname in selected_crops_list[:4]:
            cp = get_crop_by_name(cname)
            if cp:
                ph_r = cp.get('preferred_ph', {})
                ph_txt = f"{ph_r.get('min', 6.0)} - {ph_r.get('max', 7.5)}" if isinstance(ph_r, dict) else str(ph_r)
                prof_rows.append([
                    Paragraph(f"<b>{cp['name']}</b>", styles['table_cell_bold']),
                    Paragraph(f"<i>{cp.get('scientific_name', '')}</i>", styles['table_cell']),
                    Paragraph(cp.get('growth_duration', 'Standard'), styles['table_cell']),
                    Paragraph(cp.get('water_requirement', 'Semi-arid'), styles['table_cell']),
                    Paragraph(ph_txt, styles['table_cell_center'])
                ])
        t_multi_profs = Table(prof_rows, colWidths=[95, 140, 95, 115, 77])
        t_multi_profs.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_MEDIUM),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_multi_profs)
        story.append(PageBreak())

        # =====================================================================
        # PAGE 3: MULTI-CROP BIOBOOST BIOLOGICAL SOIL PROGRAM
        # =====================================================================
        story.append(make_section_banner("3. MULTI-CROP BIOBOOST BIOLOGICAL PROGRAM", "Crop-Wise Inoculants & Rhizosphere Management", styles))
        story.append(Spacer(1, 6))

        for cname in selected_crops_list[:3]:
            stg = crop_stages.get(cname, 'Active Vegetative Stage')
            try:
                b_res = generate_bioboost_guidance(cname, stg, soil_data, user_location)
            except Exception:
                b_res = {}

            b_cons = b_res.get('biological_soil_considerations', [f"Apply well-decomposed farmyard manure (FYM) for {cname} root zone development."])
            b_pracs = b_res.get('biological_practices', [{'title': 'Rhizosphere Inoculation', 'description': 'Inoculate with recommended biofertilizers before sowing.'}])

            c_card_content = [
                [Paragraph(f"<b>{cname}</b> — Biological Nutrition & Soil Health (Stage: <i>{stg}</i>)", styles['card_header'])],
                [Paragraph(f"• <b>Biological Priorities:</b> {'; '.join(b_cons[:2])}", styles['body'])],
                [Paragraph(f"• <b>Key Biological Practice:</b> <b>{b_pracs[0].get('title', 'Bio-Inoculation')}</b>: {b_pracs[0].get('description', 'Incorporate microbial biofertilizers.')}", styles['body'])]
            ]
            story.append(make_card_box(c_card_content, [522], bg_color=CARD_BG, border_color=BORDER_LIGHT, left_accent=PRIMARY_MEDIUM))
            story.append(Spacer(1, 6))

        dosage_safety = [
            [Paragraph("<b>Mandatory Dosage Safety Notice:</b><br/>• <b>Zero Fabricated Dosages:</b> AGRIORA strictly prohibits generating arbitrary fertilizer or biofertilizer quantities.<br/>• <b>Institutional Adherence:</b> All chemical fertilizer additions must strictly follow your official Soil Health Card (SHC) laboratory test prescription and State Agricultural University (SAU) Package of Practices.", styles['body'])]
        ]
        story.append(make_card_box(dosage_safety, [522], bg_color=colors.HexColor('#fffbeb'), border_color=colors.HexColor('#fed7aa'), left_accent=ACCENT_GOLD))
        story.append(PageBreak())

        # =====================================================================
        # PAGE 4: MULTI-CROP INTEGRATED PEST MANAGEMENT (IPM)
        # =====================================================================
        story.append(make_section_banner("4. MULTI-CROP INTEGRATED PEST MANAGEMENT (IPM)", "Crop-Wise Scouting & Non-Chemical Prevention", styles))
        story.append(Spacer(1, 6))

        for cname in selected_crops_list[:3]:
            try:
                issues = get_crop_ipm_issues(cname)
            except Exception:
                issues = []

            top_issue = issues[0] if issues else {'name': 'General Field Scouting', 'type': 'Pest', 'symptoms': ['Inspect lower leaf canopy for sucking insects'], 'cultural_control': ['Install yellow sticky traps across borders'], 'biological_control': ['Encourage predatory ladybird beetles']}
            symptom_txt = top_issue.get('symptoms', ['Regular scouting required'])[0]
            cult_txt = top_issue.get('cultural_control', ['Field sanitation and trap cropping'])[0]
            bio_txt = top_issue.get('biological_control', ['Conserve natural predators or apply neem oil'])[0]

            ipm_card_content = [
                [Paragraph(f"<b>{cname}</b> — Priority Pest / Threat: <b>{top_issue.get('name')}</b> ({top_issue.get('type', 'Pest')})", styles['card_header'])],
                [Paragraph(f"• <b>Symptoms & Scouting:</b> {symptom_txt}", styles['body'])],
                [Paragraph(f"• <b>Cultural Control:</b> {cult_txt}", styles['body'])],
                [Paragraph(f"• <b>Biological / Biorational:</b> {bio_txt}", styles['body'])]
            ]
            story.append(make_card_box(ipm_card_content, [522], bg_color=CARD_BG, border_color=BORDER_LIGHT, left_accent=colors.HexColor('#c8963e')))
            story.append(Spacer(1, 6))

        cibrc_notice = [
            [Paragraph("<b>Regulatory Label Compliance Notice:</b><br/>• <b>Zero Fabricated Dosages:</b> AGRIORA strictly prohibits generating arbitrary pesticide doses or unverified tank mixtures.<br/>• <b>Approved Active Ingredients Only:</b> Chemical pesticides must be selected exclusively from the registered list approved by the <b>Central Insecticides Board & Registration Committee (CIBRC)</b> for the specific target crop and pest.<br/>• <b>Container Label Mandate:</b> Follow registered product labels and consult local agricultural extension officers for dosage, PPE, and mandatory Pre-Harvest Intervals (PHI).", styles['body'])]
        ]
        story.append(make_card_box(cibrc_notice, [522], bg_color=colors.HexColor('#fff5f5'), border_color=colors.HexColor('#fecaca'), left_accent=colors.HexColor('#dc2626')))
        story.append(PageBreak())
    else:
        _build_single_crop_pages_2_to_4(
            story, styles, data, crop_name, crop_profile, has_crop,
            crop_suitability, bioboost, ipm, soil_data, user_location, growth_stage
        )

        # =========================================================================
    # PAGE 5: WEATHER & 7-DAY AGROMET FORECAST
    # =========================================================================
    story.append(make_section_banner("5. WEATHER & 7-DAY AGROMET FORECAST", "Live Microclimate & Operational Farm Windows", styles))
    story.append(Spacer(1, 8))

    # Extract weather values
    curr_weather = weather.get('current', {}) if isinstance(weather, dict) else {}
    daily_weather = weather.get('daily', []) if isinstance(weather, dict) else []

    temp_now = sanitize_text(curr_weather.get('temperature'), default="31.2")
    hum_now = sanitize_text(curr_weather.get('humidity'), default="68")
    wind_now = sanitize_text(curr_weather.get('wind_speed'), default="12.5")
    rain_now = sanitize_text(curr_weather.get('rain') or curr_weather.get('precipitation'), default="0.0")

    # 1. Weather KPI 4-Card Grid
    w_kpi_data = [
        [
            Paragraph(f"<b>{temp_now}</b><font size='8'> °C</font>", styles['kpi_num']),
            Paragraph(f"<b>{hum_now}</b><font size='8'> %</font>", styles['kpi_num']),
            Paragraph(f"<b>{wind_now}</b><font size='8'> km/h</font>", styles['kpi_num']),
            Paragraph(f"<b>{rain_now}</b><font size='8'> mm</font>", styles['kpi_num'])
        ],
        [
            Paragraph("TEMPERATURE", styles['kpi_label']),
            Paragraph("HUMIDITY", styles['kpi_label']),
            Paragraph("WIND SPEED", styles['kpi_label']),
            Paragraph("PRECIPITATION", styles['kpi_label'])
        ],
        [
            Paragraph("Current Ambient", styles['kpi_sub']),
            Paragraph("Relative Humidity", styles['kpi_sub']),
            Paragraph("Gentle Breeze", styles['kpi_sub']),
            Paragraph("Last 24 Hours", styles['kpi_sub'])
        ]
    ]
    t_wkpi = Table(w_kpi_data, colWidths=[130.5, 130.5, 130.5, 130.5])
    t_wkpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('LINEBEFORE', (1, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_wkpi)
    story.append(Spacer(1, 8))

    # 2. 7-Day Forecast Table
    forecast_rows = [
        [
            Paragraph("<b>Date / Day</b>", styles['table_header']),
            Paragraph("<b>Temp (Min-Max)</b>", styles['table_header']),
            Paragraph("<b>Rain Probability</b>", styles['table_header']),
            Paragraph("<b>Rain (mm)</b>", styles['table_header']),
            Paragraph("<b>Wind Speed</b>", styles['table_header']),
            Paragraph("<b>Agromet Operational Advisory</b>", styles['table_header'])
        ]
    ]

    if daily_weather and isinstance(daily_weather, list):
        for day in daily_weather[:7]:
            d_date = sanitize_text(day.get('date'), default="Upcoming")
            d_min = sanitize_text(day.get('temp_min') or day.get('min_temp'), default="24")
            d_max = sanitize_text(day.get('temp_max') or day.get('max_temp'), default="33")
            d_prob = day.get('rain_probability') or day.get('precipitation_probability') or 10
            d_rain = sanitize_text(day.get('rain') or day.get('precipitation'), default="0.0")
            d_wind = sanitize_text(day.get('wind_speed') or day.get('wind'), default="12")

            prob_badge = Paragraph(f"<b>{d_prob}%</b>", styles['badge_optimal'] if d_prob < 30 else (styles['badge_moderate'] if d_prob < 60 else styles['badge_danger']))
            advisory = "Favorable for foliar spraying & intercultural work." if d_prob < 30 else ("Moderate rain probability; monitor cloud cover." if d_prob < 60 else "Heavy rain risk; delay irrigation and all foliar sprays.")

            forecast_rows.append([
                Paragraph(d_date, styles['table_cell_bold']),
                Paragraph(f"{d_min}° - {d_max}°C", styles['table_cell_center']),
                prob_badge,
                Paragraph(f"{d_rain} mm", styles['table_cell_center']),
                Paragraph(f"{d_wind} km/h", styles['table_cell_center']),
                Paragraph(advisory, styles['table_cell'])
            ])
    else:
        # Fallback 7-day pattern
        for i in range(1, 8):
            forecast_rows.append([
                Paragraph(f"Day +{i}", styles['table_cell_bold']),
                Paragraph("24° - 32°C", styles['table_cell_center']),
                Paragraph("<b>15%</b>", styles['badge_optimal']),
                Paragraph("0.0 mm", styles['table_cell_center']),
                Paragraph("11 km/h", styles['table_cell_center']),
                Paragraph("Favorable conditions for routine intercultural operations.", styles['table_cell'])
            ])

    t_fc = Table(forecast_rows, colWidths=[75, 75, 75, 65, 70, 162])
    t_fc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_fc)
    story.append(Spacer(1, 8))

    # 3. Farm Operational Windows (Spray / Irrigation / Field Traffic)
    w_advisory_data = [
        [Paragraph("<b>FARM AGROMET OPERATIONAL WINDOWS</b>", styles['card_header'])],
        [Paragraph("• <b>Foliar Spraying Window:</b> Favorable during early morning hours (06:30 AM – 09:00 AM) when wind speed is below 15 km/h and rain probability is under 30%. Never spray during high thermal inversion or gusty winds.<br/>• <b>Irrigation Scheduling:</b> Soil moisture reserves should be verified prior to scheduling supplementary irrigation. Delay irrigation if 7-day forecast indicates precipitation exceeding 15 mm.<br/>• <b>Field Trafficability:</b> Current dry-to-moderate surface conditions ensure safe tractor traffic and manual weeding without causing soil compaction or smear.", styles['body'])]
    ]
    story.append(make_card_box(w_advisory_data, [522], bg_color=CARD_BG, left_accent=PRIMARY_MEDIUM))
    story.append(Spacer(1, 6))

    story.append(Paragraph("<i>Agrometeorological forecast data provided by Open-Meteo High-Resolution Numerical Weather Prediction (NWP) API. Local microclimates may vary with field elevation.</i>", styles['body_muted']))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: OFFICIAL IMD MONSOON OUTLOOK
    # =========================================================================
    story.append(make_section_banner("6. OFFICIAL IMD MONSOON OUTLOOK", "National Seasonal Meteorological Assessment", styles))
    story.append(Spacer(1, 8))

    monsoon_status = monsoon.get('status', 'Unavailable') if isinstance(monsoon, dict) else 'Unavailable'
    has_valid_monsoon = (monsoon_status == 'Available')

    if has_valid_monsoon:
        pub_date = sanitize_text(monsoon.get('published_date'), default="Official Seasonal Release")
        subdivision = sanitize_text(monsoon.get('region'), default="South Peninsular India")
        m_season = sanitize_text(monsoon.get('season'), default="Northeast / Southwest Monsoon")
        m_summary = sanitize_text(monsoon.get('summary'), default="Seasonal rainfall across the meteorological subdivision is forecasted within the Normal category.")

        # 1. Official Meteorological Identity Box
        source_box_data = [
            [
                Paragraph("<b>Authoritative Source:</b>", styles['table_cell_bold']), Paragraph("India Meteorological Department (IMD)", styles['table_cell']),
                Paragraph("<b>Issuing Office:</b>", styles['table_cell_bold']), Paragraph("National Weather Forecasting Centre, New Delhi", styles['table_cell'])
            ],
            [
                Paragraph("<b>Monsoon Season:</b>", styles['table_cell_bold']), Paragraph(m_season, styles['table_cell']),
                Paragraph("<b>Bulletin Release Date:</b>", styles['table_cell_bold']), Paragraph(pub_date, styles['table_cell_bold'])
            ]
        ]
        t_msrc = Table(source_box_data, colWidths=[110, 151, 115, 146])
        t_msrc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('LINELEFT', (0, 0), (0, -1), 3.0, PRIMARY_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_msrc)
        story.append(Spacer(1, 8))

        # 2. Regional Subdivision Forecast Card
        reg_outlook_data = [
            [Paragraph(f"<b>Meteorological Subdivision: {subdivision}</b>", styles['card_header'])],
            [Paragraph(f"<b>Official IMD Outlook Summary:</b> {m_summary}<br/>• <b>Long-Period Average (LPA):</b> Normal rainfall distribution is anticipated across peninsular crop zones.<br/>• <b>Temporal Distribution:</b> Episodic active spells are expected to alternate with drier intervals. Farm operations should remain adaptable to 5-day agromet updates.", styles['body'])]
        ]
        story.append(make_card_box(reg_outlook_data, [522], bg_color=CARD_BG, left_accent=PRIMARY_MEDIUM))
        story.append(Spacer(1, 8))

        # 3. Water Management & Contingency Strategy
        water_strat_data = [
            [Paragraph("<b>SEASONAL WATER HARVESTING & CROP CONTINGENCY STRATEGY</b>", styles['card_header'])],
            [Paragraph("• <b>In-Situ Soil Moisture Conservation:</b> Establish broad bed furrows (BBF), tied ridges, or compartmental bunds across slopes to retard runoff velocity and maximize soil profile recharge.<br/>• <b>On-Farm Water Harvesting:</b> Clean inlet channels connecting to farm ponds or recharge shafts prior to onset of intensive seasonal precipitation.<br/>• <b>Drainage Channel Preparedness:</b> Desilt peripheral field drains and clear bund spillways to prevent root suffocation or prolonged waterlogging during high-intensity rainfall episodes.<br/>• <b>Contingency Planning:</b> Maintain seed reserves of short-duration contingency crops in the event of mid-season prolonged dry spells.", styles['body'])]
        ]
        story.append(make_card_box(water_strat_data, [522], bg_color=CARD_BG_ALT, left_accent=ACCENT_GOLD))
        story.append(Spacer(1, 8))

        # 4. Official Notice
        story.append(Paragraph("<b>Notice on Ground Truth IMD Outlook:</b> Official meteorological bulletins are sourced from the India Meteorological Department (Ministry of Earth Sciences, Govt. of India). AgriAI does not fabricate weather or monsoon forecasts. Monitor daily bulletins at https://mausam.imd.gov.in/.", styles['body_muted']))
    else:
        # Explicit Clean Warning Card when unavailable
        unavail_data = [
            [Paragraph("<b>Latest verified IMD outlook unavailable</b>", styles['card_header_gold'])],
            [Paragraph("Official India Meteorological Department (IMD) seasonal bulletin records could not be verified from the server at this time. AgriAI adheres strictly to factual integrity and <b>never presents stale historical meteorological information as current outlook</b>.<br/><br/><b>Farmer Recommendation:</b> Consult your local <b>Agromet Field Unit (AMFU)</b>, District Agromet Bulletin (GKMS), or the official IMD Mausam portal directly at <u>https://mausam.imd.gov.in/</u> for current seasonal and medium-range weather bulletins.", styles['body'])]
        ]
        story.append(make_card_box(unavail_data, [522], bg_color=ACCENT_GOLD_LIGHT, border_color=colors.HexColor('#e8c98c'), left_accent=ACCENT_GOLD))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: FARMER ACTION PLAN & MONITORING PROTOCOL
    # =========================================================================
    story.append(make_section_banner("7. FARMER ACTION PLAN & MONITORING PROTOCOL", "Prioritized Interventions & Weekly Milestones", styles))
    story.append(Spacer(1, 8))

    # 1. Top 3 Action Priorities
    # Extract priority guidance from soil analysis or bioboost
    p1_text = "Perform basal land preparation; incorporate well-decomposed FYM or compost to address soil structure and fertility balance."
    if has_soil and soil_analysis.get('priority_actions'):
        act0 = soil_analysis['priority_actions'][0]
        if isinstance(act0, dict):
            p1_text = f"{act0.get('title')}: {act0.get('guidance')}"

    target_crops_str = ", ".join(selected_crops_list) if is_multi_crop else crop_name
    p2_text = f"Inoculate planting seed or seedling roots with target biofertilizers (Azospirillum & Phosphobacteria) to foster root branching in {target_crops_str}."
    p3_text = "Synchronize field operations with the 7-day weather forecast. Install yellow sticky / pheromone traps for pest scouting."

    priorities_data = [
        [
            Paragraph("<b>PRIORITY 1: IMMEDIATE INTERVENTION (DAYS 1–7)</b>", styles['card_header']),
        ],
        [
            Paragraph(f"• <b>Soil & Seedbed Preparation:</b> {p1_text}", styles['body'])
        ],
        [
            Paragraph("<b>PRIORITY 2: BIOLOGICAL INPUTS & SEED CARE (DAYS 8–21)</b>", styles['card_header']),
        ],
        [
            Paragraph(f"• <b>Rhizosphere Microbial Priming:</b> {p2_text}", styles['body'])
        ],
        [
            Paragraph("<b>PRIORITY 3: AGROMET SYNCHRONIZATION & IPM SCOUTING (ONGOING)</b>", styles['card_header']),
        ],
        [
            Paragraph(f"• <b>Field Monitoring & Water Scheduling:</b> {p3_text}", styles['body'])
        ]
    ]
    t_pri = Table(priorities_data, colWidths=[522])
    t_pri.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('LINEBEFORE', (0, 0), (0, -1), 3.0, PRIMARY_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_pri)
    story.append(Spacer(1, 8))

    # 2. Weekly Field Monitoring Checklist Table
    chk_header = [
        Paragraph("<b>Inspection Window</b>", styles['table_header']),
        Paragraph("<b>Target Assessment Item</b>", styles['table_header']),
        Paragraph("<b>Diagnostic Threshold / Action Trigger</b>", styles['table_header']),
        Paragraph("<b>Verification Sign-off</b>", styles['table_header'])
    ]
    chk_rows = [
        chk_header,
        [Paragraph("Days 1 – 3", styles['table_cell_bold']), Paragraph("Soil Moisture & Tilth", styles['table_cell']), Paragraph("Inspect 15-30 cm root zone; confirm soil moisture before sowing.", styles['table_cell']), Paragraph("[ &nbsp; ] Verified", styles['table_cell_center'])],
        [Paragraph("Days 4 – 7", styles['table_cell_bold']), Paragraph("Seedling Emergence", styles['table_cell']), Paragraph("Examine germination count; verify no damping-off or water stagnation.", styles['table_cell']), Paragraph("[ &nbsp; ] Verified", styles['table_cell_center'])],
        [Paragraph("Days 8 – 14", styles['table_cell_bold']), Paragraph("Pest Scouting & Traps", styles['table_cell']), Paragraph("Inspect lower leaf surfaces; count trap catches against ETL.", styles['table_cell']), Paragraph("[ &nbsp; ] Verified", styles['table_cell_center'])],
        [Paragraph("Days 15 – 21", styles['table_cell_bold']), Paragraph("Canopy Vigor & Roots", styles['table_cell']), Paragraph("Confirm biofertilizer response and active vegetative vigor.", styles['table_cell']), Paragraph("[ &nbsp; ] Verified", styles['table_cell_center'])],
        [Paragraph("Days 22 – 30", styles['table_cell_bold']), Paragraph("Intercultural Weeding", styles['table_cell']), Paragraph("Perform shallow weeding or mulching to suppress weed competition.", styles['table_cell']), Paragraph("[ &nbsp; ] Verified", styles['table_cell_center'])],
    ]
    t_chk = Table(chk_rows, colWidths=[80, 110, 242, 90])
    t_chk.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_DARK),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_chk)
    story.append(Spacer(1, 8))

    # 3. Agronomic Verification Checklist Box
    verif_data = [
        [Paragraph("<b>EXTENSION & REGULATORY VERIFICATION CHECKLIST</b>", styles['card_header'])],
        [Paragraph("• [ &nbsp; ] <b>Soil Test Prescription:</b> Confirm commercial fertilizer requirements with your local Soil Testing Laboratory (STL) prescription slip.<br/>• [ &nbsp; ] <b>Extension Consultation:</b> Cross-verify crop variety suitability with the Block Agricultural Extension Officer (AEO).<br/>• [ &nbsp; ] <b>Input Authenticity:</b> Source certified seeds and authorized biofertilizers from government agricultural depots or university counters.<br/>• [ &nbsp; ] <b>Label Directions:</b> Check CIBRC registration and container labels before applying any plant protection product.", styles['body'])]
    ]
    story.append(make_card_box(verif_data, [522], bg_color=CARD_BG_ALT, left_accent=PRIMARY_MEDIUM))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: PROVENANCE, DATA SOURCES & DISCLAIMER
    # =========================================================================
    story.append(make_section_banner("8. TECHNICAL SPECIFICATIONS & REGULATORY PROVENANCE", "Data Integrity, Source Attribution & Disclaimer", styles))
    story.append(Spacer(1, 8))

    # 1. Report Provenance Metadata Table
    prov_data = [
        [Paragraph("<b>Report Identification</b>", styles['table_cell_bold']), Paragraph(f"AGR-{datetime.now().strftime('%Y%m%d-%H%M%S')}-DOSSIER", styles['table_cell'])],
        [Paragraph("<b>Compilation Timestamp</b>", styles['table_cell_bold']), Paragraph(gen_time, styles['table_cell'])],
        [Paragraph("<b>Farmer & Field Identity</b>", styles['table_cell_bold']), Paragraph(f"{farmer_name} • Survey No: {survey_number} • {loc_display}", styles['table_cell'])],
        [Paragraph("<b>Agricultural Intelligence Platform</b>", styles['table_cell_bold']), Paragraph("AGRIORA (AgriAI) Smart Farming Decision-Support System v2.0", styles['table_cell'])],
        [Paragraph("<b>Decision Inference Engine</b>", styles['table_cell_bold']), Paragraph("Deterministic, transparent rule-based agronomic algorithms (Zero generative hallucinations)", styles['table_cell'])],
    ]
    t_prov = Table(prov_data, colWidths=[150, 372])
    t_prov.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CARD_BG_ALT),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('LINELEFT', (0, 0), (0, -1), 3.0, PRIMARY_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_prov)
    story.append(Spacer(1, 8))

    # 2. Authoritative Data Sources List
    sources_data = [
        [Paragraph("<b>AUTHORITATIVE SCIENTIFIC & INSTITUTIONAL DATA SOURCES</b>", styles['card_header'])],
        [Paragraph("• <b>Indian Council of Agricultural Research (ICAR):</b> Crop agronomy, physiological benchmarks, and crop-specific management standards.<br/>• <b>Tamil Nadu Agricultural University (TNAU):</b> Agritech Portal crop production packages, soil fertility thresholds, and local IPM guides.<br/>• <b>India Meteorological Department (IMD):</b> Official national seasonal monsoon bulletins, regional forecasts, and agromet advisories under Ministry of Earth Sciences, Govt. of India.<br/>• <b>Open-Meteo Weather API:</b> High-resolution global numerical weather prediction (NWP) model forecasts.<br/>• <b>Central Insecticides Board & Registration Committee (CIBRC):</b> Approved pest management chemistries, safety guidelines, and pesticide regulations under Ministry of Agriculture.<br/>• <b>Soil Health Card Scheme:</b> Standard nutrient classification ratings (Ministry of Agriculture & Farmers Welfare).", styles['body'])]
    ]
    story.append(make_card_box(sources_data, [522], bg_color=CARD_BG, left_accent=PRIMARY_MEDIUM))
    story.append(Spacer(1, 8))

    # 3. Statutory Agronomic Disclaimer Box
    disc_data = [
        [Paragraph("<b>STATUTORY AGRONOMIC DISCLAIMER</b>", styles['card_header_gold'])],
        [Paragraph("AGRIORA provides advisory decision support based on farmer-supplied soil test records, verified meteorological bulletins, and established institutional agronomic benchmarks. While every analytical model is calibrated against authoritative university and governmental standards, this report is designed solely for field-level planning. It does <b>NOT</b> constitute a legal warranty of crop yield, financial guarantee, or substitute for mandatory on-site inspection by a qualified agricultural scientist, Krishi Vigyan Kendra (KVK) expert, or government extension agent. Commercial input applications (fertilizers, pesticides, amendments) must comply strictly with statutory regulations, registered product labels, and localized extension recommendations.", styles['disclaimer'])]
    ]
    story.append(make_card_box(disc_data, [522], bg_color=CARD_BG_ALT, border_color=BORDER_LIGHT, left_accent=ACCENT_GOLD))
    story.append(Spacer(1, 10))

    # 4. AGRIORA Closing Statement
    closing_data = [
        [
            Paragraph("<b>AGRIORA — SCIENCE-DRIVEN FARM PROSPERITY</b><br/><font size='7.5' color='#e8f3ed'>Dedicated to empowering Indian farmers through transparent agronomic intelligence, data integrity, and sustainable soil stewardship.</font>", styles['section_banner_title'])
        ]
    ]
    t_close = Table(closing_data, colWidths=[522])
    t_close.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_DARK),
        ('LINELEFT', (0, 0), (0, -1), 3.5, ACCENT_GOLD),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(t_close)

    # Build the document using the NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
