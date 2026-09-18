from typing import Dict, Any
from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.tools import (
    get_crop_profile, 
    search_disease_and_treatments, 
    get_zone_suitability_by_pincode,
    get_weather_advisories
)

def entity_extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extracts entities (crop, symptoms, pincode, weather) from query or direct fields."""
    crop = state.get("crop_name")
    symptoms = state.get("symptoms") or state.get("query", "")
    pincode = state.get("pincode")
    
    # Simple fallback parser if raw query provided
    query = state.get("query", "")
    if not crop and query:
        words = [w.strip(" ,.!?") for w in query.split()]
        for w in words:
            if w.title() in ["Wheat", "Rice", "Cotton", "Mustard", "Soybean", "Maize", "Groundnut", "Chickpea", "Potato", "Tomato", "Sugarcane", "Bajra"]:
                crop = w.title()
                break
                
    return {
        "identified_crop": crop,
        "symptoms": symptoms,
        "pincode": pincode
    }

def graph_traversal_node(state: AgentState) -> Dict[str, Any]:
    """Queries Neo4j Knowledge Graph for crop profile, diseases, treatments, stages, and suitability."""
    crop = state.get("identified_crop")
    symptoms = state.get("symptoms", "")
    pincode = state.get("pincode")
    soil_class = state.get("soil_class")
    
    crop_profile = get_crop_profile(crop) if crop else None
    diseases = search_disease_and_treatments(crop, symptoms)
    
    zone_recs = []
    if pincode:
        zone_recs = get_zone_suitability_by_pincode(pincode, soil_class)
        
    weather_rules = get_weather_advisories(
        temp_level=state.get("temp_level"),
        moisture=state.get("moisture"),
        rain_status=state.get("rain_status")
    )
    
    stages = crop_profile.get("stages", []) if crop_profile else []
    
    return {
        "identified_diseases": diseases,
        "growth_stages": stages,
        "zone_recommendations": zone_recs,
        "weather_advisories": weather_rules
    }

def advisory_synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes deterministic structured advisory based on knowledge graph context."""
    crop = state.get("identified_crop") or "Crop"
    diseases = state.get("identified_diseases", [])
    stages = state.get("growth_stages", [])
    weather_adv = state.get("weather_advisories", [])
    zone_recs = state.get("zone_recommendations", [])
    
    treatments = []
    preventions = []
    
    if diseases:
        top_match = diseases[0]
        dis_name = top_match.get("disease", "Unknown Issue")
        pathogen = top_match.get("pathogen", "Biotic Stress")
        treat_list = top_match.get("treatments", [])
        
        diag_summary = f"Detected likely condition: **{dis_name}**"
        if pathogen:
            diag_summary += f" caused by `{pathogen}`."
            
        for t in treat_list:
            treatments.append({
                "disease": dis_name,
                "protocol": t,
                "type": "Chemical / Biological Spray"
            })
            
        preventions.append("Isolate affected plants and remove diseased foliage.")
        preventions.append("Avoid overhead irrigation to minimize leaf wetness.")
        preventions.append("Maintain recommended plant spacing for optimal aeration.")
        
        confidence = 0.92 if crop and treat_list else 0.75
    else:
        diag_summary = f"No specific pathogen match for '{state.get('symptoms', '')}' under {crop}. Routine monitoring recommended."
        confidence = 0.50
        preventions.append("Ensure balanced NPK fertilization.")
        preventions.append("Check soil moisture levels before next irrigation cycle.")

    # Weather synthesis
    weather_notes = []
    for w in weather_adv:
        weather_notes.append(f"- [{w.get('advisory_type', 'General').upper()}]: {w.get('advisory')}")
        
    actionable = f"### Agronomic Advisory for {crop}\n\n"
    actionable += f"**Diagnosis:** {diag_summary}\n\n"
    
    if treatments:
        actionable += "#### Recommended Treatments:\n"
        for t in treatments:
            actionable += f"* **{t['disease']}**: {t['protocol']}\n"
        actionable += "\n"
        
    if preventions:
        actionable += "#### Preventive Management:\n"
        for p in preventions:
            actionable += f"* {p}\n"
        actionable += "\n"
        
    if weather_notes:
        actionable += "#### Weather & Field Operational Advice:\n" + "\n".join(weather_notes) + "\n\n"
        
    if zone_recs:
        actionable += "#### Top Recommended Alternative Crops for Region:\n"
        for z in zone_recs[:3]:
            actionable += f"* **{z['crop']}** (Suitability: {z.get('combined_score', 0):.2f})\n"

    return {
        "confidence_score": confidence,
        "diagnosis_summary": diag_summary,
        "treatment_protocols": treatments,
        "preventive_actions": preventions,
        "actionable_advisory": actionable.strip()
    }

def create_advisory_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("extract_entities", entity_extractor_node)
    workflow.add_node("traverse_graph", graph_traversal_node)
    workflow.add_node("synthesize_advisory", advisory_synthesizer_node)
    
    workflow.set_entry_point("extract_entities")
    workflow.add_edge("extract_entities", "traverse_graph")
    workflow.add_edge("traverse_graph", "synthesize_advisory")
    workflow.add_edge("synthesize_advisory", END)
    
    return workflow.compile()

# Global compiled instance
advisory_agent = create_advisory_graph()

def run_advisory_agent(input_state: Dict[str, Any]) -> Dict[str, Any]:
    return advisory_agent.invoke(input_state)
