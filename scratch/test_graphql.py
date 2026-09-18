import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

GRAPHQL_URL = "http://127.0.0.1:8000/graphql"

def run_query(name, query, variables=None):
    print("=" * 60)
    print(f"Executing GraphQL: {name}")
    print("=" * 60)
    response = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables or {}},
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    res_data = response.json()
    print(json.dumps(res_data, indent=2, ensure_ascii=False))
    return res_data

def main():
    # 1. Query Crops
    q1 = """
    query {
      crops(limit: 5) {
        name
        nameHin
        category
      }
    }
    """
    run_query("List Crops", q1)

    # 2. Query Crop Details & Growth Stages
    q2 = """
    query {
      cropDetails(name: "Wheat") {
        name
        category
        stages {
          mainStage
          subStage
          startDay
          endDay
        }
      }
    }
    """
    run_query("Crop Details & Growth Stages", q2)

    # 3. Query Diseases & Treatments
    q3 = """
    query {
      diseases(cropName: "Wheat", symptom: "Rust") {
        crop
        disease
        pathogen
        treatments
      }
    }
    """
    run_query("Crop Diseases & Treatments", q3)

    # 4. Query Regional Zone Recommendations by PIN Code
    q4 = """
    query {
      zoneRecommendations(pincode: "141004", soilClass: 2) {
        crop
        category
        zoneId
        combinedScore
      }
    }
    """
    run_query("Zone Recommendations for PIN 141004", q4)

    # 5. Mutation: Submit Diagnostic Task (Async Queue)
    m1 = """
    mutation {
      submitDiagnosticTask(
        cropName: "Wheat",
        symptoms: "Yellow patches on leaves and powdery stripe rust",
        pincode: "141004",
        soilClass: 2
      ) {
        taskId
        status
        message
      }
    }
    """
    res_m1 = run_query("Submit Diagnostic Task Mutation", m1)
    task_id = res_m1.get("data", {}).get("submitDiagnosticTask", {}).get("taskId")

    # 6. Query Task Status by Task ID
    if task_id:
        q5 = f"""
        query {{
          taskStatus(taskId: "{task_id}") {{
            taskId
            status
            result {{
              confidenceScore
              diagnosisSummary
              preventiveActions
              treatmentProtocols {{
                disease
                protocol
                type
              }}
              actionableAdvisory
            }}
          }}
        }}
        """
        run_query(f"Check Task Status ({task_id})", q5)

    # 7. Mutation: Instant Advisory (Synchronous LangGraph)
    m2 = """
    mutation {
      instantAdvisory(
        cropName: "Soybean",
        symptoms: "Stem rot and wilt",
        pincode: "452001"
      ) {
        confidenceScore
        diagnosisSummary
        treatmentProtocols {
          disease
          protocol
        }
        actionableAdvisory
      }
    }
    """
    run_query("Instant Advisory Mutation", m2)

if __name__ == "__main__":
    main()
