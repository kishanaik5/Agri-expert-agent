import os
import json
import re
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nlp_extractor import extract_entities_from_text, _get_gemini_model
from src.agent.tools import (
    get_crop_profile, 
    search_disease_and_treatments, 
    get_zone_suitability_by_pincode,
    get_pincode_outlook,
    get_weather_advisories
)

def entity_extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extracts entities and intent from natural language query or direct state fields."""
    raw_query = state.get("query") or state.get("raw_text")
    
    if raw_query:
        nlp_res = extract_entities_from_text(raw_query)
        crop = state.get("crop_name") or nlp_res.get("crop_name")
        symptoms = state.get("symptoms") if state.get("symptoms") is not None else nlp_res.get("symptoms")
        stage = state.get("stage") or nlp_res.get("stage")
        pincode = state.get("pincode") or nlp_res.get("pincode")
        soil_class = state.get("soil_class") or nlp_res.get("soil_class")
        season = state.get("season") or nlp_res.get("season", "KHARIF")
        water_method = state.get("water_method") or nlp_res.get("water_method", "RAINFED")
        budget_bucket = state.get("budget_bucket") or nlp_res.get("budget_bucket", "B2")
        previous_crop = state.get("previous_crop") or nlp_res.get("previous_crop")
        intent = nlp_res.get("intent", "treatment_plan")
    else:
        crop = state.get("crop_name")
        symptoms = state.get("symptoms", "")
        stage = state.get("stage")
        pincode = state.get("pincode")
        soil_class = state.get("soil_class")
        season = state.get("season", "KHARIF")
        water_method = state.get("water_method", "RAINFED")
        budget_bucket = state.get("budget_bucket", "B2")
        previous_crop = state.get("previous_crop")
        intent = state.get("intent", "general_advisory")

    return {
        "identified_crop": crop,
        "symptoms": symptoms,
        "stage": stage,
        "pincode": pincode,
        "soil_class": soil_class,
        "season": season,
        "water_method": water_method,
        "budget_bucket": budget_bucket,
        "previous_crop": previous_crop,
        "intent": intent
    }

def graph_traversal_node(state: AgentState) -> Dict[str, Any]:
    """Queries deep multi-table agricultural knowledge bases."""
    crop = state.get("identified_crop")
    symptoms = state.get("symptoms", "")
    stage = state.get("stage")
    pincode = state.get("pincode")
    soil_class = state.get("soil_class")
    season = state.get("season", "KHARIF")
    water_method = state.get("water_method", "RAINFED")
    budget_bucket = state.get("budget_bucket", "B2")
    previous_crop = state.get("previous_crop")
    
    # 1. Disease & Multi-Stage Treatment Query
    diseases = search_disease_and_treatments(crop, symptoms, stage)
    
    # 2. Regional 6-Factor Suitability & Pincode Groundwater Outlook
    zone_recs = []
    groundwater_alert = None
    if pincode:
        zone_recs = get_zone_suitability_by_pincode(
            pincode=pincode,
            soil_class=soil_class,
            season=season,
            water_method=water_method,
            budget_bucket=budget_bucket,
            previous_crop=previous_crop,
            limit=10
        )
        groundwater_alert = get_pincode_outlook(pincode)
        
    # 3. Weather Advisories & Spray Safety
    weather_rules = get_weather_advisories(
        temp_level=state.get("temp_level"),
        moisture=state.get("moisture"),
        rain_status=state.get("rain_status"),
        wind_risk=state.get("wind_risk")
    )
    
    # 4. Phenological Growth Stages with Environmental Limits
    crop_profile = get_crop_profile(crop) if crop else None
    stages = crop_profile.get("stages", []) if crop_profile else []
    
    return {
        "identified_diseases": diseases,
        "growth_stages": stages,
        "zone_recommendations": zone_recs,
        "groundwater_alert": groundwater_alert,
        "weather_advisories": weather_rules
    }

def format_comprehensive_advisory_markdown(
    crop: str,
    symptoms: str,
    top_disease: Optional[Dict[str, Any]],
    active_stage: Optional[Dict[str, Any]],
    treatment_plan: List[Dict[str, Any]],
    preventative_measures: List[Dict[str, Any]],
    financial_impact: Optional[Dict[str, Any]],
    spray_safety: Optional[Dict[str, Any]],
    groundwater_alert: Optional[Dict[str, Any]],
    zone_recs: List[Dict[str, Any]],
    confidence: float
) -> str:
    """Formats an authoritative agronomic advisory grounded strictly in the knowledge graph."""
    crop_display = crop if crop and crop.lower() != "crop" else "Your Crop"
    lines = []
    
    dis_name = top_disease.get("disease", "Unknown Condition") if top_disease else "Agronomic Health Assessment"
    sci_name = top_disease.get("pathogen", "") if top_disease else ""
    if sci_name and sci_name.lower() in ("nan", "none"):
        sci_name = ""

    lines.append(f"## 🌱 Agri-Expert Copilot: {dis_name} Advisory for {crop_display}\n")
    
    # 1. Diagnosis & Pathological Stage
    lines.append("### 🔍 1. Diagnosis & Pathological Profile")
    lines.append(f"* **Target Crop:** **{crop_display}**")
    lines.append(f"* **Identified Condition:** **{dis_name}**" + (f" (*{sci_name}*)" if sci_name else ""))
    lines.append(f"* **Diagnostic Confidence:** `{int(confidence * 100)}%`")
    
    if active_stage:
        stg_num = active_stage.get("stage_number", 1)
        stg_name = active_stage.get("stage_name", "Initial Infection")
        spread = active_stage.get("spread_percentage", "0-5%")
        incubation = active_stage.get("incubation_period_days", "")
        speed = active_stage.get("spread_speed_class", "")
        lines.append(f"* **Current Infection Phase:** **Stage {stg_num} ({stg_name})** — Field Canopy Spread: `{spread}`")
        if speed or incubation:
            speed_str = f"Spread Class: `{speed}`" if speed else ""
            inc_str = f"Incubation: `{incubation} days`" if incubation else ""
            extra = " | ".join(filter(None, [speed_str, inc_str]))
            lines.append(f"* **Epidemiology:** {extra}")
        if active_stage.get("early_intervention_message"):
            lines.append(f"> ⚡ **Intervention Alert:** {active_stage.get('early_intervention_message')}")
    lines.append("")

    # 2. Step-by-Step Actionable Treatment Timeline
    lines.append("### 🧪 2. AI Early Intervention Protocol (Field Action Plan)")
    if treatment_plan:
        for idx, step in enumerate(treatment_plan, 1):
            day = step.get("day", f"Step {idx}")
            title = step.get("title", "Action Step")
            desc = step.get("desc", "")
            lines.append(f"#### **{day}: {title}**")
            lines.append(f"> {desc}\n")
    elif top_disease and top_disease.get("treatments"):
        for idx, trt in enumerate(top_disease["treatments"][:3], 1):
            lines.append(f"**Action {idx}:**")
            lines.append(f"> 🧪 {trt.strip()}\n")
    else:
        lines.append("* **Immediate Cultural Action:** Rogue out and bag the earliest diseased leaf tissues. Do not drop lesions into the furrow.")
        lines.append("* **Protective Chemical Spray:** Foliar application of Mancozeb 75% WP @ 2.0–2.5 g/L or Copper Oxychloride 50% WP @ 3.0 g/L covering both sides of canopy.")
    lines.append("")

    # 3. Financial & Yield Loss Assessment
    if financial_impact and (financial_impact.get("stage_revenue_loss_display") or financial_impact.get("max_revenue_loss_max_per_acre")):
        lines.append("### 💰 3. Financial Impact & Revenue Loss per Acre")
        rev_disp = financial_impact.get("stage_revenue_loss_display")
        max_rev = financial_impact.get("max_revenue_loss_max_per_acre")
        min_yld = financial_impact.get("min_yield_loss_pct")
        max_yld = financial_impact.get("max_yield_loss_pct")
        
        if rev_disp:
            lines.append(f"* **Current Stage Economic Loss:** **{rev_disp}**")
        if max_rev and max_rev > 0:
            lines.append(f"* **Unmanaged Terminal Revenue Risk:** **Up to ₹{max_rev:,.0f} per acre**")
        if max_yld and max_yld > 0:
            lines.append(f"* **Projected Yield Loss (if untreated):** `{min_yld:.0f}% – {max_yld:.0f}%`")
        lines.append("")

    # 4. Preventative Agronomic & Cultural Measures
    lines.append("### 🛡️ 4. Preventative & Integrated Pest Management (IPM)")
    if preventative_measures:
        for p in preventative_measures[:4]:
            p_title = p.get("title", "")
            p_desc = p.get("description", "")
            if p_title and p_desc:
                lines.append(f"* **{p_title}:** {p_desc}")
            elif p_desc:
                lines.append(f"* {p_desc}")
    else:
        lines.append("* **Certified Seed Quality:** Sowing certified disease-free, fungicide-treated seeds (e.g. Carbendazim / Thiram @ 2 g/kg seed).")
        lines.append("* **Canopy Aeration:** Maintain recommended spacing to improve airflow and minimize leaf wetness duration.")
        lines.append("* **Nutrient Balancing:** Avoid excess nitrogenous fertilization which produces soft, succulent tissues susceptible to fungal penetration.")
        lines.append("* **Crop Hygiene:** Deep summer ploughing and destruction of infected crop stubbles after harvest.")
    lines.append("")

    # 5. Operational Spray Window & Weather Watch
    if spray_safety:
        lines.append("### 🌦️ 5. Operational Spray Safety & Micro-Climate Context")
        lines.append(f"* **Safe Spraying Window:** `{spray_safety.get('recommended_window', '6:00 AM – 9:00 AM / 5:30 PM – 7:00 PM')}`")
        if spray_safety.get("advisory_message"):
            lines.append(f"* **Field Advisory:** {spray_safety.get('advisory_message')}")
        lines.append("")

    # 6. Groundwater & Regional Pincode Outlook
    if groundwater_alert:
        lines.append("### 🗺️ 6. Regional Groundwater & Season Outlook")
        dist = groundwater_alert.get("district", "Your District")
        pin = groundwater_alert.get("pincode", "")
        outlook = groundwater_alert.get("water_outlook_tag", "Normal")
        res = groundwater_alert.get("reservoir_level_current", "")
        grow = groundwater_alert.get("crops_to_grow", [])
        avoid = groundwater_alert.get("crops_to_avoid", [])
        
        lines.append(f"* **District & PIN:** **{dist} ({pin})** | Water Status: `{outlook}`")
        if res:
            lines.append(f"* **Reservoir / Groundwater Level:** {res}")
        if grow:
            lines.append(f"* **Recommended Water-Efficient Crops:** {', '.join(grow[:5])}")
        if avoid:
            lines.append(f"* **High-Water Crops to Avoid:** {', '.join(avoid[:4])}")
        lines.append("")

    lines.append("---")
    lines.append("💡 *Agronomic Guidance: Verify chemical applications with your local Krishi Vigyan Kendra (KVK). Always apply sprays with protective gear during calm weather.*")
    
    return "\n".join(lines)

def format_recommendation_markdown(
    pincode: str,
    zone_recs: List[Dict[str, Any]],
    groundwater_alert: Optional[Dict[str, Any]],
    season: str,
    soil_class: Optional[int]
) -> str:
    """Formats 6-factor regional suitability ranking with water outlook context."""
    lines = []
    lines.append(f"## 🗺️ Multi-Factor Crop Recommendation Engine")
    lines.append(f"**Evaluation for PIN Code: `{pincode}` | Season: `{season}`**\n")
    
    if groundwater_alert:
        dist = groundwater_alert.get("district", "")
        tag = groundwater_alert.get("water_outlook_tag", "Normal")
        lines.append(f"> 💧 **District Water Outlook ({dist}):** `{tag}` — {groundwater_alert.get('water_outlook_subtext', '')}\n")

    lines.append("### 🏆 Top Ranked Crops (Weighted Scoring: Zone, Season, Water, Soil, Budget, Rotation)\n")
    lines.append("| Rank | Crop | Match % | Zone Score | Season | Water Method | Soil Fit | Water Outlook |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |")
    
    for idx, r in enumerate(zone_recs[:8], 1):
        c_name = r.get("crop", "Crop")
        match = r.get("match_percentage", 0.0)
        z_sc = r.get("zone_score", 0.0)
        s_sc = r.get("season_score", 0.0)
        w_sc = r.get("water_score", 0.0)
        sl_sc = r.get("soil_score", 0.0)
        warning = r.get("water_outlook_warning") or "✅ Approved"
        warn_icon = "⚠️ Restricted" if "Risk" in warning or "High" in warning else "✅ High Fit"
        
        lines.append(f"| **#{idx}** | **{c_name}** | **`{match:.1f}%`** | {z_sc}/2 | {s_sc}/2 | {w_sc}/2 | {sl_sc}/2 | {warn_icon} |")
        
    lines.append("\n---\n")
    if groundwater_alert:
        if groundwater_alert.get("crops_to_grow"):
            lines.append(f"* **District Endorsed Species:** {', '.join(groundwater_alert.get('crops_to_grow', [])[:6])}")
        if groundwater_alert.get("crops_to_avoid"):
            lines.append(f"* **Species with Excessive Water Depletion Risk:** {', '.join(groundwater_alert.get('crops_to_avoid', [])[:5])}")

    return "\n".join(lines)

def format_phenology_markdown(crop: str, stages: List[Dict[str, Any]]) -> str:
    """Formats growth stages, day timelines, environmental conditions, and pests."""
    lines = []
    lines.append(f"## 🌾 Phenological Growth Stages & Crop Calendar: {crop}\n")
    lines.append(f"Below is the complete agronomic growth schedule for **{crop}**, with critical day milestones, environmental thresholds, and vulnerable pest/disease intervals:\n")
    
    for idx, s in enumerate(stages, 1):
        main = s.get("main_stage", "Phase")
        sub = s.get("sub_stage", "")
        start = s.get("start_day", 0)
        end = s.get("end_day", 0)
        pests = s.get("susceptible_pests", "")
        diseases = s.get("susceptible_diseases", "")
        env = s.get("env_conditions", {})
        
        lines.append(f"### {idx}. **{main}: {sub}** (`Day {start} – {end}`)")
        if env:
            temp = env.get("optimal_temp_c", "")
            hum = env.get("rel_humidity_pct", "")
            moist = env.get("soil_moisture_pct", "")
            irrig = env.get("irrigation_mm", "")
            env_parts = []
            if temp: env_parts.append(f"Optimal Temp: `{temp}°C`")
            if hum: env_parts.append(f"Humidity: `{hum}%`")
            if moist: env_parts.append(f"Soil Moisture: `{moist}`")
            if irrig: env_parts.append(f"Irrigation: `{irrig} mm`")
            if env_parts:
                lines.append(f"* **Environmental Conditions:** {' | '.join(env_parts)}")
                
        if pests:
            lines.append(f"* **Vulnerable Pests:** {pests}")
            if s.get("pest_management"):
                lines.append(f"> 🐛 *Pest Management:* {s.get('pest_management')[:200]}...")
        if diseases:
            lines.append(f"* **Susceptible Diseases:** {diseases}")
            if s.get("disease_management"):
                lines.append(f"> 🦠 *Disease Management:* {s.get('disease_management')[:200]}...")
        lines.append("")
        
    return "\n".join(lines)

def advisory_synthesizer_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes structured multi-table data into rich advisory and typed payloads."""
    crop = state.get("identified_crop") or "Crop"
    symptoms = state.get("symptoms", "")
    intent = state.get("intent", "treatment_plan")
    diseases = state.get("identified_diseases", [])
    stages = state.get("growth_stages", [])
    weather_adv = state.get("weather_advisories", [])
    zone_recs = state.get("zone_recommendations", [])
    groundwater_alert = state.get("groundwater_alert")
    pincode = state.get("pincode")

    # Pick top disease and active stage
    top_disease = diseases[0] if diseases else None
    active_stage = None
    treatment_plan = []
    preventative_measures = []
    financial_impact = None
    confidence = 0.92 if (top_disease and crop.lower() != "crop") else (0.80 if top_disease else 0.50)

    if top_disease:
        active_stage = top_disease.get("active_stage")
        if not active_stage and top_disease.get("stages"):
            active_stage = top_disease["stages"][0]

        if active_stage:
            treatment_plan = active_stage.get("treatment_steps", [])
            preventative_measures = active_stage.get("preventative_measures", [])
            
            financial_impact = {
                "stage_revenue_loss_display": active_stage.get("stage_revenue_loss_range_display"),
                "max_revenue_loss_max_per_acre": active_stage.get("max_revenue_loss_max_per_acre"),
                "min_yield_loss_pct": active_stage.get("min_yield_loss_pct"),
                "max_yield_loss_pct": active_stage.get("max_yield_loss_pct"),
                "net_returns_mid": None
            }

    # Spray safety
    spray_safety = {
        "status": "Safe Window Active",
        "recommended_window": "6:00 AM – 9:00 AM / 5:30 PM – 7:00 PM",
        "wind_risk": "Calm (< 8 km/h)",
        "fungal_risk": "Moderate",
        "advisory_message": "Spray early morning or late afternoon when wind speeds are low and UV radiation is minimized to avoid chemical burn."
    }
    if weather_adv:
        for w in weather_adv:
            if w.get("advisory_type") == "spraying":
                spray_safety["advisory_message"] = w.get("message_en", spray_safety["advisory_message"])
                spray_safety["wind_risk"] = w.get("wind_risk", spray_safety["wind_risk"])
            elif w.get("advisory_type") == "fungal_risk":
                spray_safety["fungal_risk"] = w.get("status", "High Fungal Risk")

    # Generate Output Based on Intent
    if intent == "crop_recommendation" and zone_recs:
        neat_markdown = format_recommendation_markdown(
            pincode=pincode or "Selected Region",
            zone_recs=zone_recs,
            groundwater_alert=groundwater_alert,
            season=state.get("season", "KHARIF"),
            soil_class=state.get("soil_class")
        )
        diag_summary = f"Calculated 6-factor suitability ranking for {len(zone_recs)} regional crops in PIN {pincode}."
        confidence = 0.96

    elif intent == "phenology_stages" and stages:
        neat_markdown = format_phenology_markdown(crop=crop, stages=stages)
        diag_summary = f"Loaded {len(stages)} phenological growth stages, day ranges, and pest risks for {crop}."
        confidence = 0.95

    elif intent == "water_pincode_outlook" and groundwater_alert:
        dist = groundwater_alert.get("district", "District")
        pin = groundwater_alert.get("pincode", pincode)
        tag = groundwater_alert.get("water_outlook_tag", "Normal")
        res = groundwater_alert.get("reservoir_level_current", "N/A")
        mon = groundwater_alert.get("monsoon_forecast_vs_last_year", "Normal")
        grow = groundwater_alert.get("crops_to_grow", [])
        avoid = groundwater_alert.get("crops_to_avoid", [])
        
        lines = [
            f"## 💧 Groundwater & Seasonal Water Outlook: {dist} ({pin})\n",
            f"* **Water Availability Status:** `{tag}`",
            f"* **Current Reservoir Level:** {res}",
            f"* **Monsoon Projection:** {mon}",
            f"* **Groundwater Risk Analysis:** {groundwater_alert.get('water_risk', 'Normal recharge')}\n",
            "### 🌾 Recommended Water-Efficient Crops:",
            ", ".join(grow) if grow else "Standard local crops",
            "\n### 🚫 High-Water Crops to Avoid or Restrict:",
            ", ".join(avoid) if avoid else "None restricted",
            f"\n> 💡 *Note: {groundwater_alert.get('what_this_means_details', '')}*"
        ]
        neat_markdown = "\n".join(lines)
        diag_summary = f"Retrieved seasonal groundwater reserve analysis for PIN {pin} ({dist})."
        confidence = 0.98

    else:
        # Treatment plan or diagnosis
        preventions_flat = [p.get("description", p.get("title", "")) for p in preventative_measures if p]
        if not preventions_flat:
            preventions_flat = [
                "Isolate and rogue out severely infected plants before pathogens sporulate.",
                "Avoid overhead sprinkler irrigation which extends leaf moisture periods.",
                "Maintain balanced potassium and zinc to enhance natural plant defense mechanisms.",
                "Practice legume crop rotation to disrupt fungal and insect pupation cycles."
            ]

        neat_markdown = format_comprehensive_advisory_markdown(
            crop=crop,
            symptoms=symptoms,
            top_disease=top_disease,
            active_stage=active_stage,
            treatment_plan=treatment_plan,
            preventative_measures=preventative_measures,
            financial_impact=financial_impact,
            spray_safety=spray_safety,
            groundwater_alert=groundwater_alert,
            zone_recs=zone_recs,
            confidence=confidence
        )
        dis_title = top_disease.get('disease') if top_disease else 'General Field Assessment'
        diag_summary = f"Identified condition: **{dis_title}** under {crop}."

    # Build treatment protocols list for GraphQL
    protocols = []
    if treatment_plan:
        for t in treatment_plan:
            protocols.append({
                "disease": top_disease.get("disease", crop) if top_disease else crop,
                "protocol": f"{t.get('day', '')} ({t.get('title', '')}): {t.get('desc', '')}",
                "type": "Stage Intervention Step"
            })
    elif top_disease and top_disease.get("treatments"):
        for trt in top_disease["treatments"][:3]:
            protocols.append({
                "disease": top_disease.get("disease", crop),
                "protocol": trt,
                "type": "Protective Treatment"
            })

    # Convert preventative_measures to flat list
    preventions = [p.get("title", "") + ": " + p.get("description", "") for p in preventative_measures if p.get("title")]
    if not preventions:
        preventions = [
            "Use certified disease-free treated seed.",
            "Maintain optimal field drainage and canopy spacing.",
            "Avoid excessive nitrogen fertilization."
        ]

    return {
        "confidence_score": confidence,
        "diagnosis_summary": diag_summary,
        "treatment_protocols": protocols,
        "treatment_plan": treatment_plan,
        "financial_impact": financial_impact,
        "spray_safety": spray_safety,
        "groundwater_alert": groundwater_alert,
        "preventive_actions": preventions,
        "actionable_advisory": neat_markdown,
        "identified_crop": crop,
        "symptoms": symptoms,
        "active_disease": top_disease,
        "active_stage_info": active_stage
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
