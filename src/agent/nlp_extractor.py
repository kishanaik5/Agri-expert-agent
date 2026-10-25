import re
import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from src.graph.embedded_graph import get_embedded_graph

# Load environment
load_dotenv()

# Indian soil keywords to class mapping (1 to 8)
SOIL_KEYWORDS = {
    "clay": 1,
    "clayey": 1,
    "heavy clay": 1,
    "black": 2,
    "black soil": 2,
    "regur": 2,
    "loam": 3,
    "loamy": 3,
    "sandy loam": 4,
    "sandy": 5,
    "red": 6,
    "red soil": 6,
    "alluvial": 7,
    "laterite": 8
}

SOIL_CLASS_TO_NAME = {
    1: "Clayey Soil (Class 1)",
    2: "Black Soil (Class 2)",
    3: "Loamy Soil (Class 3)",
    4: "Sandy Loam (Class 4)",
    5: "Sandy Soil (Class 5)",
    6: "Red Soil (Class 6)",
    7: "Alluvial Soil (Class 7)",
    8: "Laterite Soil (Class 8)"
}

SEASON_KEYWORDS = {
    "kharif": "KHARIF",
    "monsoon": "KHARIF",
    "rainy": "KHARIF",
    "rabi": "RABI",
    "winter": "RABI",
    "zaid": "ZAID",
    "summer": "ZAID",
    "annual": "LONGTERM",
    "perennial": "LONGTERM"
}

WATER_KEYWORDS = {
    "rainfed": "RAINFED",
    "rain fed": "RAINFED",
    "dryland": "RAINFED",
    "canal": "SURFACE",
    "flood": "SURFACE",
    "surface": "SURFACE",
    "furrow": "SURFACE",
    "drip": "DRIP",
    "micro irrigation": "DRIP",
    "sprinkler": "SPRINKLER"
}

BUDGET_KEYWORDS = {
    "low budget": "B1",
    "low cost": "B1",
    "poor": "B1",
    "b1": "B1",
    "medium budget": "B2",
    "moderate": "B2",
    "b2": "B2",
    "high budget": "B3",
    "commercial": "B3",
    "b3": "B3",
    "enterprise": "B4",
    "b4": "B4"
}

STOP_WORDS = {
    "give", "tell", "me", "show", "what", "is", "are", "the", "all", "a", "an",
    "disease", "diseases", "crop", "crops", "for", "of", "in", "on", "about",
    "please", "list", "names", "detail", "details", "to", "with", "and", "check",
    "this", "plan", "plans", "treatment", "treatments", "spray", "sprays", "how",
    "can", "i", "my", "our", "farm", "field", "medicine", "cure"
}

# Lazy Gemini model handle
_gemini_model = None

def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        key = os.getenv("GEMINI_API_KEY")
        if key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=key)
                model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")
                _gemini_model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"[NLP Extractor] Gemini initialization failed: {e}")
                _gemini_model = False
    return _gemini_model if _gemini_model else None

def extract_with_gemini(text: str) -> Optional[Dict[str, Any]]:
    """Uses Gemini 2.5 Flash to extract deep structured agronomic parameters from conversational text."""
    model = _get_gemini_model()
    if not model:
        return None

    system_prompt = (
        "You are an expert Agricultural NLP entity parser for Indian agronomy.\n"
        "Extract the following structured JSON from the user's agricultural query:\n"
        "{\n"
        '  "intent": "disease_diagnosis" | "treatment_plan" | "crop_recommendation" | "phenology_stages" | "water_pincode_outlook" | "spray_safety" | "list_diseases",\n'
        '  "crop_name": "Standard English crop name (e.g. Cotton, Wheat, Rice, Mustard) or null",\n'
        '  "symptoms": "Specific disease name, pest, or observed symptoms (e.g. leaf blight, yellow rust, stem rot) or empty string",\n'
        '  "stage": "Growth stage (e.g. flowering, vegetative) or disease stage (e.g. initial spots, severe) or null",\n'
        '  "pincode": "6-digit Indian PIN code or null",\n'
        '  "soil_class": 1 (clay) | 2 (black) | 3 (loam) | 4 (sandy loam) | 5 (sandy) | 6 (red) | 7 (alluvial) | 8 (laterite) or null,\n'
        '  "season": "KHARIF" | "RABI" | "ZAID" | "LONGTERM" or null,\n'
        '  "water_method": "RAINFED" | "SURFACE" | "DRIP" | "SPRINKLER" or null,\n'
        '  "budget_bucket": "B1" | "B2" | "B3" | "B4" or null,\n'
        '  "previous_crop": "Name of previous crop for rotation or null",\n'
        '  "weather_observation": "rainy, humid, hot, windy, calm or null"\n'
        "}\n\n"
        f"Query: \"{text}\"\n"
        "Respond ONLY with a single valid JSON block without markdown formatting."
    )

    try:
        response = model.generate_content(system_prompt)
        raw_text = response.text.strip()
        # Clean possible markdown fence
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```(?:json)?", "", raw_text)
            raw_text = re.sub(r"```$", "", raw_text)
            raw_text = raw_text.strip()
            
        data = json.loads(raw_text)
        return data
    except Exception as e:
        print(f"[NLP Extractor] Gemini LLM parse exception: {e}")
        return None

