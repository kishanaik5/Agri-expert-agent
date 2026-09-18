import json
import time
import os
import pika
from typing import Dict, Any, Optional
from src.config import RABBITMQ_QUEUE_DIAGNOSTICS, DATA_DIR
from src.queue.broker import get_rabbitmq_connection, init_broker_topology
from src.agent.workflow import run_advisory_agent

# Local task result cache
TASK_RESULTS_DIR = DATA_DIR / "task_results"
TASK_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
_IN_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

def save_task_result(task_id: str, result: Dict[str, Any]):
    _IN_MEMORY_CACHE[task_id] = result
    file_path = TASK_RESULTS_DIR / f"{task_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    if task_id in _IN_MEMORY_CACHE:
        return _IN_MEMORY_CACHE[task_id]
    file_path = TASK_RESULTS_DIR / f"{task_id}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _IN_MEMORY_CACHE[task_id] = data
            return data
    return None

def process_task_message(ch, method, properties, body):
    try:
        data = json.loads(body.decode("utf-8"))
        task_id = data.get("task_id")
        payload = data.get("payload", {})
        
        print(f"\n[RabbitMQ Worker] Processing Task ID: {task_id}")
        print(f"  Input: Crop={payload.get('crop_name')}, Symptoms={payload.get('symptoms')}")
        
        # Save initial pending status
        save_task_result(task_id, {
            "task_id": task_id,
            "status": "PROCESSING",
            "timestamp": time.time(),
            "input": payload
        })
        
        # Run LangGraph reasoning
        result = run_advisory_agent(payload)
        
        # Save completed status
        final_result = {
            "task_id": task_id,
            "status": "COMPLETED",
            "timestamp": time.time(),
            "input": payload,
            "result": {
                "confidence_score": result.get("confidence_score", 0.0),
                "diagnosis_summary": result.get("diagnosis_summary", ""),
                "treatment_protocols": result.get("treatment_protocols", []),
                "preventive_actions": result.get("preventive_actions", []),
                "actionable_advisory": result.get("actionable_advisory", "")
            }
        }
        save_task_result(task_id, final_result)
        
        # Acknowledge RabbitMQ message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"  Task {task_id} completed and acknowledged!")
        
    except Exception as e:
        print(f"[Error] Failed processing task: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_worker():
    print("==================================================")
    print("[Worker] Starting Agri LangGraph RabbitMQ Consumer Worker")
    print("==================================================")
    
    while True:
        try:
            init_broker_topology()
            conn = get_rabbitmq_connection()
            if not conn:
                print("[Worker] RabbitMQ not reachable yet. Retrying in 5 seconds...")
                time.sleep(5)
                continue
                
            channel = conn.channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=RABBITMQ_QUEUE_DIAGNOSTICS,
                on_message_callback=process_task_message
            )
            
            print(f"[*] Waiting for messages in queue '{RABBITMQ_QUEUE_DIAGNOSTICS}'. To exit press CTRL+C")
            channel.start_consuming()
        except KeyboardInterrupt:
            print("\n[Worker] Stopping consumer worker...")
            break
        except Exception as e:
            print(f"[Worker] Connection lost or error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    start_worker()
