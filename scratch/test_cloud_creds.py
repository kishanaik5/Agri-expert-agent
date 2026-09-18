import os
import sys
import pika
from neo4j import GraphDatabase
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

def test_cloudamqp():
    url = os.getenv("CLOUDAMQP_URL")
    print("=" * 60)
    print("Testing CloudAMQP connection...")
    print("URL:", url.split("@")[-1] if url else "None")
    print("=" * 60)
    try:
        params = pika.URLParameters(url)
        params.socket_timeout = 10
        conn = pika.BlockingConnection(params)
        channel = conn.channel()
        channel.queue_declare(queue="test_cloud_queue", durable=False)
        print(" Connected to CloudAMQP successfully!")
        conn.close()
    except Exception as e:
        print("❌ CloudAMQP Error:", e)

def test_neo4j_aura():
    uri = os.getenv("NEO4J_URI", "neo4j+s://6c8a60f9.databases.neo4j.io")
    password = os.getenv("NEO4J_PASSWORD")
    
    print("\n" + "=" * 60)
    print(f"Testing Neo4j AuraDB: {uri}")
    print("=" * 60)
    
    # Try with 'neo4j' user first, then '6c8a60f9'
    for user in ["neo4j", "6c8a60f9"]:
        print(f"Trying user '{user}'...")
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            with driver.session() as session:
                res = session.run("RETURN 'Connected to Neo4j AuraDB!' AS msg").single()
                print(f" Success with user '{user}':", res["msg"])
                driver.close()
                return user
        except Exception as e:
            print(f"❌ Failed with user '{user}':", e)
    return None

if __name__ == "__main__":
    test_cloudamqp()
    test_neo4j_aura()
