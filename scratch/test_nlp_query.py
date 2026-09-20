import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Restart check
r_health = requests.get("http://127.0.0.1:8000/")
print("Health:", r_health.json())

# NLP Query
query = """
query {
  askCopilot(query: "give treatment plan for cotton crop and leaf blight disease") {
    intent
    crop
    symptoms
    diagnosis
    confidenceScore
    treatments {
      disease
      protocol
    }
    preventiveActions
    advisory
  }
}
"""

print("\n--- Testing Conversational NLP Interaction ---")
response = requests.post("http://127.0.0.1:8000/graphql", json={"query": query})
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
