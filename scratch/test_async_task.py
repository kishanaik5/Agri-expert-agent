import requests
import time
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

mutation = """
mutation {
  submitDiagnosticTask(
    cropName: "Cotton",
    symptoms: "Boll rot and leaf curl",
    pincode: "141004"
  ) {
    taskId
    status
    message
  }
}
"""

print("Submitting diagnostic task to RabbitMQ...")
r = requests.post("http://127.0.0.1:8000/graphql", json={"query": mutation})
print(json.dumps(r.json(), indent=2))
task_id = r.json()["data"]["submitDiagnosticTask"]["taskId"]

time.sleep(1)

query = f"""
query {{
  taskStatus(taskId: "{task_id}") {{
    taskId
    status
    result {{
      confidenceScore
      diagnosisSummary
      treatmentProtocols {{
        disease
        protocol
      }}
      actionableAdvisory
    }}
  }}
}}
"""

print(f"\nChecking task status for {task_id}...")
r2 = requests.post("http://127.0.0.1:8000/graphql", json={"query": query})
print(json.dumps(r2.json(), indent=2, ensure_ascii=False))
