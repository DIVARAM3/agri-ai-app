"""
AgriAI - Soil Report Extractor
Extracts key soil parameters from text-based PDF reports using PyMuPDF (fitz).
Parameters extracted:
- pH (Soil Reaction)
- Nitrogen (Available N)
- Phosphorus (Available P)
- Potassium (Available K)
- Organic Carbon (OC)
- Electrical Conductivity (EC)
"""

import re
import os
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# Sane agronomic validation ranges to prevent false-positive extraction of random numbers
VALIDATION_RANGES = {
    'ph': (3.0, 11.0),
    'nitrogen': (5.0, 1500.0),
    'phosphorus': (0.5, 400.0),
    'potassium': (5.0, 2000.0),
    'organic_carbon': (0.01, 12.0),
    'ec': (0.01, 20.0)
}

PARAM_DISPLAY = {
    'ph': {'name': 'pH Level', 'unit': '', 'desc': 'Soil Acidity / Alkalinity'},
    'nitrogen': {'name': 'Nitrogen (N)', 'unit': 'kg/ha', 'desc': 'Available Nitrogen'},
    'phosphorus': {'name': 'Phosphorus (P)', 'unit': 'kg/ha', 'desc': 'Available Phosphorus'},
    'potassium': {'name': 'Potassium (K)', 'unit': 'kg/ha', 'desc': 'Available Potassium'},
    'organic_carbon': {'name': 'Organic Carbon (OC)', 'unit': '%', 'desc': 'Total Organic Carbon'},
    'ec': {'name': 'Electrical Conductivity (EC)', 'unit': 'dS/m', 'desc': 'Salinity / Soluble Salts'}
}


def is_valid_param_value(param: str, val: float) -> bool:
    """Check if value falls into a realistic agronomic range."""
    if param not in VALIDATION_RANGES:
        return False
    min_v, max_v = VALIDATION_RANGES[param]
    return min_v <= val <= max_v


def clean_number_str(s: str) -> float | None:
    """Convert number string to float, removing commas or leading/trailing chars."""
    if not s:
        return None
    s = s.strip().replace(',', '')
    # Ignore ratio patterns like 1:2.5 or 1:2
    if ':' in s or '/' in s:
        return None
    try:
        val = float(s)
        return val
    except ValueError:
        return None


