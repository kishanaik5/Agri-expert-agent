import pandas as pd
from typing import Dict, Any, List, Optional
from src.config import DATA_DIR

class EmbeddedAgriGraph:
    """In-memory graph database engine with graph traversal methods mirroring Neo4j Cypher queries."""
    _instance: Optional['EmbeddedAgriGraph'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddedAgriGraph, cls).__new__(cls)
            cls._instance._load_graph()
        return cls._instance

    def _load_graph(self):
        print("[KnowledgeGraph] Initializing In-Memory Agricultural Knowledge Graph...")
        self.crops: Dict[str, Dict[str, Any]] = {}
        self.crop_stages: Dict[str, List[Dict[str, Any]]] = {}
        self.diseases: List[Dict[str, Any]] = []
        self.zone_pincodes: Dict[str, int] = {}
        self.crop_zone_scores: List[Dict[str, Any]] = []
        self.crop_soil_scores: List[Dict[str, Any]] = []
        self.weather_rules: List[Dict[str, Any]] = []

        # 1. Load Crops
        agro_crops = DATA_DIR / "kissan_agro_prod" / "crops.csv"
        rec_crops = DATA_DIR / "crop_recommendation" / "crops.csv"
        crop_uid_to_name = {}

        if agro_crops.exists():
            df = pd.read_csv(agro_crops)
            for _, r in df.iterrows():
                name = str(r.get("crop_name", "")).strip().title()
                if name and name != "Nan":
                    self.crops[name.lower()] = {
                        "name": name,
                        "name_hin": str(r.get("lan_hin", "")),
                        "category": "Crop"
                    }

        if rec_crops.exists():
            df = pd.read_csv(rec_crops)
            for _, r in df.iterrows():
                name = str(r.get("name_en", "")).strip().title()
                uid = str(r.get("uid", "")).strip()
                if name and name != "Nan":
                    crop_uid_to_name[uid] = name
                    if name.lower() not in self.crops:
                        self.crops[name.lower()] = {
                            "name": name,
                            "name_hin": str(r.get("name_hi", "")),
                            "category": str(r.get("category", "Crop"))
                        }

        # 2. Load Stages
        stages_path = DATA_DIR / "kissan_agro_prod" / "crop_stage_knowledge.csv"
        if stages_path.exists():
            df = pd.read_csv(stages_path)
            for _, r in df.iterrows():
                crop_name = str(r.get("crop_name", "")).strip().title()
                if not crop_name or crop_name == "Nan":
                    continue
                k = crop_name.lower()
                if k not in self.crop_stages:
                    self.crop_stages[k] = []
                self.crop_stages[k].append({
                    "main_stage": str(r.get("main_stage", "")),
                    "sub_stage": str(r.get("sub_stage_name", "")),
                    "start_day": int(r.get("start_day", 0)) if pd.notna(r.get("start_day")) else 0,
                    "end_day": int(r.get("end_day", 0)) if pd.notna(r.get("end_day")) else 0
                })

        # 3. Load Diseases & Treatments
        kb_path = DATA_DIR / "kissan_cv" / "knowledge_base.csv"
        if kb_path.exists():
            df = pd.read_csv(kb_path)
            for _, r in df.iterrows():
                crop = str(r.get("item_name", "")).strip().title()
                dis = str(r.get("disease_name", "")).strip()
                sci = str(r.get("scientific_name", "")).strip()
                trt = str(r.get("treatment", "")).strip()
                if crop and dis and crop != "Nan":
                    self.diseases.append({
                        "crop": crop,
                        "disease": dis,
                        "pathogen": sci if sci != "Nan" else "",
                        "treatments": [trt] if trt and trt != "Nan" else []
                    })

        # 4. Load Pincodes & Zone Scores
        pin_path = DATA_DIR / "crop_recommendation" / "pincode_zone_mappings.csv"
        if pin_path.exists():
            df = pd.read_csv(pin_path)
            for _, r in df.head(10000).iterrows():
                code = str(r.get("pincode", "")).strip()
                zone = int(r.get("zone", 0)) if pd.notna(r.get("zone")) else 0
                if code:
                    self.zone_pincodes[code] = zone

        zs_path = DATA_DIR / "crop_recommendation" / "crop_zone_scores.csv"
        if zs_path.exists():
            df = pd.read_csv(zs_path)
            for _, r in df.iterrows():
                c_uid = str(r.get("crop_uid", "")).strip()
                c_name = crop_uid_to_name.get(c_uid)
                zone = int(r.get("zone", 0)) if pd.notna(r.get("zone")) else 0
                score = float(r.get("score", 0.0)) if pd.notna(r.get("score")) else 0.0
                if c_name and zone:
                    self.crop_zone_scores.append({"crop": c_name, "zone_id": zone, "score": score})

        # 5. Load Soil Scores
        ss_path = DATA_DIR / "crop_recommendation" / "crop_soil_scores.csv"
        if ss_path.exists():
            df = pd.read_csv(ss_path)
            for _, r in df.iterrows():
                c_uid = str(r.get("crop_uid", "")).strip()
                c_name = crop_uid_to_name.get(c_uid)
                soil_class = int(r.get("soil_class", 0)) if pd.notna(r.get("soil_class")) else 0
                score = float(r.get("score", 0.0)) if pd.notna(r.get("score")) else 0.0
                if c_name and soil_class:
                    self.crop_soil_scores.append({"crop": c_name, "soil_class": soil_class, "score": score})

        # 6. Load Weather Rules
        wr_path = DATA_DIR / "kissan_agro_prod" / "weather_advisory_rules.csv"
        if wr_path.exists():
            df = pd.read_csv(wr_path)
            for _, r in df.iterrows():
                self.weather_rules.append({
                    "temp_level": str(r.get("temp_level", "")).strip(),
                    "moisture": str(r.get("moisture", "")).strip(),
                    "rain_status": str(r.get("rain_status", "")).strip(),
                    "advisory_type": str(r.get("advisory_type", "")).strip(),
                    "advisory": str(r.get("advisory_en", r.get("status", ""))).strip()
                })

        print(f"[KnowledgeGraph] Loaded: {len(self.crops)} Crops, {len(self.diseases)} Diseases, {len(self.zone_pincodes)} Pincodes.")

    def get_crops(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self.crops.values())[:limit]

    def get_crop_profile(self, name: str) -> Optional[Dict[str, Any]]:
        k = name.lower()
        if k not in self.crops:
            # partial match
            for ck, cv in self.crops.items():
                if k in ck or ck in k:
                    k = ck
                    break
        if k in self.crops:
            c = dict(self.crops[k])
            c["stages"] = self.crop_stages.get(k, [])
            return c
        return None

    def search_diseases(self, crop_name: Optional[str], symptom: str) -> List[Dict[str, Any]]:
        matches = []
        sym_lower = (symptom or "").lower()
        crop_lower = (crop_name or "").lower() if crop_name else ""
        
        # Tokenize symptom words
        sym_tokens = [w.strip(" ,.!?") for w in sym_lower.split() if len(w.strip(" ,.!?")) > 2]
        
        for d in self.diseases:
            d_crop = d["crop"].lower()
            d_name = d["disease"].lower()
            d_trt = " ".join(d["treatments"]).lower()
            
            crop_match = (not crop_lower) or (crop_lower in d_crop) or (d_crop in crop_lower)
            
            # Match either direct substring or any significant token
            sym_match = False
            if not sym_lower:
                sym_match = True
            elif sym_lower in d_name or sym_lower in d_trt:
                sym_match = True
            elif any(token in d_name or token in d_trt for token in sym_tokens):
                sym_match = True
                
            if crop_match and sym_match:
                matches.append(d)
                if len(matches) >= 10:
                    break
        return matches

    def get_zone_recommendations(self, pincode: str, soil_class: Optional[int] = None) -> List[Dict[str, Any]]:
        zone_id = self.zone_pincodes.get(pincode, 3) # default zone 3 if not found
        recs = []
        
        soil_lookup = {}
        if soil_class:
            for s in self.crop_soil_scores:
                if s["soil_class"] == soil_class:
                    soil_lookup[s["crop"]] = s["score"]

        for z in self.crop_zone_scores:
            if z["zone_id"] == zone_id:
                crop = z["crop"]
                z_score = z["score"]
                s_score = soil_lookup.get(crop, 50.0)
                comb_score = (z_score + s_score) / 2.0 if soil_class else z_score
                
                recs.append({
                    "crop": crop,
                    "category": self.crops.get(crop.lower(), {}).get("category", "Field Crop"),
                    "zone_id": zone_id,
                    "zone_score": z_score,
                    "combined_score": comb_score
                })
                
        recs.sort(key=lambda x: x["combined_score"], reverse=True)
        return recs[:10]

    def get_weather_advisories(self, temp: Optional[str] = None, moist: Optional[str] = None, rain: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for r in self.weather_rules:
            t_m = (not temp) or (temp.lower() in r["temp_level"].lower())
            m_m = (not moist) or (moist.lower() in r["moisture"].lower())
            r_m = (not rain) or (rain.lower() in r["rain_status"].lower())
            if t_m and m_m and r_m:
                results.append(r)
                if len(results) >= 5:
                    break
        return results if results else self.weather_rules[:3]

def get_embedded_graph() -> EmbeddedAgriGraph:
    return EmbeddedAgriGraph()
