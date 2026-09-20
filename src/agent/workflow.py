from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nlp_extractor import extract_entities_from_text
from src.agent.tools import (
    get_crop_profile, 
    search_disease_and_treatments, 
    get_zone_suitability_by_pincode,
    get_weather_advisories
)

def entity_extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extracts entities (crop, symptoms, pincode, weather, intent) from natural language query or direct fields."""
    raw_query = state.get("query") or state.get("raw_text")
    
    if raw_query and (not state.get("crop_name") or not state.get("symptoms")):
        nlp_res = extract_entities_from_text(raw_query)
        crop = state.get("crop_name") or nlp_res.get("crop_name")
        symptoms = state.get("symptoms") or nlp_res.get("symptoms")
        pincode = state.get("pincode") or nlp_res.get("pincode")
        soil_class = state.get("soil_class") or nlp_res.get("soil_class")
    else:
        crop = state.get("crop_name")
        symptoms = state.get("symptoms") or state.get("query", "")
        pincode = state.get("pincode")
        soil_class = state.get("soil_class")

    return {
        "identified_crop": crop,
        "symptoms": symptoms,
        "pincode": pincode,
        "soil_class": soil_class
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

def format_conversational_llm_response(
    crop: str,
    symptoms: str,
    disease_name: str,
    pathogen: str,
    confidence: float,
    treatments: List[Dict[str, Any]],
    preventions: List[str],
    weather_adv: List[Dict[str, Any]],
    zone_recs: List[Dict[str, Any]]
) -> str:
    """Formats a polished, neat LLM-style advisory response."""
    lines = []
    lines.append(f"🌱 **Agri-Expert Copilot Advisory**\n")
    lines.append(f"Hello! Here is the tailored diagnostic analysis and actionable treatment plan for your **{crop}** crop:\n")
    lines.append("---\n")
    
    # 1. Diagnosis
    lines.append("### 🔍 **Diagnosis & Pathology**")
    if disease_name != "General Health Assessment":
        lines.append(f"* **Likely Condition:** **{disease_name}**")
        if pathogen:
            lines.append(f"* **Causal Organism / Pathogen:** *{pathogen}*")
        lines.append(f"* **Diagnostic Confidence:** `{int(confidence * 100)}%`")
    else:
        lines.append(f"* **Assessment:** Routine agronomic monitoring. No severe pathogen outbreak identified for *'{symptoms}'*.")
    lines.append("")
    
    # 2. Treatment Protocols
    lines.append("### 💊 **Recommended Treatment Plan & Formulations**")
    if treatments:
        for idx, t in enumerate(treatments, 1):
            protocol_text = t.get("protocol", "").strip()
            lines.append(f"**Step {idx}: Application for {t.get('disease')}**")
            lines.append(f"> 🧪 *Protocol:* {protocol_text}\n")
    else:
        lines.append("* Apply balanced micronutrients (Zinc, Boron) and maintain regular irrigation intervals.")
        lines.append("* If localized spotting intensifies, spray broad-spectrum preventive fungicide (e.g., Mancozeb @ 2 g/L).")
    lines.append("")

    # 3. Preventive Cultural Management
    lines.append("### 🛡️ **Preventative & Cultural Practices**")
    for p in preventions:
        lines.append(f"* {p}")
    lines.append("")

    # 4. Weather & Field Advice
    if weather_adv:
        lines.append("### 🌦️ **Operational & Weather Considerations**")
        for w in weather_adv[:2]:
            lines.append(f"* **{w.get('advisory_type', 'Operational').title()}:** {w.get('advisory')}")
        lines.append("")

    # 5. Alternative Regional Crops
    if zone_recs:
        lines.append("### 🗺️ **High-Suitability Regional Crops**")
        for z in zone_recs[:3]:
            lines.append(f"* **{z.get('crop')}** — Agro-Climatic Match Score: `{z.get('combined_score', 0):.2f}`")
        lines.append("")

    lines.append("---")
    lines.append("💡 *Tip: For best absorption, spray during early morning or late afternoon when wind speeds are low and temperatures are moderate.*")
    
    return "\n".join(lines)

def advisory_synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes structured data and clean conversational LLM response."""
    crop = state.get("identified_crop") or "Crop"
    symptoms = state.get("symptoms") or "general check"
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
            
        preventions.append("Isolate and rogue out severely infected plant parts.")
        preventions.append("Avoid overhead sprinkler irrigation to minimize canopy wetness.")
        preventions.append("Maintain optimal plant spacing for healthy airflow and sunlight penetration.")
        preventions.append("Destroy crop residue post-harvest to break pathogen overwintering cycles.")
        
        confidence = 0.92 if crop and treat_list else 0.75
    else:
        dis_name = "General Health Assessment"
        pathogen = ""
        diag_summary = f"No severe pathogen match detected for '{symptoms}' under {crop}. Routine agronomic monitoring recommended."
        confidence = 0.50
        preventions.append("Maintain balanced NPK fertilizer schedule.")
        preventions.append("Inspect soil moisture levels before initiating irrigation.")
        preventions.append("Regularly check underleaf surfaces for early pest colonizers.")

    # Generate neat LLM-style markdown advisory
    neat_llm_response = format_conversational_llm_response(
        crop=crop,
        symptoms=symptoms,
        disease_name=dis_name,
        pathogen=pathogen,
        confidence=confidence,
        treatments=treatments,
        preventions=preventions,
        weather_adv=weather_adv,
        zone_recs=zone_recs
    )

    return {
        "confidence_score": confidence,
        "diagnosis_summary": diag_summary,
        "treatment_protocols": treatments,
        "preventive_actions": preventions,
        "actionable_advisory": neat_llm_response
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
