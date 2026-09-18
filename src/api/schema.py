import strawberry
from typing import List, Optional
from src.api.types import (
    CropType,
    CropStageType,
    DiseaseType,
    ZoneRecommendationType,
    AdvisoryResultType,
    TreatmentProtocolType,
    TaskStatusType,
    TaskSubmissionResponseType
)
from src.graph.client import get_graph_client
from src.graph.embedded_graph import get_embedded_graph
from src.agent.tools import (
    get_crop_profile,
    search_disease_and_treatments,
    get_zone_suitability_by_pincode
)
from src.agent.workflow import run_advisory_agent
from src.queue.broker import publish_diagnostic_task
from src.queue.worker import get_task_result

@strawberry.type
class Query:
    @strawberry.field
    def crops(self, limit: Optional[int] = 20) -> List[CropType]:
        """List master crops available in the knowledge graph."""
        client = get_graph_client()
        if client.verify_connectivity():
            cypher = """
            MATCH (c:Crop)
            RETURN c.name AS name, c.name_hin AS name_hin, c.category AS category
            ORDER BY c.name
            LIMIT $limit
            """
            records = client.query(cypher, {"limit": limit or 20})
            return [
                CropType(
                    name=r["name"],
                    name_hin=r.get("name_hin"),
                    category=r.get("category")
                )
                for r in records
            ]
        else:
            records = get_embedded_graph().get_crops(limit or 20)
            return [
                CropType(
                    name=r["name"],
                    name_hin=r.get("name_hin"),
                    category=r.get("category")
                )
                for r in records
            ]

    @strawberry.field
    def crop_details(self, name: str) -> Optional[CropType]:
        """Fetch deep profile of a crop including its phenological growth stages."""
        profile = get_crop_profile(name)
        if not profile:
            return None
        
        stages = [
            CropStageType(
                main_stage=s.get("main_stage", ""),
                sub_stage=s.get("sub_stage", ""),
                start_day=s.get("start_day", 0),
                end_day=s.get("end_day", 0)
            )
            for s in profile.get("stages", [])
        ]
        return CropType(
            name=profile["name"],
            name_hin=profile.get("name_hin"),
            category=profile.get("category"),
            stages=stages
        )

    @strawberry.field
    def diseases(
        self, 
        crop_name: Optional[str] = None, 
        symptom: Optional[str] = None,
        crop: Optional[str] = None,
        symptoms: Optional[str] = None
    ) -> List[DiseaseType]:
        """Search diseases and treatments for a crop or symptom."""
        target_crop = crop or crop_name
        target_symptom = symptoms or symptom or ""
        results = search_disease_and_treatments(target_crop, target_symptom)
        return [
            DiseaseType(
                crop=r["crop"],
                disease=r["disease"],
                pathogen=r.get("pathogen"),
                treatments=r.get("treatments", [])
            )
            for r in results
        ]

    @strawberry.field
    def disease(
        self, 
        crop_name: Optional[str] = None, 
        symptom: Optional[str] = None,
        crop: Optional[str] = None,
        symptoms: Optional[str] = None
    ) -> List[DiseaseType]:
        """Alias for diseases query."""
        target_crop = crop or crop_name
        target_symptom = symptoms or symptom or ""
        results = search_disease_and_treatments(target_crop, target_symptom)
        return [
            DiseaseType(
                crop=r["crop"],
                disease=r["disease"],
                pathogen=r.get("pathogen"),
                treatments=r.get("treatments", [])
            )
            for r in results
        ]

    @strawberry.field
    def zone_recommendations(self, pincode: str, soil_class: Optional[int] = None) -> List[ZoneRecommendationType]:
        """Get suited crops for an Indian PIN code and soil type."""
        recs = get_zone_suitability_by_pincode(pincode, soil_class)
        return [
            ZoneRecommendationType(
                crop=r["crop"],
                category=r.get("category"),
                zone_id=r["zone_id"],
                zone_score=float(r.get("zone_score", 0.0)),
                combined_score=float(r.get("combined_score", 0.0))
            )
            for r in recs
        ]

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
                actionable_advisory=r.get("actionable_advisory", "")
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
    def submit_diagnostic_task(
        self, 
        crop_name: Optional[str] = None, 
        symptoms: Optional[str] = None,
        crop: Optional[str] = None,
        symptom: Optional[str] = None,
        pincode: Optional[str] = None,
        soil_class: Optional[int] = None,
        temp_level: Optional[str] = None,
        moisture: Optional[str] = None,
        rain_status: Optional[str] = None
    ) -> TaskSubmissionResponseType:
        """Asynchronously dispatches a diagnostic request to RabbitMQ / CloudAMQP queue for LangGraph agent worker."""
        target_crop = crop or crop_name or "Crop"
        target_symptoms = symptoms or symptom or ""
        payload = {
            "crop_name": target_crop,
            "symptoms": target_symptoms,
            "pincode": pincode,
            "soil_class": soil_class,
            "temp_level": temp_level,
            "moisture": moisture,
            "rain_status": rain_status
        }
        try:
            task_id = publish_diagnostic_task(payload)
            msg = f"Diagnostic job submitted to RabbitMQ queue for crop '{target_crop}'."
        except Exception as e:
            # Fallback to direct async task processing if broker offline
            from src.queue.worker import save_task_result
            import uuid, time
            task_id = f"task_{uuid.uuid4().hex[:12]}"
            res = run_advisory_agent(payload)
            save_task_result(task_id, {
                "task_id": task_id,
                "status": "COMPLETED",
                "timestamp": time.time(),
                "input": payload,
                "result": res
            })
            msg = f"Diagnostic task processed via direct fallback executor for crop '{target_crop}'."

        return TaskSubmissionResponseType(
            task_id=task_id,
            status="QUEUED",
            message=msg
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
        temp_level: Optional[str] = None,
        moisture: Optional[str] = None,
        rain_status: Optional[str] = None
    ) -> AdvisoryResultType:
        """Synchronously executes the LangGraph agent graph on the request and returns the advisory."""
        target_crop = crop or crop_name or "Crop"
        target_symptoms = symptoms or symptom or ""
        payload = {
            "crop_name": target_crop,
            "symptoms": target_symptoms,
            "pincode": pincode,
            "soil_class": soil_class,
            "temp_level": temp_level,
            "moisture": moisture,
            "rain_status": rain_status
        }
        res = run_advisory_agent(payload)
        return AdvisoryResultType(
            confidence_score=res.get("confidence_score", 0.0),
            diagnosis_summary=res.get("diagnosis_summary", ""),
            treatment_protocols=[
                TreatmentProtocolType(
                    disease=tp.get("disease", ""),
                    protocol=tp.get("protocol", ""),
                    type=tp.get("type", "")
                )
                for tp in res.get("treatment_protocols", [])
            ],
            preventive_actions=res.get("preventive_actions", []),
            actionable_advisory=res.get("actionable_advisory", "")
        )

schema = strawberry.Schema(query=Query, mutation=Mutation)
