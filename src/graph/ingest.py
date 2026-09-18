import os
import csv
import json
import pandas as pd
from typing import Dict, Any, List
from src.config import DATA_DIR
from src.graph.client import get_graph_client
from src.graph.schema import apply_schema

def ingest_crops(client):
    print("\n--- Ingesting Crops ---")
    agro_crops_path = DATA_DIR / "kissan_agro_prod" / "crops.csv"
    rec_crops_path = DATA_DIR / "crop_recommendation" / "crops.csv"
    
    crops_dict: Dict[str, Dict[str, Any]] = {}
    
    if agro_crops_path.exists():
        df_agro = pd.read_csv(agro_crops_path)
        for _, row in df_agro.iterrows():
            name = str(row.get("crop_name", "")).strip().title()
            if not name or name == "Nan":
                continue
            crops_dict[name] = {
                "name": name,
                "name_hin": str(row.get("lan_hin", "")),
                "name_kan": str(row.get("lan_kan", "")),
                "name_mar": str(row.get("lan_mar", "")),
                "name_tel": str(row.get("lan_tel", "")),
                "name_tam": str(row.get("lan_tam", "")),
                "category": "Crop"
            }
            
    if rec_crops_path.exists():
        df_rec = pd.read_csv(rec_crops_path)
        for _, row in df_rec.iterrows():
            name = str(row.get("name_en", "")).strip().title()
            if not name or name == "Nan":
                continue
            if name not in crops_dict:
                crops_dict[name] = {
                    "name": name,
                    "name_hin": str(row.get("name_hi", "")),
                    "name_kan": str(row.get("name_kn", "")),
                    "name_mar": str(row.get("name_mr", "")),
                    "name_tel": str(row.get("name_te", "")),
                    "name_tam": str(row.get("name_ta", "")),
                    "category": str(row.get("category", "Crop"))
                }

    cypher = """
    UNWIND $batch AS c
    MERGE (crop:Crop {name: c.name})
    SET crop.name_hin = c.name_hin,
        crop.name_kan = c.name_kan,
        crop.name_mar = c.name_mar,
        crop.name_tel = c.name_tel,
        crop.name_tam = c.name_tam,
        crop.category = c.category
    """
    batch = list(crops_dict.values())
    client.execute_write(cypher, {"batch": batch})
    print(f" Ingested {len(batch)} Crop nodes.")

def ingest_crop_stages(client):
    print("\n--- Ingesting Crop Growth Stages ---")
    path = DATA_DIR / "kissan_agro_prod" / "crop_stage_knowledge.csv"
    if not path.exists():
        return
    
    df = pd.read_csv(path)
    stages = []
    for idx, row in df.iterrows():
        crop_name = str(row.get("crop_name", "")).strip().title()
        main_stage = str(row.get("main_stage", "")).strip()
        sub_stage = str(row.get("sub_stage_name", "")).strip()
        if not crop_name or not sub_stage or crop_name == "Nan":
            continue
        stage_id = f"{crop_name}_{main_stage}_{sub_stage}".replace(" ", "_")
        stages.append({
            "crop_name": crop_name,
            "stage_id": stage_id,
            "main_stage": main_stage,
            "sub_stage": sub_stage,
            "start_day": int(row.get("start_day", 0)) if pd.notna(row.get("start_day")) else 0,
            "end_day": int(row.get("end_day", 0)) if pd.notna(row.get("end_day")) else 0
        })
        
    cypher = """
    UNWIND $batch AS s
    MERGE (crop:Crop {name: s.crop_name})
    MERGE (stage:CropStage {stage_id: s.stage_id})
    SET stage.main_stage = s.main_stage,
        stage.sub_stage = s.sub_stage,
        stage.start_day = s.start_day,
        stage.end_day = s.end_day
    MERGE (crop)-[:HAS_STAGE]->(stage)
    """
    client.execute_write(cypher, {"batch": stages})
    print(f" Ingested {len(stages)} CropStage nodes & [:HAS_STAGE] relationships.")

