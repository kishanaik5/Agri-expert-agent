from src.graph.client import get_graph_client

CONSTRAINTS_AND_INDEXES = [
    # Node Unique Constraints
    "CREATE CONSTRAINT crop_name_unique IF NOT EXISTS FOR (c:Crop) REQUIRE c.name IS UNIQUE;",
    "CREATE CONSTRAINT disease_name_unique IF NOT EXISTS FOR (d:Disease) REQUIRE d.name IS UNIQUE;",
    "CREATE CONSTRAINT pathogen_name_unique IF NOT EXISTS FOR (p:Pathogen) REQUIRE p.name IS UNIQUE;",
    "CREATE CONSTRAINT stage_unique IF NOT EXISTS FOR (s:CropStage) REQUIRE s.stage_id IS UNIQUE;",
    "CREATE CONSTRAINT zone_id_unique IF NOT EXISTS FOR (z:AgroZone) REQUIRE z.zone_id IS UNIQUE;",
    "CREATE CONSTRAINT soil_class_unique IF NOT EXISTS FOR (s:SoilType) REQUIRE s.soil_class IS UNIQUE;",
    "CREATE CONSTRAINT pincode_unique IF NOT EXISTS FOR (p:Pincode) REQUIRE p.code IS UNIQUE;",
    "CREATE CONSTRAINT treatment_name_unique IF NOT EXISTS FOR (t:Treatment) REQUIRE t.name IS UNIQUE;",

    # Fulltext & Performance Indexes
    "CREATE INDEX crop_names_idx IF NOT EXISTS FOR (c:Crop) ON (c.name, c.name_hin);",
    "CREATE INDEX disease_names_idx IF NOT EXISTS FOR (d:Disease) ON (d.name);",
    "CREATE INDEX pincode_code_idx IF NOT EXISTS FOR (p:Pincode) ON (p.code);"
]

def apply_schema():
    client = get_graph_client()
    print("Applying Neo4j Schema Constraints and Indexes...")
    for statement in CONSTRAINTS_AND_INDEXES:
        try:
            client.query(statement)
            print(f"  Applied: {statement.split()[1]} {statement.split()[2]}")
        except Exception as e:
            print(f"  Error applying '{statement[:30]}...': {e}")
    print(" Neo4j Schema configured successfully.")

if __name__ == "__main__":
    apply_schema()
