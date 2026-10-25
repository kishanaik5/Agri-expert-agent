import strawberry
from typing import List, Optional

@strawberry.type
class TreatmentStepType:
    day: str
    step: str
    title: str
    desc: str

@strawberry.type
class DiseaseStageDetailType:
    stage_number: int
    stage_name: str
    early_intervention_message: Optional[str] = None
    spread_percentage: Optional[str] = None
    eta_for_next_stage_in_days: Optional[float] = None
    stage_timeline_day: Optional[str] = None
    stage_revenue_loss_min: Optional[float] = None
    stage_revenue_loss_max: Optional[float] = None
    revenue_loss_range_display: Optional[str] = None
    max_revenue_loss_max_per_acre: Optional[float] = None
    min_yield_loss_pct: Optional[float] = None
    max_yield_loss_pct: Optional[float] = None
    spread_speed_class: Optional[str] = None
    incubation_period_days: Optional[str] = None
    disease_cycle_days: Optional[str] = None
    days_to_severe: Optional[str] = None
    treatment_steps: Optional[List[TreatmentStepType]] = None
    recoverability: Optional[str] = None
    action: Optional[str] = None
    header_alert: Optional[str] = None

@strawberry.type
class FinancialImpactType:
    stage_revenue_loss_display: Optional[str] = None
    max_revenue_loss_max_per_acre: Optional[float] = None
    min_yield_loss_pct: Optional[float] = None
    max_yield_loss_pct: Optional[float] = None
    net_returns_mid: Optional[float] = None

@strawberry.type
class SpraySafetyType:
    status: str
    recommended_window: Optional[str] = None
    wind_risk: Optional[str] = None
    fungal_risk: Optional[str] = None
    advisory_message: Optional[str] = None

@strawberry.type
class GroundwaterOutlookType:
    pincode: str
    district: str
    water_outlook_tag: str
    reservoir_level_current: Optional[str] = None
    monsoon_forecast: Optional[str] = None
    water_risk: Optional[str] = None
    crops_to_grow: List[str] = strawberry.field(default_factory=list)
    crops_to_avoid: List[str] = strawberry.field(default_factory=list)
    what_this_means: Optional[str] = None

@strawberry.type
class CropStageType:
    main_stage: str
    sub_stage: str
    start_day: int
    end_day: int
    susceptible_pests: Optional[str] = None
    pest_risk_factors: Optional[str] = None
    pest_management: Optional[str] = None
    susceptible_diseases: Optional[str] = None
    disease_risk_factors: Optional[str] = None
    disease_management: Optional[str] = None
    optimal_temp_c: Optional[str] = None
    rel_humidity_pct: Optional[str] = None
    soil_moisture_pct: Optional[str] = None
    uv_index: Optional[str] = None
    irrigation_mm: Optional[str] = None

@strawberry.type
class CropType:
    name: str
    name_hin: Optional[str] = None
    name_kan: Optional[str] = None
    name_mar: Optional[str] = None
    name_tel: Optional[str] = None
    name_tam: Optional[str] = None
    category: Optional[str] = None
    stages: Optional[List[CropStageType]] = None

@strawberry.type
class DiseaseType:
    crop: str
    disease: str
    pathogen: Optional[str] = None
    treatments: List[str]
    stages: Optional[List[DiseaseStageDetailType]] = None
    active_stage: Optional[DiseaseStageDetailType] = None

@strawberry.type
class ZoneRecommendationType:
    crop: str
    category: Optional[str] = None
    family: Optional[str] = None
    zone_id: int
    zone_score: float
    season_score: float = 1.0
    water_score: float = 1.0
    soil_score: float = 1.0
    budget_score: float = 1.0
    rotation_score: float = 1.0
    total_score: float = 0.0
    match_percentage: float = 0.0
    combined_score: float = 0.0
    water_outlook_warning: Optional[str] = None

@strawberry.type
class TreatmentProtocolType:
    disease: str
    protocol: str
    type: str

@strawberry.type
class AdvisoryResultType:
    confidence_score: float
    diagnosis_summary: str
    treatment_protocols: List[TreatmentProtocolType]
    preventive_actions: List[str]
    actionable_advisory: str
    stages: Optional[List[DiseaseStageDetailType]] = None
    treatment_plan: Optional[List[TreatmentStepType]] = None
    financial_impact: Optional[FinancialImpactType] = None
    spray_safety: Optional[SpraySafetyType] = None
    groundwater_alert: Optional[GroundwaterOutlookType] = None

@strawberry.type
class CopilotChatResponseType:
    intent: str
    crop: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: str = ""
    confidence_score: float = 0.0
    treatments: List[TreatmentProtocolType] = strawberry.field(default_factory=list)
    preventive_actions: List[str] = strawberry.field(default_factory=list)
    advisory: str = ""
    llm_response: str = ""
    stages: Optional[List[DiseaseStageDetailType]] = None
    treatment_plan: Optional[List[TreatmentStepType]] = None
    financial_impact: Optional[FinancialImpactType] = None
    spray_safety: Optional[SpraySafetyType] = None
    groundwater_alert: Optional[GroundwaterOutlookType] = None

@strawberry.type
class TaskStatusType:
    task_id: str
    status: str
    timestamp: float
    result: Optional[AdvisoryResultType] = None

@strawberry.type
class TaskSubmissionResponseType:
    task_id: str
    status: str
    message: str