def ingest_knowledge_base_and_diagnostics(client):
    print("\n--- Ingesting Disease Diagnostics & Treatments ---")
    kb_path = DATA_DIR / "kissan_cv" / "knowledge_base.csv"
    if not kb_path.exists():
        return
        
    df = pd.read_csv(kb_path)
    items = []
    for _, row in df.iterrows():
        crop_name = str(row.get("item_name", "")).strip().title()
        disease_name = str(row.get("disease_name", "")).strip()
        scientific = str(row.get("scientific_name", "")).strip()
        treatment = str(row.get("treatment", "")).strip()
        
        if not crop_name or not disease_name or crop_name == "Nan" or disease_name == "Nan":
            continue
            
        items.append({
            "crop_name": crop_name,
            "disease_name": disease_name,
            "scientific_name": scientific if scientific != "Nan" else "",
            "treatment": treatment if treatment != "Nan" else ""
        })

    cypher = """
    UNWIND $batch AS item
    MERGE (c:Crop {name: item.crop_name})
    MERGE (d:Disease {name: item.disease_name})
    MERGE (c)-[:PRONE_TO]->(d)
    WITH item, d
    WHERE item.scientific_name <> ''
    MERGE (p:Pathogen {name: item.scientific_name})
    MERGE (d)-[:CAUSED_BY]->(p)
    WITH item, d
    WHERE item.treatment <> ''
    MERGE (t:Treatment {name: item.treatment})
    MERGE (d)-[:TREATED_BY]->(t)
    """
    client.execute_write(cypher, {"batch": items})
    print(f" Ingested {len(items)} Disease-Treatment relationships.")

def ingest_zones_and_pincodes(client):
    print("\n--- Ingesting Agro-Climatic Zones & Pincode Mappings ---")
    pincode_path = DATA_DIR / "crop_recommendation" / "pincode_zone_mappings.csv"
    zone_scores_path = DATA_DIR / "crop_recommendation" / "crop_zone_scores.csv"
    rec_crops_path = DATA_DIR / "crop_recommendation" / "crops.csv"

    # Crop UID to Name mapping
    crop_uid_to_name = {}
    if rec_crops_path.exists():
        df_crops = pd.read_csv(rec_crops_path)
        for _, row in df_crops.iterrows():
            uid = str(row.get("uid", "")).strip()
            name = str(row.get("name_en", "")).strip().title()
            if uid and name:
                crop_uid_to_name[uid] = name

    # 1. Pincodes and Zones
    if pincode_path.exists():
        df_pin = pd.read_csv(pincode_path)
        pin_batch = []
        for _, row in df_pin.iterrows():
            code = str(row.get("pincode", "")).strip()
            zone = int(row.get("zone", 0)) if pd.notna(row.get("zone")) else 0
            if code and code != "nan":
                pin_batch.append({"code": code, "zone": zone})
                
        cypher_pin = """
        UNWIND $batch AS p
        MERGE (z:AgroZone {zone_id: p.zone})
        MERGE (pin:Pincode {code: p.code})
        MERGE (pin)-[:IN_ZONE]->(z)
        """
        # Batch in chunks of 5000
        for i in range(0, len(pin_batch), 5000):
            chunk = pin_batch[i:i+5000]
            client.execute_write(cypher_pin, {"batch": chunk})
        print(f" Ingested all {len(pin_batch)} Pincodes and AgroZones.")

    # 2. Crop Zone Scores
    if zone_scores_path.exists():
        df_zs = pd.read_csv(zone_scores_path)
        zone_scores = []
        for _, row in df_zs.iterrows():
            c_uid = str(row.get("crop_uid", "")).strip()
            zone = int(row.get("zone", 0)) if pd.notna(row.get("zone")) else 0
            score = float(row.get("score", 0.0)) if pd.notna(row.get("score")) else 0.0
            crop_name = crop_uid_to_name.get(c_uid)
            if crop_name and zone:
                zone_scores.append({"crop_name": crop_name, "zone": zone, "score": score})

        cypher_zs = """
        UNWIND $batch AS item
        MERGE (c:Crop {name: item.crop_name})
        MERGE (z:AgroZone {zone_id: item.zone})
        MERGE (c)-[r:SUITED_FOR_ZONE]->(z)
        SET r.score = item.score
        """
        client.execute_write(cypher_zs, {"batch": zone_scores})
        print(f" Ingested {len(zone_scores)} Crop-Zone suitability edges.")