def extract_entities_from_text(text: str) -> Dict[str, Any]:
    """
    Hybrid NLP Agricultural Entity & Intent Extractor.
    Combines LLM parsing (Gemini) with deterministic ontology matching.
    """
    text_clean = text.lower().strip()
    graph = get_embedded_graph()

    # 1. Attempt LLM structured parsing first
    llm_extracted = extract_with_gemini(text)
    if llm_extracted and isinstance(llm_extracted, dict):
        crop = llm_extracted.get("crop_name")
        if crop:
            crop = graph.normalize_crop_name(crop)

        return {
            "intent": llm_extracted.get("intent", "treatment_plan"),
            "crop_name": crop,
            "symptoms": llm_extracted.get("symptoms", ""),
            "stage": llm_extracted.get("stage"),
            "pincode": llm_extracted.get("pincode"),
            "soil_class": llm_extracted.get("soil_class"),
            "season": llm_extracted.get("season", "KHARIF"),
            "water_method": llm_extracted.get("water_method", "RAINFED"),
            "budget_bucket": llm_extracted.get("budget_bucket", "B2"),
            "previous_crop": llm_extracted.get("previous_crop"),
            "weather_observation": llm_extracted.get("weather_observation"),
            "raw_text": text,
            "parsed_by": "llm"
        }

    # 2. Deterministic High-Precision Fallback Parser
    # Pincode (6-digit)
    pincode_match = re.search(r'\b[1-9][0-9]{5}\b', text)
    pincode = pincode_match.group(0) if pincode_match else None

    # Soil Class
    soil_class = None
    for s_kw, s_id in SOIL_KEYWORDS.items():
        if re.search(r'\b' + re.escape(s_kw) + r'\b', text_clean):
            soil_class = s_id
            break

    # Season
    season = None
    for se_kw, se_val in SEASON_KEYWORDS.items():
        if re.search(r'\b' + re.escape(se_kw) + r'\b', text_clean):
            season = se_val
            break

    # Water method
    water_method = None
    for w_kw, w_val in WATER_KEYWORDS.items():
        if re.search(r'\b' + re.escape(w_kw) + r'\b', text_clean):
            water_method = w_val
            break

    # Budget
    budget = None
    for b_kw, b_val in BUDGET_KEYWORDS.items():
        if re.search(r'\b' + re.escape(b_kw) + r'\b', text_clean):
            budget = b_val
            break

    # Intent
    intent = "general_advisory"
    if any(k in text_clean for k in ["all disease", "all diseases", "list disease", "list all", "what diseases", "diseases of", "diseases affecting"]):
        intent = "list_diseases"
    elif any(k in text_clean for k in ["water outlook", "groundwater", "reservoir", "district water", "pincode water", "monsoon forecast"]):
        intent = "water_pincode_outlook"
    elif any(k in text_clean for k in ["spray safe", "can i spray", "wind speed", "uv safety", "safe to spray", "safe spray window"]):
        intent = "spray_safety"
    elif any(k in text_clean for k in ["growth stage", "phenology", "stages of", "flowering stage", "vegetative stage", "timeline day", "how many days"]):
        intent = "phenology_stages"
    elif any(k in text_clean for k in ["recommend", "best crop", "suitability", "yield", "zone", "grow in", "suitable for", "what should i grow"]):
        intent = "crop_recommendation"
    elif any(k in text_clean for k in ["treatment", "cure", "spray", "medicine", "dosage", "chemical", "control", "remedy", "protocol", "how to treat"]):
        intent = "treatment_plan"
    elif any(k in text_clean for k in ["spots", "rot", "blight", "yellowing", "mildew", "rust", "curling", "wilt", "dieback", "pests"]):
        intent = "disease_diagnosis"

    # Crop extraction matching against all 164 crops and multilingual aliases
    identified_crop = None
    sorted_aliases = sorted(graph.crop_aliases.items(), key=lambda x: len(x[0]), reverse=True)
    for alias_key, canonical_name in sorted_aliases:
        pattern = r'\b' + re.escape(alias_key) + r'\b'
        if re.search(pattern, text_clean):
            identified_crop = canonical_name
            break

    # Symptoms / Disease Extraction
    symptoms = ""
    # Check against known disease names
    common_diseases = [
        "leaf blight", "bacterial blight", "early blight", "late blight",
        "powdery mildew", "downy mildew", "yellow rust", "stripe rust", "black rust", "brown rust", "rust",
        "anthracnose", "collar rot", "root rot", "stem rot", "fruit rot", "boll rot",
        "fusarium wilt", "wilt", "bacterial wilt", "leaf curl", "yellow mosaic virus",
        "blast", "sheath blight", "brown spot", "false smut", "smut", "tikka", "cercospora",
        "pink bollworm", "whitefly", "aphid", "thrips", "jassid", "stem borer", "fall armyworm"
    ]
    for d_kw in common_diseases:
        if re.search(r'\b' + re.escape(d_kw) + r'\b', text_clean):
            symptoms = d_kw
            break

    # If symptoms empty and not a list or recommendation intent, extract meaningful keywords
    if not symptoms and intent not in ("list_diseases", "crop_recommendation", "water_pincode_outlook"):
        tokens = [w.strip(" ,.!?") for w in text_clean.split()]
        meaningful_tokens = [w for w in tokens if w and w not in STOP_WORDS]
        if identified_crop:
            crop_words = set(identified_crop.lower().replace("(", " ").replace(")", " ").split())
            meaningful_tokens = [w for w in meaningful_tokens if w not in crop_words]
        if meaningful_tokens:
            symptoms = " ".join(meaningful_tokens)

    return {
        "intent": intent,
        "crop_name": identified_crop,
        "symptoms": symptoms,
        "stage": None,
        "pincode": pincode,
        "soil_class": soil_class,
        "season": season or "KHARIF",
        "water_method": water_method or "RAINFED",
        "budget_bucket": budget or "B2",
        "previous_crop": None,
        "weather_observation": None,
        "raw_text": text,
        "parsed_by": "deterministic"
    }
