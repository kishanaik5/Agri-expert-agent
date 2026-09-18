import requests
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

query = """
query {
  disease(crop: "Cotton", symptoms: "Leaf Blight") {
    crop
    disease
    pathogen
    treatments
  }
}
"""

r = requests.post("http://127.0.0.1:8000/graphql", json={"query": query})
print(json.dumps(r.json(), indent=2, ensure_ascii=False))
