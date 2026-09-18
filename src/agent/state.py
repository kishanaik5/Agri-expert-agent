from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    # Inputs
    query: str
    crop_name: Optional[str]
    symptoms: Optional[str]
    pincode: Optional[str]
    soil_class: Optional[int]
    temp_level: Optional[str]
    moisture: Optional[str]
    rain_status: Optional[str]

    # Graph Context & Entity State
    identified_crop: Optional[str]
    identified_diseases: List[Dict[str, Any]]
    growth_stages: List[Dict[str, Any]]
    zone_recommendations: List[Dict[str, Any]]
    weather_advisories: List[Dict[str, Any]]
    
    # Synthesized Output
    confidence_score: float
    diagnosis_summary: str
    treatment_protocols: List[Dict[str, Any]]
    preventive_actions: List[str]
    actionable_advisory: str
    error: Optional[str]
