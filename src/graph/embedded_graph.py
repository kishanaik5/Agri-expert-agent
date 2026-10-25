import pandas as pd
import json
import ast
import re
import os
from typing import Dict, Any, List, Optional
from src.config import DATA_DIR

class EmbeddedAgriGraph:
    """
    High-Performance In-Memory Agricultural Knowledge Graph Engine.
    Deeply integrates:
      - cv_kb_version2 (Multi-stage disease progression, Day 1/2/5 treatment protocols, revenue/yield loss)
      - crop_stage_knowledge (Phenological growth stages, pest/disease susceptibilities, environmental thresholds)
      - season_advisor_pincode (Pincode groundwater reserves, monsoon forecasts, recommended & restricted crops)
      - crop_recommendation (6-factor weighted suitability: Zone, Season, Water, Soil, Budget, Rotation)
      - weather_advisory_rules (Operational spraying, fungal risk, and irrigation advisories)
    """
    _instance: Optional['EmbeddedAgriGraph'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddedAgriGraph, cls).__new__(cls)
            cls._instance._load_graph()
        return cls._instance

    def _load_graph(self):
        print("[KnowledgeGraph] Initializing Deep Agricultural Knowledge Engine...")
        self.crops: Dict[str, Dict[str, Any]] = {}
        self.crop_aliases: Dict[str, str] = {}
        self.crop_phenology: Dict[str, List[Dict[str, Any]]] = {}
        self.disease_profiles: Dict[str, Dict[str, Any]] = {}  # key: (crop.lower(), disease.lower())
        self.diseases_list: List[Dict[str, Any]] = []
        
        # Pincode & Regional Suitability
        self.pincode_to_zone: Dict[str, int] = {}
        self.pincode_season_outlook: Dict[str, Dict[str, Any]] = {}
        
        # Recommendation scoring tables
        self.rec_crops: Dict[str, Dict[str, Any]] = {}  # crop_uid -> crop info
        self.crop_name_to_uid: Dict[str, str] = {}
        self.zone_scores: Dict[str, Dict[int, float]] = {}  # crop_uid -> {zone_id: score}
        self.season_scores: Dict[str, Dict[str, float]] = {}  # crop_uid -> {season: score}
        self.water_scores: Dict[str, Dict[str, float]] = {}  # crop_uid -> {water_method: score}
        self.soil_scores: Dict[str, Dict[int, float]] = {}  # crop_uid -> {soil_class: score}
        self.budget_rules: Dict[str, Dict[str, float]] = {}  # budget_bucket -> {cost_class: score}
        self.rotation_rules: Dict[str, float] = {}  # situation -> score
        self.scoring_weights: Dict[str, float] = {
            "ZONE": 2.0, "SEASON": 2.0, "WATER": 2.0, "SOIL": 1.5, "BUDGET": 1.5, "ROTATION": 1.0
        }
        self.weather_rules: List[Dict[str, Any]] = []

        # 1. Load Master Crops & Multilingual Aliases
        self._load_master_crops()

        # 2. Load Phenological Stages & Management (kissan_agro_prod/crop_stage_knowledge.csv)
        self._load_crop_phenology()

        # 3. Load Disease Knowledge Base (cv_kb_v2_en.csv + fallback knowledge_base.csv)
        self._load_disease_knowledge_base()

        # 4. Load Pincode Zone Mappings & Regional Outlook
        self._load_pincode_data()

        # 5. Load 6-Factor Recommendation Engine Data
        self._load_recommendation_models()

        # 6. Load Weather Advisory Rules
        self._load_weather_rules()

        print(f"[KnowledgeGraph] Ready: {len(self.crops)} Crops, {len(self.diseases_list)} Diseases, {len(self.pincode_to_zone)} PIN Codes.")

    def _register_alias(self, alias: str, canonical: str):
        if not alias or pd.isna(alias):
            return
        clean = str(alias).strip().lower()
        if len(clean) < 2:
            return
        self.crop_aliases[clean] = canonical
        # Also clean punctuation
        no_punc = re.sub(r'[\(\)\/\,\-]', ' ', clean)
        for part in no_punc.split():
            part = part.strip()
            if len(part) >= 3 and part not in self.crop_aliases:
                self.crop_aliases[part] = canonical

    def _load_master_crops(self):
        agro_crops = DATA_DIR / "kissan_agro_prod" / "crops.csv"
        rec_crops = DATA_DIR / "crop_recommendation" / "crops.csv"

        if agro_crops.exists():
            df = pd.read_csv(agro_crops)
            for _, r in df.iterrows():
                name = str(r.get("crop_name", "")).strip().title()
                if not name or name == "Nan":
                    continue
                k = name.lower()
                self.crops[k] = {
                    "name": name,
                    "name_hin": str(r.get("lan_hin", "")),
                    "name_kan": str(r.get("lan_kan", "")),
                    "name_mar": str(r.get("lan_mar", "")),
                    "name_tel": str(r.get("lan_tel", "")),
                    "name_tam": str(r.get("lan_tam", "")),
                    "name_guj": str(r.get("lan_guj", "")),
                    "category": "Field Crop"
                }
                self._register_alias(name, name)
                for lang_col in ["lan_hin", "lan_kan", "lan_mar", "lan_tel", "lan_tam", "lan_guj", "lan_urd", "lan_ban"]:
                    val = r.get(lang_col)
                    if pd.notna(val):
                        self._register_alias(str(val), name)

        if rec_crops.exists():
            df = pd.read_csv(rec_crops)
            for _, r in df.iterrows():
                name = str(r.get("name_en", "")).strip().title()
                uid = str(r.get("uid", "")).strip()
                if not name or name == "Nan":
                    continue
                k = name.lower()
                self.rec_crops[uid] = {
                    "uid": uid,
                    "name": name,
                    "family": str(r.get("family", "")),
                    "horizon": str(r.get("horizon", "SEASONAL")),
                    "water_need": str(r.get("water_need", "MEDIUM")),
                    "cost_class": str(r.get("cost_class", "MEDIUM")),
                    "category": str(r.get("category", "Crop"))
                }
                self.crop_name_to_uid[k] = uid
                if k not in self.crops:
                    self.crops[k] = {
                        "name": name,
                        "name_hin": str(r.get("name_hn", "")),
                        "name_kan": str(r.get("name_kn", "")),
                        "name_mar": str(r.get("name_mr", "")),
                        "name_tel": str(r.get("name_te", "")),
                        "name_tam": str(r.get("name_ta", "")),
                        "category": str(r.get("category", "Crop"))
                    }
                self._register_alias(name, name)

    def _load_crop_phenology(self):
        stages_path = DATA_DIR / "kissan_agro_prod" / "crop_stage_knowledge.csv"
        if not stages_path.exists():
            return

        df = pd.read_csv(stages_path)
        for _, r in df.iterrows():
            c_name = str(r.get("crop_name", "")).strip()
            if not c_name or c_name == "nan":
                continue
            canonical = self.normalize_crop_name(c_name.replace("_", " "))
            k = canonical.lower()

            env_raw = r.get("env_conditions")
            env_parsed = {}
            if pd.notna(env_raw):
                try:
                    env_parsed = json.loads(env_raw)
                except Exception:
                    pass

            stage_obj = {
                "main_stage": str(r.get("main_stage", "")).strip(),
                "sub_stage": str(r.get("sub_stage_name", "")).strip(),
                "start_day": int(r.get("start_day", 0)) if pd.notna(r.get("start_day")) else 0,
                "end_day": int(r.get("end_day", 0)) if pd.notna(r.get("end_day")) else 0,
                "susceptible_pests": str(r.get("susceptible_pests", "")) if pd.notna(r.get("susceptible_pests")) else "",
                "pest_risk_factors": str(r.get("pest_risk_factors", "")) if pd.notna(r.get("pest_risk_factors")) else "",
                "pest_management": str(r.get("pest_management", "")) if pd.notna(r.get("pest_management")) else "",
                "susceptible_diseases": str(r.get("susceptible_diseases", "")) if pd.notna(r.get("susceptible_diseases")) else "",
                "disease_risk_factors": str(r.get("disease_risk_factors", "")) if pd.notna(r.get("disease_risk_factors")) else "",
                "disease_management": str(r.get("disease_management", "")) if pd.notna(r.get("disease_management")) else "",
                "env_conditions": env_parsed
            }

            if k not in self.crop_phenology:
                self.crop_phenology[k] = []
            self.crop_phenology[k].append(stage_obj)

    def _load_disease_knowledge_base(self):
        # 1. Fast English slice of cv_kb_version2
        en_v2_path = DATA_DIR / "kissan_cv" / "cv_kb_v2_en.csv"
        raw_v2_path = DATA_DIR / "kissan_cv" / "cv_kb_version2.csv"

        if not en_v2_path.exists() and raw_v2_path.exists():
            try:
                print("[KnowledgeGraph] Generating English slice from cv_kb_version2.csv...")
                chunks = []
                for chunk in pd.read_csv(raw_v2_path, chunksize=40000):
                    en_c = chunk[chunk['language'] == 'en']
                    if len(en_c) > 0:
                        chunks.append(en_c)
                df_en = pd.concat(chunks, ignore_index=True)
                df_en.to_csv(en_v2_path, index=False)
            except Exception as e:
                print(f"[KnowledgeGraph] Error extracting English slice: {e}")

        if en_v2_path.exists():
            df = pd.read_csv(en_v2_path)
            for _, r in df.iterrows():
                crop = str(r.get("item_name_en", "")).strip().title()
                disease = str(r.get("disease_name_en", "")).strip()
                if not crop or not disease or crop == "Nan" or disease == "Nan":
                    continue

                canonical_crop = self.normalize_crop_name(crop)
                self._register_alias(crop, canonical_crop)

                prof_key = (canonical_crop.lower(), disease.lower())

                # Parse treatment_plan_json
                trt_plan_raw = r.get("treatment_plan_json")
                treatment_steps = []
                if pd.notna(trt_plan_raw) and trt_plan_raw != "[]":
                    try:
                        treatment_steps = ast.literal_eval(trt_plan_raw)
                    except Exception:
                        pass

                # Parse preventative measures
                prev_raw = r.get("disease_preventative_measures")
                preventative_measures = []
                if pd.notna(prev_raw) and prev_raw != "[]":
                    try:
                        preventative_measures = ast.literal_eval(prev_raw)
                    except Exception:
                        pass

                def _to_float(v, d=0.0):
                    if pd.isna(v): return d
                    try:
                        return float(v)
                    except Exception:
                        m = re.search(r"[-+]?\d*\.?\d+", str(v))
                        return float(m.group(0)) if m else d

                stage_info = {
                    "stage_number": int(_to_float(r.get("stage_number", 1), 1)),
                    "stage_name": str(r.get("stage_name", "")),
                    "early_intervention_message": str(r.get("early_intervention_message", "")),
                    "spread_percentage": str(r.get("spread_percentage", "")),
                    "eta_for_next_stage_in_days": _to_float(r.get("eta_for_next_stage_in_days", 0)),
                    "stage_timeline_day": str(r.get("stage_timeline_day", "")),
                    "stage_revenue_loss_min": _to_float(r.get("stage_revenue_loss_min", 0)),
                    "stage_revenue_loss_max": _to_float(r.get("stage_revenue_loss_max", 0)),
                    "stage_revenue_loss_range_display": str(r.get("stage_revenue_loss_range_display", "")),
                    "max_revenue_loss_max_per_acre": _to_float(r.get("max_revenue_loss_max_per_acre", 0)),
                    "min_yield_loss_pct": _to_float(r.get("min_yield_loss_pct", 0)),
                    "max_yield_loss_pct": _to_float(r.get("max_yield_loss_pct", 0)),
                    "spread_speed_class": str(r.get("spread_speed_class", "")),
                    "incubation_period_days": str(r.get("incubation_period_days", "")) if pd.notna(r.get("incubation_period_days")) else "",
                    "disease_cycle_days": str(r.get("disease_cycle_days", "")) if pd.notna(r.get("disease_cycle_days")) else "",
                    "days_to_severe": str(r.get("days_to_severe", "")) if pd.notna(r.get("days_to_severe")) else "",
                    "treatment_steps": treatment_steps,
                    "preventative_measures": preventative_measures,
                    "recoverability": str(r.get("recoverability", "")),
                    "action": str(r.get("action", "")),
                    "header_alert": str(r.get("header_alert", ""))
                }

                if prof_key not in self.disease_profiles:
                    self.disease_profiles[prof_key] = {
                        "crop": canonical_crop,
                        "disease": disease,
                        "scientific_name": str(r.get("scientific_name", "")),
                        "stages": [],
                        "category": str(r.get("category", "Crop"))
                    }
                self.disease_profiles[prof_key]["stages"].append(stage_info)

        # Build diseases_list with stages sorted
        for prof_key, prof in self.disease_profiles.items():
            prof["stages"].sort(key=lambda s: s["stage_number"])
            # Flatten protocols for simple queries
            protocols = []
            for stg in prof["stages"]:
                for step in stg.get("treatment_steps", []):
                    desc = step.get("desc", "")
                    title = step.get("title", "")
                    day = step.get("day", "")
                    if desc:
                        protocols.append(f"{day} ({title}): {desc}")
            
            entry = {
                "crop": prof["crop"],
                "disease": prof["disease"],
                "pathogen": prof["scientific_name"],
                "treatments": protocols if protocols else ["Consult integrated pest management guidelines."],
                "stages": prof["stages"]
            }
            self.diseases_list.append(entry)

        # Fallback from kissan_cv/knowledge_base.csv if not present in v2
        kb_path = DATA_DIR / "kissan_cv" / "knowledge_base.csv"
        if kb_path.exists():
            df_kb = pd.read_csv(kb_path)
            for _, r in df_kb.iterrows():
                crop = str(r.get("item_name", "")).strip().title()
                disease = str(r.get("disease_name", "")).strip()
                if not crop or not disease or crop == "Nan" or disease == "Nan":
                    continue
                canonical_crop = self.normalize_crop_name(crop)
                prof_key = (canonical_crop.lower(), disease.lower())
                if prof_key not in self.disease_profiles:
                    trt = str(r.get("treatment", "")).strip()
                    sci = str(r.get("scientific_name", "")).strip()
                    entry = {
                        "crop": canonical_crop,
                        "disease": disease,
                        "pathogen": sci if sci != "Nan" else "",
                        "treatments": [trt] if trt and trt != "Nan" else [],
                        "stages": []
                    }
                    self.disease_profiles[prof_key] = {
                        "crop": canonical_crop,
                        "disease": disease,
                        "scientific_name": entry["pathogen"],
                        "stages": []
                    }
                    self.diseases_list.append(entry)

    def _load_pincode_data(self):
        # 1. Pincode to Agro-Climatic Zone (crop_recommendation/pincode_zone_mappings.csv)
        pzm_path = DATA_DIR / "crop_recommendation" / "pincode_zone_mappings.csv"
        if pzm_path.exists():
            df = pd.read_csv(pzm_path)
            for _, r in df.iterrows():
                pin = str(r.get("pincode", "")).strip()
                zone = int(r.get("zone", 0)) if pd.notna(r.get("zone")) else 0
                if pin and zone:
                    self.pincode_to_zone[pin] = zone

        # 2. Season Advisor Pincode Groundwater & Reservoir Status (kissan_agro_prod/season_advisor_pincode.csv)
        sa_path = DATA_DIR / "kissan_agro_prod" / "season_advisor_pincode.csv"
        if sa_path.exists():
            df = pd.read_csv(sa_path)
            for _, r in df.iterrows():
                pin = str(r.get("pincode", "")).strip()
                if not pin:
                    continue
                grow_raw = str(r.get("crops_to_grow", "")) if pd.notna(r.get("crops_to_grow")) else ""
                avoid_raw = str(r.get("crops_to_avoid", "")) if pd.notna(r.get("crops_to_avoid")) else ""
                
                crops_to_grow = [c.strip() for c in grow_raw.split(",") if c.strip()]
                crops_to_avoid = [c.strip() for c in avoid_raw.split(",") if c.strip()]

                self.pincode_season_outlook[pin] = {
                    "pincode": pin,
                    "district": str(r.get("district", "")),
                    "water_outlook_tag": str(r.get("water_outlook_tag", "Normal")),
                    "water_outlook_subtext": str(r.get("water_outlook_subtext", "")),
                    "reservoir_level_current": str(r.get("reservoir_level_current", "")),
                    "monsoon_forecast_vs_last_year": str(r.get("monsoon_forecast_vs_last_year", "")),
                    "water_risk": str(r.get("water_risk", "")),
                    "crops_to_grow": crops_to_grow,
                    "crops_to_avoid": crops_to_avoid,
                    "what_this_means_titles": str(r.get("what_this_means_titles", "")),
                    "what_this_means_details": str(r.get("what_this_means_details", ""))
                }

    def _load_recommendation_models(self):
        # 1. Zone scores
        p = DATA_DIR / "crop_recommendation" / "crop_zone_scores.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                uid = str(r.get("crop_uid", "")).strip()
                z = int(r.get("zone", 0)) if pd.notna(r.get("zone")) else 0
                sc = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                if uid not in self.zone_scores:
                    self.zone_scores[uid] = {}
                self.zone_scores[uid][z] = sc

        # 2. Season scores
        p = DATA_DIR / "crop_recommendation" / "crop_season_scores.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                uid = str(r.get("crop_uid", "")).strip()
                s = str(r.get("season", "")).strip().upper()
                sc = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                if uid not in self.season_scores:
                    self.season_scores[uid] = {}
                self.season_scores[uid][s] = sc

        # 3. Water method scores
        p = DATA_DIR / "crop_recommendation" / "crop_water_scores.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                uid = str(r.get("crop_uid", "")).strip()
                w = str(r.get("method", "")).strip().upper()
                sc = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                if uid not in self.water_scores:
                    self.water_scores[uid] = {}
                self.water_scores[uid][w] = sc

        # 4. Soil class scores
        p = DATA_DIR / "crop_recommendation" / "crop_soil_scores.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                uid = str(r.get("crop_uid", "")).strip()
                sc_id = int(r.get("soil_class", 0)) if pd.notna(r.get("soil_class")) else 0
                score = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                if uid not in self.soil_scores:
                    self.soil_scores[uid] = {}
                self.soil_scores[uid][sc_id] = score

        # 5. Budget rules
        p = DATA_DIR / "crop_recommendation" / "budget_rules.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                bucket = str(r.get("budget_bucket", "")).strip().upper()
                cost = str(r.get("cost_class", "")).strip().upper()
                sc = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                if bucket not in self.budget_rules:
                    self.budget_rules[bucket] = {}
                self.budget_rules[bucket][cost] = sc

        # 6. Rotation rules
        p = DATA_DIR / "crop_recommendation" / "rotation_rules.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                sit = str(r.get("situation", "")).strip().upper()
                sc = float(r.get("score", 0)) if pd.notna(r.get("score")) else 0.0
                self.rotation_rules[sit] = sc

        # 7. Scoring weights
        p = DATA_DIR / "crop_recommendation" / "scoring_weights.csv"
        if p.exists():
            df = pd.read_csv(p)
            for _, r in df.iterrows():
                factor = str(r.get("factor", "")).strip().upper()
                wt = float(r.get("weight", 1.0)) if pd.notna(r.get("weight")) else 1.0
                self.scoring_weights[factor] = wt

    def _load_weather_rules(self):
        wr_path = DATA_DIR / "kissan_agro_prod" / "weather_advisory_rules.csv"
        if wr_path.exists():
            df = pd.read_csv(wr_path)
            for _, r in df.iterrows():
                self.weather_rules.append({
                    "temp_level": str(r.get("temp_level", "")).strip(),
                    "moisture": str(r.get("moisture", "")).strip(),
                    "wind_risk": str(r.get("wind_risk", "")).strip(),
                    "rain_status": str(r.get("rain_status", "")).strip(),
                    "advisory_type": str(r.get("advisory_type", "")).strip(),
                    "status": str(r.get("status", "")).strip(),
                    "severity_score": int(r.get("severity_score", 1)) if pd.notna(r.get("severity_score")) else 1,
                    "title": str(r.get("title", "")).strip(),
                    "message_en": str(r.get("message_en", r.get("status", ""))).strip(),
                    "time_window": str(r.get("time_window", "")).strip(),
                    "icon_type": str(r.get("icon_type", "")).strip()
                })

    # =========================================================================
    # CORE GRAPH QUERY & REASONING METHODS
    # =========================================================================

    def normalize_crop_name(self, name: Optional[str]) -> str:
        if not name:
            return ""
        name_clean = name.strip().lower()
        if name_clean in self.crop_aliases:
            return self.crop_aliases[name_clean]
        for alias, canonical in self.crop_aliases.items():
            if alias in name_clean or name_clean in alias:
                return canonical
        return name.strip().title()

    def get_crops(self, limit: Optional[int] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self.crops.values())
        if search:
            s_low = search.strip().lower()
            results = [c for c in results if s_low in c["name"].lower() or s_low in c.get("name_hin", "").lower()]
        if limit:
            results = results[:limit]
        return results

    def get_crop_profile(self, name: str) -> Optional[Dict[str, Any]]:
        canonical = self.normalize_crop_name(name)
        k = canonical.lower()
        crop_data = self.crops.get(k)
        if not crop_data:
            # Fallback search
            for ck, cv in self.crops.items():
                if k in ck or ck in k:
                    crop_data = cv
                    k = ck
                    break
        if not crop_data:
            return None

        result = dict(crop_data)
        result["stages"] = self.crop_phenology.get(k, [])
        return result

    def search_diseases(
        self, 
        crop_name: Optional[str], 
        symptom: str, 
        stage_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        sym_lower = (symptom or "").strip().lower()
        canonical_crop = self.normalize_crop_name(crop_name) if crop_name else ""
        crop_lower = canonical_crop.lower() if canonical_crop else ""
        
        sym_tokens = [w.strip(" ,.!?") for w in sym_lower.split() if len(w.strip(" ,.!?")) > 2]
        
        scored_matches = []
        for d in self.diseases_list:
            d_crop = d["crop"].lower()
            d_name = d["disease"].lower()
            d_sci = d.get("pathogen", "").lower()
            d_trt = " ".join(d.get("treatments", [])).lower()
            
            # Crop match check
            crop_match = False
            crop_score = 0
            if not crop_lower:
                crop_match = True
                crop_score = 10
            elif (crop_lower in d_crop) or (d_crop in crop_lower):
                crop_match = True
                crop_score = 120
            elif any(w in d_crop for w in crop_lower.replace("(", " ").replace(")", " ").split() if len(w) > 2):
                crop_match = True
                crop_score = 80

            sym_score = 0
            if not sym_lower:
                sym_score = 50
            else:
                # Exact disease match
                if sym_lower == d_name:
                    sym_score += 250
                elif sym_lower in d_name:
                    sym_score += 180
                elif all(t in d_name for t in sym_tokens) and sym_tokens:
                    sym_score += 140
                elif any(t in d_name for t in sym_tokens):
                    matched_cnt = sum(1 for t in sym_tokens if t in d_name)
                    sym_score += 40 * matched_cnt
                    
                # Pathogen name match (e.g. Fusarium, Alternaria, Pyricularia)
                if sym_lower in d_sci:
                    sym_score += 80
                elif any(t in d_sci for t in sym_tokens):
                    sym_score += 30

                # Treatment text matches
                if sym_lower in d_trt:
                    sym_score += 30
                elif any(t in d_trt for t in sym_tokens):
                    sym_score += 15

            if crop_match and sym_score > 0:
                total_score = crop_score + sym_score
                scored_matches.append((total_score, d))
            elif not crop_match and sym_score >= 140:
                # Strong symptom match even if crop was unspecified
                scored_matches.append((sym_score, d))

        scored_matches.sort(key=lambda x: x[0], reverse=True)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for _, item in scored_matches:
            key = (item["crop"], item["disease"])
            if key not in seen:
                seen.add(key)
                
                # Pick active stage if stage_name specified or default to first actionable stage
                item_copy = dict(item)
                stages = item_copy.get("stages", [])
                active_stage = None
                if stages:
                    if stage_name:
                        for s in stages:
                            if stage_name.lower() in s["stage_name"].lower():
                                active_stage = s
                                break
                    if not active_stage:
                        # Prefer stage with treatment steps (stage_number > 1)
                        actionable = [s for s in stages if s.get("treatment_steps")]
                        active_stage = actionable[0] if actionable else stages[0]
                item_copy["active_stage"] = active_stage
                unique_results.append(item_copy)
                if len(unique_results) >= 15:
                    break

        return unique_results

    def get_pincode_outlook(self, pincode: str) -> Optional[Dict[str, Any]]:
        clean_pin = str(pincode).strip()
        return self.pincode_season_outlook.get(clean_pin)

    def calculate_6factor_recommendations(
        self,
        pincode: str,
        season: Optional[str] = None,
        soil_class: Optional[int] = None,
        water_method: Optional[str] = None,
        budget_bucket: Optional[str] = None,
        previous_crop: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        clean_pin = str(pincode).strip()
        zone_id = self.pincode_to_zone.get(clean_pin, 3) # default zone 3 (Trans-Gangetic Plains) if unknown
        pincode_outlook = self.pincode_season_outlook.get(clean_pin)

        # Standardize inputs
        target_season = season.upper().strip() if season else "KHARIF"
        target_water = water_method.upper().strip() if water_method else "RAINFED"
        target_budget = budget_bucket.upper().strip() if budget_bucket else "B2"
        target_soil = int(soil_class) if soil_class else 2 # default black soil

        prev_family = ""
        if previous_crop:
            prev_canonical = self.normalize_crop_name(previous_crop).lower()
            prev_uid = self.crop_name_to_uid.get(prev_canonical)
            if prev_uid and prev_uid in self.rec_crops:
                prev_family = self.rec_crops[prev_uid].get("family", "").upper()

        w_zone = self.scoring_weights.get("ZONE", 2.0)
        w_season = self.scoring_weights.get("SEASON", 2.0)
        w_water = self.scoring_weights.get("WATER", 2.0)
        w_soil = self.scoring_weights.get("SOIL", 1.5)
        w_budget = self.scoring_weights.get("BUDGET", 1.5)
        w_rotation = self.scoring_weights.get("ROTATION", 1.0)
        max_possible_weighted = 2.0 * (w_zone + w_season + w_water + w_soil + w_budget + w_rotation) # 20.0

        recommendations = []
        for uid, crop_meta in self.rec_crops.items():
            crop_name = crop_meta["name"]
            crop_family = crop_meta.get("family", "").upper()
            cost_class = crop_meta.get("cost_class", "MEDIUM").upper()

            # 1. Zone score (0 to 2)
            z_score = self.zone_scores.get(uid, {}).get(zone_id, 0.0)

            # 2. Season score (0 to 2)
            s_score = self.season_scores.get(uid, {}).get(target_season, 1.0)

            # 3. Water method score (0 to 2)
            w_score = self.water_scores.get(uid, {}).get(target_water, 1.0)

            # 4. Soil class score (0 to 2)
            sl_score = self.soil_scores.get(uid, {}).get(target_soil, 1.0)

            # 5. Budget score (0 to 2)
            b_score = self.budget_rules.get(target_budget, {}).get(cost_class, 1.0)

            # 6. Rotation score (0 to 2)
            rot_score = 1.0
            if previous_crop:
                if previous_crop.lower() in ("fallow", "none", "no crop"):
                    rot_score = self.rotation_rules.get("FALLOW", 1.0)
                elif prev_family and crop_family and prev_family == crop_family:
                    rot_score = self.rotation_rules.get("SAME_FAMILY", 0.0)
                else:
                    rot_score = self.rotation_rules.get("DIFFERENT_FAMILY", 2.0)

            # Calculate total weighted score
            weighted_total = (
                (z_score * w_zone) +
                (s_score * w_season) +
                (w_score * w_water) +
                (sl_score * w_soil) +
                (b_score * w_budget) +
                (rot_score * w_rotation)
            )
            match_pct = (weighted_total / max_possible_weighted) * 100.0

            # Pincode Groundwater Cross-Reference
            water_warning = None
            if pincode_outlook:
                crops_to_grow_str = " ".join(pincode_outlook.get("crops_to_grow", [])).lower()
                crops_to_avoid_str = " ".join(pincode_outlook.get("crops_to_avoid", [])).lower()
                c_low = crop_name.lower()

                if c_low in crops_to_avoid_str:
                    water_warning = f"High Risk: Groundwater / reservoir levels in {pincode_outlook.get('district')} are restricted for this high-water crop."
                    match_pct = max(0.0, match_pct - 15.0) # Penalty for restricted water crops
                elif c_low in crops_to_grow_str:
                    water_warning = f"Recommended: Endorsed by district water management for {pincode_outlook.get('district')}."
                    match_pct = min(100.0, match_pct + 5.0)

            recommendations.append({
                "crop": crop_name,
                "category": crop_meta.get("category", "Field Crop"),
                "family": crop_meta.get("family", ""),
                "zone_id": zone_id,
                "zone_score": z_score,
                "season_score": s_score,
                "water_score": w_score,
                "soil_score": sl_score,
                "budget_score": b_score,
                "rotation_score": rot_score,
                "total_score": round(weighted_total, 2),
                "match_percentage": round(match_pct, 1),
                "combined_score": round(match_pct / 100.0, 3), # for backward compatibility
                "water_outlook_warning": water_warning
            })

        recommendations.sort(key=lambda x: x["match_percentage"], reverse=True)
        return recommendations[:limit]

    def get_weather_advisories(
        self, 
        temp: Optional[str] = None, 
        moist: Optional[str] = None, 
        rain: Optional[str] = None,
        wind: Optional[str] = None,
        advisory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        for r in self.weather_rules:
            t_m = (not temp) or (temp.lower() in r["temp_level"].lower())
            m_m = (not moist) or (moist.lower() in r["moisture"].lower())
            r_m = (not rain) or (rain.lower() in r["rain_status"].lower())
            w_m = (not wind) or (wind.lower() in r["wind_risk"].lower())
            a_m = (not advisory_type) or (advisory_type.lower() in r["advisory_type"].lower())
            
            if t_m and m_m and r_m and w_m and a_m:
                results.append(r)
        return results

_embedded_graph = None

def get_embedded_graph() -> EmbeddedAgriGraph:
    global _embedded_graph
    if _embedded_graph is None:
        _embedded_graph = EmbeddedAgriGraph()
    return _embedded_graph
