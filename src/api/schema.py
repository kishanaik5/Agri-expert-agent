import strawberry
from typing import List, Optional, Dict, Any
from src.api.types import (
    CropType,
    CropStageType,
    DiseaseType,
    ZoneRecommendationType,
    AdvisoryResultType,
    TreatmentProtocolType,
    TreatmentStepType,
    DiseaseStageDetailType,
    FinancialImpactType,
    SpraySafetyType,
    GroundwaterOutlookType,
    TaskStatusType,
    TaskSubmissionResponseType,
    CopilotChatResponseType
)
from src.graph.client import get_graph_client
from src.graph.embedded_graph import get_embedded_graph
from src.agent.tools import (
    get_crop_profile,
    search_disease_and_treatments,
    get_zone_suitability_by_pincode,
    get_pincode_outlook
)
from src.agent.nlp_extractor import extract_entities_from_text
from src.agent.workflow import run_advisory_agent
from src.queue.broker import publish_diagnostic_task
from src.queue.worker import get_task_result

def _to_treatment_steps(steps_raw: Optional[List[Dict[str, Any]]]) -> Optional[List[TreatmentStepType]]:
    if not steps_raw:
        return None
    return [
        TreatmentStepType(
            day=str(s.get("day", "")),
            step=str(s.get("step", "")),
            title=str(s.get("title", "")),
            desc=str(s.get("desc", ""))
        )
        for s in steps_raw
    ]

def _to_stage_details(stages_raw: Optional[List[Dict[str, Any]]]) -> Optional[List[DiseaseStageDetailType]]:
    if not stages_raw:
        return None
    return [
        DiseaseStageDetailType(
            stage_number=s.get("stage_number", 1),
            stage_name=s.get("stage_name", ""),
            early_intervention_message=s.get("early_intervention_message"),
            spread_percentage=s.get("spread_percentage"),
            eta_for_next_stage_in_days=s.get("eta_for_next_stage_in_days"),
            stage_timeline_day=s.get("stage_timeline_day"),
            stage_revenue_loss_min=s.get("stage_revenue_loss_min"),
            stage_revenue_loss_max=s.get("stage_revenue_loss_max"),
            revenue_loss_range_display=s.get("stage_revenue_loss_range_display"),
            max_revenue_loss_max_per_acre=s.get("max_revenue_loss_max_per_acre"),
            min_yield_loss_pct=s.get("min_yield_loss_pct"),
            max_yield_loss_pct=s.get("max_yield_loss_pct"),
            spread_speed_class=s.get("spread_speed_class"),
            incubation_period_days=str(s.get("incubation_period_days", "")),
            disease_cycle_days=str(s.get("disease_cycle_days", "")),
            days_to_severe=str(s.get("days_to_severe", "")),
            treatment_steps=_to_treatment_steps(s.get("treatment_steps")),
            recoverability=s.get("recoverability"),
            action=s.get("action"),
            header_alert=s.get("header_alert")
        )
        for s in stages_raw
    ]

def _to_financial_impact(fi_raw: Optional[Dict[str, Any]]) -> Optional[FinancialImpactType]:
    if not fi_raw:
        return None
    return FinancialImpactType(
        stage_revenue_loss_display=fi_raw.get("stage_revenue_loss_display"),
        max_revenue_loss_max_per_acre=fi_raw.get("max_revenue_loss_max_per_acre"),
        min_yield_loss_pct=fi_raw.get("min_yield_loss_pct"),
        max_yield_loss_pct=fi_raw.get("max_yield_loss_pct"),
        net_returns_mid=fi_raw.get("net_returns_mid")
    )

def _to_spray_safety(ss_raw: Optional[Dict[str, Any]]) -> Optional[SpraySafetyType]:
    if not ss_raw:
        return None
    return SpraySafetyType(
        status=ss_raw.get("status", "Safe Window Active"),
        recommended_window=ss_raw.get("recommended_window"),
        wind_risk=ss_raw.get("wind_risk"),
        fungal_risk=ss_raw.get("fungal_risk"),
        advisory_message=ss_raw.get("advisory_message")
    )

def _to_groundwater_alert(gw_raw: Optional[Dict[str, Any]]) -> Optional[GroundwaterOutlookType]:
    if not gw_raw:
        return None
    return GroundwaterOutlookType(
        pincode=str(gw_raw.get("pincode", "")),
        district=str(gw_raw.get("district", "")),
        water_outlook_tag=str(gw_raw.get("water_outlook_tag", "Normal")),
        reservoir_level_current=gw_raw.get("reservoir_level_current"),
        monsoon_forecast=gw_raw.get("monsoon_forecast_vs_last_year"),
        water_risk=gw_raw.get("water_risk"),
        crops_to_grow=gw_raw.get("crops_to_grow", []),
        crops_to_avoid=gw_raw.get("crops_to_avoid", []),
        what_this_means=gw_raw.get("what_this_means_details")
    )

