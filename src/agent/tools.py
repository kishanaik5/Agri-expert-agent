from typing import List, Dict, Any, Optional
from src.graph.client import get_graph_client
from src.graph.embedded_graph import get_embedded_graph

def get_crop_profile(crop_name: str) -> Optional[Dict[str, Any]]:
    client = get_graph_client()
    if client.verify_connectivity():
        cypher = """
        MATCH (c:Crop)
        WHERE toLower(c.name) = toLower($crop_name) 
           OR toLower(c.name_hin) = toLower($crop_name)
        OPTIONAL MATCH (c)-[:HAS_STAGE]->(s:CropStage)
        WITH c, collect({
            main_stage: s.main_stage, 
            sub_stage: s.sub_stage, 
            start_day: s.start_day, 
            end_day: s.end_day
        }) AS stages
        RETURN c.name AS name,
               c.name_hin AS name_hin,
               c.category AS category,
               stages
        LIMIT 1
        """
        results = client.query(cypher, {"crop_name": crop_name})
        return results[0] if results else None
    else:
        return get_embedded_graph().get_crop_profile(crop_name)

def search_disease_and_treatments(crop_name: Optional[str], symptom_or_disease: str) -> List[Dict[str, Any]]:
    client = get_graph_client()
    if client.verify_connectivity():
        # Tokenize keywords
        words = [w.strip(" ,.!?") for w in (symptom_or_disease or "").split() if len(w.strip(" ,.!?")) > 2]
        regex_pattern = "(?i).*(" + "|".join(words) + ").*" if words else ".*"
        
        if crop_name:
            cypher = """
            MATCH (c:Crop)-[:PRONE_TO]->(d:Disease)
            WHERE (toLower(c.name) = toLower($crop_name) OR toLower(c.name_hin) = toLower($crop_name))
              AND (d.name =~ $pattern OR $pattern = '.*')
            OPTIONAL MATCH (d)-[:CAUSED_BY]->(p:Pathogen)
            OPTIONAL MATCH (d)-[:TREATED_BY]->(t:Treatment)
            RETURN c.name AS crop,
                   d.name AS disease,
                   p.name AS pathogen,
                   collect(DISTINCT t.name) AS treatments
            LIMIT 10
            """
            return client.query(cypher, {"crop_name": crop_name, "pattern": regex_pattern})
        else:
            cypher = """
            MATCH (c:Crop)-[:PRONE_TO]->(d:Disease)
            WHERE d.name =~ $pattern
            OPTIONAL MATCH (d)-[:CAUSED_BY]->(p:Pathogen)
            OPTIONAL MATCH (d)-[:TREATED_BY]->(t:Treatment)
            RETURN c.name AS crop,
                   d.name AS disease,
                   p.name AS pathogen,
                   collect(DISTINCT t.name) AS treatments
            LIMIT 10
            """
            return client.query(cypher, {"pattern": regex_pattern})
    else:
        return get_embedded_graph().search_diseases(crop_name, symptom_or_disease)

def get_zone_suitability_by_pincode(pincode: str, soil_class: Optional[int] = None) -> List[Dict[str, Any]]:
    client = get_graph_client()
    if client.verify_connectivity():
        if soil_class:
            cypher = """
            MATCH (pin:Pincode {code: $pincode})-[:IN_ZONE]->(z:AgroZone)<-[rz:SUITED_FOR_ZONE]-(c:Crop)-[rs:SUITED_FOR_SOIL]->(s:SoilType {soil_class: $soil_class})
            RETURN c.name AS crop,
                   c.category AS category,
                   z.zone_id AS zone_id,
                   rz.score AS zone_score,
                   rs.score AS soil_score,
                   (rz.score + rs.score) / 2.0 AS combined_score
            ORDER BY combined_score DESC
            LIMIT 10
            """
            results = client.query(cypher, {"pincode": str(pincode), "soil_class": int(soil_class)})
            if not results:
                # Fallback without soil restriction if exact soil score wasn't rated
                cypher_fallback = """
                MATCH (pin:Pincode {code: $pincode})-[:IN_ZONE]->(z:AgroZone)<-[rz:SUITED_FOR_ZONE]-(c:Crop)
                RETURN c.name AS crop,
                       c.category AS category,
                       z.zone_id AS zone_id,
                       rz.score AS zone_score,
                       rz.score AS combined_score
                ORDER BY combined_score DESC
                LIMIT 10
                """
                results = client.query(cypher_fallback, {"pincode": str(pincode)})
            return results
        else:
            cypher = """
            MATCH (pin:Pincode {code: $pincode})-[:IN_ZONE]->(z:AgroZone)<-[rz:SUITED_FOR_ZONE]-(c:Crop)
            RETURN c.name AS crop,
                   c.category AS category,
                   z.zone_id AS zone_id,
                   rz.score AS zone_score,
                   rz.score AS combined_score
            ORDER BY combined_score DESC
            LIMIT 10
            """
            return client.query(cypher, {"pincode": str(pincode)})
    else:
        return get_embedded_graph().get_zone_recommendations(pincode, soil_class)

def get_weather_advisories(temp_level: Optional[str] = None, moisture: Optional[str] = None, rain_status: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_graph_client()
    if client.verify_connectivity():
        cypher = """
        MATCH (r:WeatherRule)
        WHERE (toLower(r.temp_level) = toLower($temp) OR $temp = '' OR $temp IS NULL)
          AND (toLower(r.moisture) = toLower($moist) OR $moist = '' OR $moist IS NULL)
          AND (toLower(r.rain_status) = toLower($rain) OR $rain = '' OR $rain IS NULL)
        RETURN r.advisory_type AS advisory_type,
               r.advisory AS advisory,
               r.temp_level AS temp_level,
               r.moisture AS moisture,
               r.rain_status AS rain_status
        LIMIT 5
        """
        return client.query(cypher, {
            "temp": temp_level or "",
            "moist": moisture or "",
            "rain": rain_status or ""
        })
    else:
        return get_embedded_graph().get_weather_advisories(temp_level, moisture, rain_status)