def extract_parameters_from_text(text: str) -> dict:
    """
    Extract soil parameters from plain text string.
    Returns:
    {
        "ph": float or None,
        "nitrogen": float or None,
        "phosphorus": float or None,
        "potassium": float or None,
        "organic_carbon": float or None,
        "ec": float or None
    }
    """
    results = {
        'ph': None,
        'nitrogen': None,
        'phosphorus': None,
        'potassium': None,
        'organic_carbon': None,
        'ec': None
    }

    if not text:
        return results

    # Normalize whitespace while preserving line structure
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # High-priority regex patterns (label and value on same line or separated by colon/tab/spaces)
    patterns = {
        'ph': [
            # Matches: "pH: 6.8", "Soil pH : 7.2", "Reaction (pH) : 7.4", "pH (1:2.5) : 7.15"
            r'(?:soil\s+)?(?:reaction\s+)?(?:soil\s+reaction\s+)?(?:soil\s+)?ph(?:\s*\([^)]*\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bph\s+value\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bph\b\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)'
        ],
        'nitrogen': [
            # Matches: "Available Nitrogen (N): 280", "Available N : 240 kg/ha", "Nitrogen: 280"
            r'(?:available\s+)?nitrogen(?:\s*\([Nn]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'(?:available\s+)?total\s+nitrogen(?:\s*\([Nn]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bavailable\s+n\b(?:\s*\([^)]*\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bN\s*[:\-|=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kg/ha|mg/kg|ppm)?'
        ],
        'phosphorus': [
            # Matches: "Available Phosphorus (P): 18.5", "Phosphorus: 22", "Available P: 18"
            r'(?:available\s+)?phosphorus(?:\s*\([Pp]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'(?:available\s+)?phosphate(?:\s*\([Pp]2[Oo]5\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bavailable\s+p\b(?:\s*\([^)]*\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bP\s*[:\-|=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kg/ha|mg/kg|ppm)?'
        ],
        'potassium': [
            # Matches: "Available Potassium (K): 320", "Potassium: 210", "Available K: 320"
            r'(?:available\s+)?potassium(?:\s*\([Kk]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'(?:available\s+)?potash(?:\s*\([Kk]2[Oo]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bavailable\s+k\b(?:\s*\([^)]*\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bK\s*[:\-|=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kg/ha|mg/kg|ppm)?'
        ],
        'organic_carbon': [
            # Matches: "Organic Carbon (OC): 0.72", "OC: 0.65 %", "Organic Carbon: 1.2"
            r'(?:total\s+)?organic\s+carbon(?:\s*\([Oo][Cc]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\borganic\s+matter(?:\s*\([Oo][Mm]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\b(?:soc|toc)\b\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bOC\s*[:\-|=]\s*([0-9]+(?:\.[0-9]+)?)\s*%?'
        ],
        'ec': [
            # Matches: "Electrical Conductivity (EC): 0.42", "EC: 0.35 dS/m", "Electrical Conductivity : 0.45"
            r'electrical\s+conductivity(?:\s*\([Ee][Cc]\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bsalinity(?:\s*\(ec\))?\s*[:\-|=\t ]\s*([0-9]+(?:\.[0-9]+)?)',
            r'\bEC\b\s*[:\-|=]\s*([0-9]+(?:\.[0-9]+)?)\s*(?:ds/m|ms/cm|mmhos/cm)?'
        ]
    }

    # Pass 1: Try regex on single line or full text
    for param, regex_list in patterns.items():
        for pattern in regex_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                candidate = clean_number_str(match.group(1))
                if candidate is not None and is_valid_param_value(param, candidate):
                    results[param] = candidate
                    break

    # Pass 2: Line-by-line tabular parsing for values that were not matched (e.g. multi-column tables)
    # PyMuPDF tables often separate labels and numbers into adjacent tokens or adjacent lines
    param_keywords = {
        'ph': [r'\bph\b', r'\bsoil\s+reaction\b'],
        'nitrogen': [r'\bnitrogen\b', r'\bavailable\s+n\b'],
        'phosphorus': [r'\bphosphorus\b', r'\bavailable\s+p\b'],
        'potassium': [r'\bpotassium\b', r'\bavailable\s+k\b'],
        'organic_carbon': [r'\borganic\s+carbon\b', r'\boc\b'],
        'ec': [r'\belectrical\s+conductivity\b', r'\bec\b']
    }

    for i, line in enumerate(lines):
        line_clean = line.strip()
        for param, keywords in param_keywords.items():
            if results[param] is not None:
                continue

            matches_keyword = any(re.search(kw, line_clean, re.IGNORECASE) for kw in keywords)
            if matches_keyword:
                # 1. Search for numbers within this line itself
                # Split tokens by space/tab/pipe/colon
                tokens = re.findall(r'[-+]?[0-9]*\.?[0-9]+', line_clean)
                for token in tokens:
                    # Ignore numbers that look like dilutions e.g. 1:2.5 or integers like "1" or "2" if param is Nitrogen/Potassium
                    val = clean_number_str(token)
                    if val is not None and is_valid_param_value(param, val):
                        results[param] = val
                        break

                # 2. If not found in current line, check next 1 or 2 lines (for vertical table output)
                if results[param] is None:
                    for offset in [1, 2]:
                        if i + offset < len(lines):
                            next_line = lines[i + offset]
                            tokens_next = re.findall(r'[-+]?[0-9]*\.?[0-9]+', next_line)
                            for token in tokens_next:
                                val = clean_number_str(token)
                                if val is not None and is_valid_param_value(param, val):
                                    results[param] = val
                                    break
                            if results[param] is not None:
                                break

    # Format numeric types cleanly (integers if whole numbers, else rounded floats)
    formatted = {}
    for k, v in results.items():
        if v is not None:
            if k in ['nitrogen', 'phosphorus', 'potassium'] and v.is_integer():
                formatted[k] = int(v)
            else:
                formatted[k] = round(v, 2)
        else:
            formatted[k] = None

    return formatted


def extract_soil_parameters_from_pdf(pdf_path: str) -> dict:
    """
    Extract text and soil parameters from a PDF using PyMuPDF (fitz).
    Returns a dictionary:
    {
        "success": bool,
        "parameters": dict,
        "detected_count": int,
        "missing_count": int,
        "detected_keys": list,
        "missing_keys": list,
        "raw_text_length": int,
        "is_scanned_or_empty": bool,
        "error": str or None
    }
    """
    if not os.path.exists(pdf_path):
        return {
            "success": False,
            "error": "File does not exist.",
            "parameters": {k: None for k in VALIDATION_RANGES},
            "detected_count": 0,
            "missing_count": len(VALIDATION_RANGES),
            "detected_keys": [],
            "missing_keys": list(VALIDATION_RANGES.keys()),
            "raw_text_length": 0,
            "is_scanned_or_empty": False
        }

    if fitz is None:
        return {
            "success": False,
            "error": "PyMuPDF library is not installed.",
            "parameters": {k: None for k in VALIDATION_RANGES},
            "detected_count": 0,
            "missing_count": len(VALIDATION_RANGES),
            "detected_keys": [],
            "missing_keys": list(VALIDATION_RANGES.keys()),
            "raw_text_length": 0,
            "is_scanned_or_empty": False
        }

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to open PDF (file may be corrupted or encrypted): {str(e)}",
            "parameters": {k: None for k in VALIDATION_RANGES},
            "detected_count": 0,
            "missing_count": len(VALIDATION_RANGES),
            "detected_keys": [],
            "missing_keys": list(VALIDATION_RANGES.keys()),
            "raw_text_length": 0,
            "is_scanned_or_empty": False
        }

    try:
        full_text = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if text:
                full_text.append(text)
        
        extracted_text = "\n".join(full_text).strip()
        doc.close()
    except Exception as e:
        try:
            doc.close()
        except Exception:
            pass
        return {
            "success": False,
            "error": f"Error reading PDF pages: {str(e)}",
            "parameters": {k: None for k in VALIDATION_RANGES},
            "detected_count": 0,
            "missing_count": len(VALIDATION_RANGES),
            "detected_keys": [],
            "missing_keys": list(VALIDATION_RANGES.keys()),
            "raw_text_length": 0,
            "is_scanned_or_empty": False
        }

    # Check if empty or scanned (no text extractable)
    if not extracted_text or len(extracted_text) < 15:
        return {
            "success": True,
            "parameters": {k: None for k in VALIDATION_RANGES},
            "detected_count": 0,
            "missing_count": len(VALIDATION_RANGES),
            "detected_keys": [],
            "missing_keys": list(VALIDATION_RANGES.keys()),
            "raw_text_length": len(extracted_text),
            "is_scanned_or_empty": True,
            "error": None,
            "message": "Automatic extraction is unavailable for this report (scanned or image-only PDF). Please enter the values manually."
        }

    parameters = extract_parameters_from_text(extracted_text)

    detected = [k for k, v in parameters.items() if v is not None]
    missing = [k for k, v in parameters.items() if v is None]

    return {
        "success": True,
        "parameters": parameters,
        "detected_count": len(detected),
        "missing_count": len(missing),
        "detected_keys": detected,
        "missing_keys": missing,
        "raw_text_length": len(extracted_text),
        "is_scanned_or_empty": False,
        "error": None
    }
