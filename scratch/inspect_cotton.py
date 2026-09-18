from src.graph.client import get_graph_client
import sys

sys.stdout.reconfigure(encoding='utf-8')
c = get_graph_client()
res = c.query('MATCH (c:Crop)-[:PRONE_TO]->(d:Disease) WHERE toLower(c.name) CONTAINS "cotton" OPTIONAL MATCH (d)-[:CAUSED_BY]->(p:Pathogen) RETURN c.name AS crop, d.name AS disease, p.name AS pathogen')
for r in res:
    print(r)
