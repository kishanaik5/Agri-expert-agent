from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    # Inputs & NLP parsed state
    query: str
    raw_text: Optional[str]
    crop_name: Optional[str]
    symptoms: Optional[str]
    stage: Optional[str]
    pincode: Optional[str]
    soil_class: Optional[int]
    season: Optional[str]
    water_method: Optional[str]
    budget_bucket: Optional[str]
    previous_crop: Optional[str]
    temp_level: Optional[str]
    moisture: Optional[str]
    rain_status: Optional[str]
    wind_risk: Optional[str]
    intent: Optional[str]

    # Graph Context & Entity State
    identified_crop: Optional[str]
    identified_diseases: List[Dict[str, Any]]
    active_disease: Optional[Dict[str, Any]]
    active_stage_info: Optional[Dict[str, Any]]
    growth_stages: List[Dict[str, Any]]
    zone_recommendations: List[Dict[str, Any]]
    weather_advisories: List[Dict[str, Any]]
    groundwater_alert: Optional[Dict[str, Any]]
    
    # Synthesized Output
    confidence_score: float
    diagnosis_summary: str
    treatment_protocols: List[Dict[str, Any]]
    treatment_plan: List[Dict[str, Any]]
    financial_impact: Optional[Dict[str, Any]]
    spray_safety: Optional[Dict[str, Any]]
    preventive_actions: List[str]
    actionable_advisory: str
    error: Optional[str]
