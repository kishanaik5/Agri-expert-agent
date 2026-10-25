from typing import List, Dict, Any, Optional
from src.graph.embedded_graph import get_embedded_graph

def get_crop_profile(crop_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves deep crop profile with phenological growth stages, pest/disease risks, and environmental thresholds."""
    return get_embedded_graph().get_crop_profile(crop_name)

def search_disease_and_treatments(
    crop_name: Optional[str], 
    symptom_or_disease: str,
    stage_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Queries multi-stage disease profiles, Day 1/2/5 treatment plans, and revenue loss curves."""
    return get_embedded_graph().search_diseases(crop_name, symptom_or_disease, stage_name)

def get_pincode_outlook(pincode: str) -> Optional[Dict[str, Any]]:
    """Fetches groundwater reserve status, water outlook tag, and crops to grow/avoid from season advisor."""
    return get_embedded_graph().get_pincode_outlook(pincode)

def get_zone_suitability_by_pincode(
    pincode: str, 
    soil_class: Optional[int] = None,
    season: Optional[str] = None,
    water_method: Optional[str] = None,
    budget_bucket: Optional[str] = None,
    previous_crop: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Calculates 6-factor weighted regional crop recommendations (Zone, Season, Water, Soil, Budget, Rotation)."""
    return get_embedded_graph().calculate_6factor_recommendations(
        pincode=pincode,
        season=season,
        soil_class=soil_class,
        water_method=water_method,
        budget_bucket=budget_bucket,
        previous_crop=previous_crop,
        limit=limit
    )

def get_weather_advisories(
    temp_level: Optional[str] = None, 
    moisture: Optional[str] = None, 
    rain_status: Optional[str] = None,
    wind_risk: Optional[str] = None,
    advisory_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Queries operational weather rules for spraying, fungal risk, field work, and irrigation."""
    return get_embedded_graph().get_weather_advisories(
        temp=temp_level,
        moist=moisture,
        rain=rain_status,
        wind=wind_risk,
        advisory_type=advisory_type
    )