def ingest_soil_scores(client):
    print("\n--- Ingesting Soil Class Suitability ---")
    soil_scores_path = DATA_DIR / "crop_recommendation" / "crop_soil_scores.csv"
    rec_crops_path = DATA_DIR / "crop_recommendation" / "crops.csv"
    
    crop_uid_to_name = {}
    if rec_crops_path.exists():
        df_crops = pd.read_csv(rec_crops_path)
        for _, row in df_crops.iterrows():
            crop_uid_to_name[str(row.get("uid", "")).strip()] = str(row.get("name_en", "")).strip().title()

    if soil_scores_path.exists():
        df_soil = pd.read_csv(soil_scores_path)
        soil_batch = []
        for _, row in df_soil.iterrows():
            c_uid = str(row.get("crop_uid", "")).strip()
            soil_class = int(row.get("soil_class", 0)) if pd.notna(row.get("soil_class")) else 0
            score = float(row.get("score", 0.0)) if pd.notna(row.get("score")) else 0.0
            crop_name = crop_uid_to_name.get(c_uid)
            if crop_name and soil_class:
                soil_batch.append({"crop_name": crop_name, "soil_class": soil_class, "score": score})

        cypher = """
        UNWIND $batch AS item
        MERGE (c:Crop {name: item.crop_name})
        MERGE (s:SoilType {soil_class: item.soil_class})
        MERGE (c)-[r:SUITED_FOR_SOIL]->(s)
        SET r.score = item.score
        """
        client.execute_write(cypher, {"batch": soil_batch})
        print(f" Ingested {len(soil_batch)} Crop-Soil suitability edges.")

def ingest_weather_rules(client):
    print("\n--- Ingesting Weather Advisory Rules ---")
    path = DATA_DIR / "kissan_agro_prod" / "weather_advisory_rules.csv"
    if not path.exists():
        return
        
    df = pd.read_csv(path)
    rules = []
    for idx, row in df.iterrows():
        temp = str(row.get("temp_level", "")).strip()
        moisture = str(row.get("moisture", "")).strip()
        wind = str(row.get("wind_risk", "")).strip()
        rain = str(row.get("rain_status", "")).strip()
        adv_type = str(row.get("advisory_type", "")).strip()
        adv_text = str(row.get("advisory_en", row.get("status", ""))).strip()
        
        rule_id = f"rule_{idx}_{adv_type}"
        rules.append({
            "rule_id": rule_id,
            "temp_level": temp,
            "moisture": moisture,
            "wind_risk": wind,
            "rain_status": rain,
            "advisory_type": adv_type,
            "advisory": adv_text
        })

    cypher = """
    UNWIND $batch AS r
    MERGE (rule:WeatherRule {rule_id: r.rule_id})
    SET rule.temp_level = r.temp_level,
        rule.moisture = r.moisture,
        rule.wind_risk = r.wind_risk,
        rule.rain_status = r.rain_status,
        rule.advisory_type = r.advisory_type,
        rule.advisory = r.advisory
    """
    client.execute_write(cypher, {"batch": rules})
    print(f" Ingested {len(rules)} WeatherRule nodes.")

def run_all_ingestions():
    print("==================================================")
    print("Starting Neo4j Knowledge Graph Ingestion Pipeline")
    print("==================================================")
    apply_schema()
    client = get_graph_client()
    
    ingest_crops(client)
    ingest_crop_stages(client)
    ingest_knowledge_base_and_diagnostics(client)
    ingest_zones_and_pincodes(client)
    ingest_soil_scores(client)
    ingest_weather_rules(client)
    
    print("\n Knowledge Graph ingestion complete!")

if __name__ == "__main__":
    run_all_ingestions()