@strawberry.type
class Query:
    @strawberry.field
    def ask_copilot(self, query: str) -> CopilotChatResponseType:
        """
        Conversational NLP interaction endpoint.
        Example: 'give treatment plan for cotton crop and leaf blight disease'
        """
        result = run_advisory_agent({"query": query})
        
        treatment_list = [
            TreatmentProtocolType(
                disease=tp.get("disease", ""),
                protocol=tp.get("protocol", ""),
                type=tp.get("type", "Treatment Plan")
            )
            for tp in result.get("treatment_protocols", [])
        ]
        
        adv = result.get("actionable_advisory", "")
        
        return CopilotChatResponseType(
            intent=result.get("intent", "treatment_plan"),
            crop=result.get("identified_crop"),
            symptoms=result.get("symptoms"),
            diagnosis=result.get("diagnosis_summary", ""),
            confidence_score=result.get("confidence_score", 0.0),
            treatments=treatment_list,
            preventive_actions=result.get("preventive_actions", []),
            advisory=adv,
            llm_response=adv,
            stages=_to_stage_details(result.get("active_disease", {}).get("stages")) if result.get("active_disease") else None,
            treatment_plan=_to_treatment_steps(result.get("treatment_plan")),
            financial_impact=_to_financial_impact(result.get("financial_impact")),
            spray_safety=_to_spray_safety(result.get("spray_safety")),
            groundwater_alert=_to_groundwater_alert(result.get("groundwater_alert"))
        )

    @strawberry.field
    def chat(self, message: str) -> CopilotChatResponseType:
        """Alias for askCopilot."""
        return self.ask_copilot(query=message)

    @strawberry.field
    def crops(self, limit: Optional[int] = None, search: Optional[str] = None) -> List[CropType]:
        """List master crops available in the knowledge graph."""
        records = get_embedded_graph().get_crops(limit=limit, search=search)
        return [
            CropType(
                name=r["name"],
                name_hin=r.get("name_hin"),
                name_kan=r.get("name_kan"),
                name_mar=r.get("name_mar"),
                name_tel=r.get("name_tel"),
                name_tam=r.get("name_tam"),
                category=r.get("category")
            )
            for r in records
        ]

    @strawberry.field
    def crop_details(self, name: str) -> Optional[CropType]:
        """Fetch deep profile of a crop including its phenological growth stages, pests, and environmental limits."""
        profile = get_crop_profile(name)
        if not profile:
            return None
        
        stages = [
            CropStageType(
                main_stage=s.get("main_stage", ""),
                sub_stage=s.get("sub_stage", ""),
                start_day=s.get("start_day", 0),
                end_day=s.get("end_day", 0),
                susceptible_pests=s.get("susceptible_pests"),
                pest_risk_factors=s.get("pest_risk_factors"),
                pest_management=s.get("pest_management"),
                susceptible_diseases=s.get("susceptible_diseases"),
                disease_risk_factors=s.get("disease_risk_factors"),
                disease_management=s.get("disease_management"),
                optimal_temp_c=str(s.get("env_conditions", {}).get("optimal_temp_c", "")) if s.get("env_conditions") else None,
                rel_humidity_pct=str(s.get("env_conditions", {}).get("rel_humidity_pct", "")) if s.get("env_conditions") else None,
                soil_moisture_pct=str(s.get("env_conditions", {}).get("soil_moisture_pct", "")) if s.get("env_conditions") else None,
                uv_index=str(s.get("env_conditions", {}).get("uv_index", "")) if s.get("env_conditions") else None,
                irrigation_mm=str(s.get("env_conditions", {}).get("irrigation_mm", "")) if s.get("env_conditions") else None
            )
            for s in profile.get("stages", [])
        ]
        return CropType(
            name=profile["name"],
            name_hin=profile.get("name_hin"),
            name_kan=profile.get("name_kan"),
            name_mar=profile.get("name_mar"),
            name_tel=profile.get("name_tel"),
            name_tam=profile.get("name_tam"),
            category=profile.get("category"),
            stages=stages
        )

    @strawberry.field
    def diseases(
        self, 
        crop_name: Optional[str] = None, 
        symptom: Optional[str] = None,
        crop: Optional[str] = None,
        symptoms: Optional[str] = None,
        stage: Optional[str] = None
    ) -> List[DiseaseType]:
        """Search diseases, pathogens, multi-stage progression, and treatments for a crop or symptom."""
        target_crop = crop or crop_name
        target_symptom = symptoms or symptom or ""
        results = search_disease_and_treatments(target_crop, target_symptom, stage)
        
        out = []
        for r in results:
            stages_obj = _to_stage_details(r.get("stages"))
            active_stg = None
            if r.get("active_stage"):
                active_list = _to_stage_details([r["active_stage"]])
                if active_list:
                    active_stg = active_list[0]
                    
            out.append(DiseaseType(
                crop=r["crop"],
                disease=r["disease"],
                pathogen=r.get("pathogen"),
                treatments=r.get("treatments", []),
                stages=stages_obj,
                active_stage=active_stg
            ))
        return out

    @strawberry.field
    def disease(
        self, 
        crop_name: Optional[str] = None, 
        symptom: Optional[str] = None,
        crop: Optional[str] = None,
        symptoms: Optional[str] = None,
        stage: Optional[str] = None
    ) -> List[DiseaseType]:
        """Alias for diseases query."""
        return self.diseases(crop_name=crop_name, symptom=symptom, crop=crop, symptoms=symptoms, stage=stage)

    @strawberry.field
    def zone_recommendations(
        self, 
        pincode: str, 
        soil_class: Optional[int] = None,
        season: Optional[str] = None,
        water_method: Optional[str] = None,
        budget_bucket: Optional[str] = None,
        previous_crop: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> List[ZoneRecommendationType]:
        """Get 6-factor suited crops for an Indian PIN code, soil type, season, water method, budget, and rotation."""
        recs = get_zone_suitability_by_pincode(
            pincode=pincode, 
            soil_class=soil_class,
            season=season,
            water_method=water_method,
            budget_bucket=budget_bucket,
            previous_crop=previous_crop,
            limit=limit or 10
        )
        return [
            ZoneRecommendationType(
                crop=r["crop"],
                category=r.get("category"),
                family=r.get("family"),
                zone_id=r["zone_id"],
                zone_score=float(r.get("zone_score", 0.0)),
                season_score=float(r.get("season_score", 1.0)),
                water_score=float(r.get("water_score", 1.0)),
                soil_score=float(r.get("soil_score", 1.0)),
                budget_score=float(r.get("budget_score", 1.0)),
                rotation_score=float(r.get("rotation_score", 1.0)),
                total_score=float(r.get("total_score", 0.0)),
                match_percentage=float(r.get("match_percentage", 0.0)),
                combined_score=float(r.get("combined_score", 0.0)),
                water_outlook_warning=r.get("water_outlook_warning")
            )
            for r in recs
        ]

    @strawberry.field
    def pincode_outlook(self, pincode: str) -> Optional[GroundwaterOutlookType]:
        """Lookup district water availability, current reservoir level, and recommended/restricted crops for a PIN."""
        data = get_pincode_outlook(pincode)
        return _to_groundwater_alert(data)

    @strawberry.field
    def task_status(self, task_id: str) -> Optional[TaskStatusType]:
        """Check status of an asynchronous LangGraph task queued via RabbitMQ."""
        data = get_task_result(task_id)
        if not data:
            return None
            
        res_obj = None
        if "result" in data:
            r = data["result"]
            res_obj = AdvisoryResultType(
                confidence_score=r.get("confidence_score", 0.0),
                diagnosis_summary=r.get("diagnosis_summary", ""),
                treatment_protocols=[
                    TreatmentProtocolType(
                        disease=tp.get("disease", ""),
                        protocol=tp.get("protocol", ""),
                        type=tp.get("type", "")
                    )
                    for tp in r.get("treatment_protocols", [])
                ],
                preventive_actions=r.get("preventive_actions", []),
                actionable_advisory=r.get("actionable_advisory", ""),
                stages=_to_stage_details(r.get("active_disease", {}).get("stages")) if r.get("active_disease") else None,
                treatment_plan=_to_treatment_steps(r.get("treatment_plan")),
                financial_impact=_to_financial_impact(r.get("financial_impact")),
                spray_safety=_to_spray_safety(r.get("spray_safety")),
                groundwater_alert=_to_groundwater_alert(r.get("groundwater_alert"))
            )
            
        return TaskStatusType(
            task_id=data["task_id"],
            status=data["status"],
            timestamp=data["timestamp"],
            result=res_obj
        )

@strawberry.type
class Mutation:
    @strawberry.mutation
    def ask_copilot(self, query: str) -> CopilotChatResponseType:
        """Conversational NLP interaction mutation."""
        result = run_advisory_agent({"query": query})
        
        treatment_list = [
            TreatmentProtocolType(
                disease=tp.get("disease", ""),
                protocol=tp.get("protocol", ""),
                type=tp.get("type", "Treatment Plan")
            )
            for tp in result.get("treatment_protocols", [])
        ]
        
        adv = result.get("actionable_advisory", "")
        
        return CopilotChatResponseType(
            intent=result.get("intent", "treatment_plan"),
            crop=result.get("identified_crop"),
            symptoms=result.get("symptoms"),
            diagnosis=result.get("diagnosis_summary", ""),
            confidence_score=result.get("confidence_score", 0.0),
            treatments=treatment_list,
            preventive_actions=result.get("preventive_actions", []),
            advisory=adv,
            llm_response=adv,
            stages=_to_stage_details(result.get("active_disease", {}).get("stages")) if result.get("active_disease") else None,
            treatment_plan=_to_treatment_steps(result.get("treatment_plan")),
            financial_impact=_to_financial_impact(result.get("financial_impact")),
            spray_safety=_to_spray_safety(result.get("spray_safety")),
            groundwater_alert=_to_groundwater_alert(result.get("groundwater_alert"))
        )

    @strawberry.mutation
    def submit_diagnostic_task(
        self, 
        crop_name: Optional[str] = None, 
        symptoms: Optional[str] = None,
        crop: Optional[str] = None,
        symptom: Optional[str] = None,
        pincode: Optional[str] = None,
        soil_class: Optional[int] = None,
        season: Optional[str] = None,
        water_method: Optional[str] = None,
        budget_bucket: Optional[str] = None,
        temp_level: Optional[str] = None,
        moisture: Optional[str] = None,
        rain_status: Optional[str] = None,
        wind_risk: Optional[str] = None
    ) -> TaskSubmissionResponseType:
        """Dispatch diagnostic advisory task asynchronously via RabbitMQ broker."""
        target_crop = crop or crop_name
        target_symptom = symptoms or symptom or ""
        
        task_payload = {
            "crop_name": target_crop,
            "symptoms": target_symptom,
            "pincode": pincode,
            "soil_class": soil_class,
            "season": season,
            "water_method": water_method,
            "budget_bucket": budget_bucket,
            "temp_level": temp_level,
            "moisture": moisture,
            "rain_status": rain_status,
            "wind_risk": wind_risk,
            "query": f"{target_crop or ''} {target_symptom or ''} {pincode or ''}".strip()
        }
        
        task_id = publish_diagnostic_task(task_payload)
        return TaskSubmissionResponseType(
            task_id=task_id,
            status="QUEUED",
            message=f"Diagnostic task {task_id} successfully dispatched to RabbitMQ."
        )

    @strawberry.mutation
    def instant_advisory(
        self,
        crop_name: Optional[str] = None,
        symptoms: Optional[str] = None,
        crop: Optional[str] = None,
        symptom: Optional[str] = None,
        pincode: Optional[str] = None,
        soil_class: Optional[int] = None,
        season: Optional[str] = None,
        water_method: Optional[str] = None,
        budget_bucket: Optional[str] = None
    ) -> AdvisoryResultType:
        """Synchronously execute LangGraph advisory reasoning pipeline."""
        target_crop = crop or crop_name
        target_symptom = symptoms or symptom or ""
        
        result = run_advisory_agent({
            "crop_name": target_crop,
            "symptoms": target_symptom,
            "pincode": pincode,
            "soil_class": soil_class,
            "season": season,
            "water_method": water_method,
            "budget_bucket": budget_bucket,
            "query": f"{target_crop or ''} {target_symptom or ''} {pincode or ''}".strip()
        })
        
        treatment_list = [
            TreatmentProtocolType(
                disease=tp.get("disease", ""),
                protocol=tp.get("protocol", ""),
                type=tp.get("type", "Treatment Plan")
            )
            for tp in result.get("treatment_protocols", [])
        ]
        
        return AdvisoryResultType(
            confidence_score=result.get("confidence_score", 0.0),
            diagnosis_summary=result.get("diagnosis_summary", ""),
            treatment_protocols=treatment_list,
            preventive_actions=result.get("preventive_actions", []),
            actionable_advisory=result.get("actionable_advisory", ""),
            stages=_to_stage_details(result.get("active_disease", {}).get("stages")) if result.get("active_disease") else None,
            treatment_plan=_to_treatment_steps(result.get("treatment_plan")),
            financial_impact=_to_financial_impact(result.get("financial_impact")),
            spray_safety=_to_spray_safety(result.get("spray_safety")),
            groundwater_alert=_to_groundwater_alert(result.get("groundwater_alert"))
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)
