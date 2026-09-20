import re
from typing import Dict, Any, Optional
from src.graph.embedded_graph import get_embedded_graph

# Common Indian soil keywords to class mapping
SOIL_KEYWORDS = {
    "clay": 1,
    "clayey": 1,
    "black": 2,
    "black soil": 2,
    "loam": 3,
    "loamy": 3,
    "sandy loam": 4,
    "sandy": 5,
    "red": 6,
    "alluvial": 7,
    "laterite": 8
}

COMMON_DISEASE_KEYWORDS = [
    "leaf blight", "bacterial blight", "ascochyta blight", "alternaria", 
    "leaf spot", "boll rot", "pink bollworm", "leaf curl", "rust", 
    "yellow rust", "stripe rust", "black rust", "stem rot", "root rot", 
    "powdery mildew", "downy mildew", "wilt", "fusarium wilt", "whitefly",
    "mealybug", "anthracnose", "caterpillar", "jassid", "aphid", "thrips"
]

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    NLP Entity & Intent Extractor for Agricultural Queries.
    Extracts crop, disease/symptoms, pincode, soil class, and user intent.
    """
    text_clean = text.lower().strip()
    
    # 1. Intent Detection
    intent = "general_advisory"
    if any(k in text_clean for k in ["treatment", "cure", "spray", "medicine", "control", "remedy", "protocol"]):
        intent = "treatment_plan"
    elif any(k in text_clean for k in ["stage", "phase", "growth", "duration", "timeline"]):
        intent = "crop_stages"
    elif any(k in text_clean for k in ["recommend", "best crop", "suitability", "yield", "zone", "grow"]):
        intent = "zone_recommendation"
    elif any(k in text_clean for k in ["disease", "symptom", "identify", "spots", "rot", "blight", "yellowing"]):
        intent = "disease_diagnosis"

    # 2. Dynamic Crop Extraction (matches against 164 known crops)
    graph = get_embedded_graph()
    identified_crop = None
    
    # Check multi-word and single-word crop names
    for crop_key, crop_data in graph.crops.items():
        # Match whole word
        pattern = r'\b' + re.escape(crop_key) + r'\b'
        if re.search(pattern, text_clean):
            identified_crop = crop_data["name"]
            break
            
    # Fallback common crops if exact boundary missed
    if not identified_crop:
        common_crops = ["cotton", "wheat", "rice", "paddy", "soybean", "mustard", "maize", "potato", "tomato", "sugarcane", "groundnut", "chickpea", "jute", "lentil", "onion"]
        for c in common_crops:
            if c in text_clean:
                profile = graph.get_crop_profile(c)
                if profile:
                    identified_crop = profile["name"]
                    break

    # 3. Pincode Extraction (6-digit Indian PIN code)
    pincode_match = re.search(r'\b[1-9][0-9]{5}\b', text)
    pincode = pincode_match.group(0) if pincode_match else None

    # 4. Soil Extraction
    soil_class = None
    for soil_kw, s_class in SOIL_KEYWORDS.items():
        if soil_kw in text_clean:
            soil_class = s_class
            break

    # 5. Disease / Symptom Extraction
    symptoms = ""
    for d_kw in COMMON_DISEASE_KEYWORDS:
        if d_kw in text_clean:
            symptoms = d_kw
            break
            
    # If no specific disease keyword, extract symptom phrase
    if not symptoms:
        # Strip query prefixes
        cleaned_query = re.sub(
            r'^(give|what is|tell me|show|how to cure|treatment for|plan for|spray for|advice for)\s+',
            '',
            text_clean
        )
        if identified_crop:
            cleaned_query = cleaned_query.replace(identified_crop.lower(), "").replace("crop", "").replace("disease", "").strip()
        symptoms = cleaned_query if len(cleaned_query) > 3 else "general health assessment"

    return {
        "intent": intent,
        "crop_name": identified_crop,
        "symptoms": symptoms,
        "pincode": pincode,
        "soil_class": soil_class,
        "raw_text": text
    }
