import strawberry
from typing import List, Optional

@strawberry.type
class CropStageType:
    main_stage: str
    sub_stage: str
    start_day: int
    end_day: int

@strawberry.type
class CropType:
    name: str
    name_hin: Optional[str] = None
    category: Optional[str] = None
    stages: Optional[List[CropStageType]] = None

@strawberry.type
class DiseaseType:
    crop: str
    disease: str
    pathogen: Optional[str] = None
    treatments: List[str]

@strawberry.type
class ZoneRecommendationType:
    crop: str
    category: Optional[str] = None
    zone_id: int
    zone_score: float
    combined_score: float

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
