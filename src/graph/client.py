import socket
from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional
from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

class Neo4jClient:
    _instance: Optional['Neo4jClient'] = None
    _driver: Optional[Driver] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Neo4jClient, cls).__new__(cls)
            cls._instance._init_driver()
        return cls._instance

    def _init_driver(self):
        self._driver = None

    def _is_port_open(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", 7687), timeout=0.2):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def verify_connectivity(self) -> bool:
        if not self._is_port_open():
            return False
        if not self._driver:
            try:
                self._driver = GraphDatabase.driver(
                    NEO4J_URI,
                    auth=(NEO4J_USER, NEO4J_PASSWORD),
                    connection_timeout=1.0,
                    max_connection_lifetime=3600,
                    max_connection_pool_size=50
                )
            except Exception:
                return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def close(self):
        if self._driver:
            self._driver.close()

    def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        parameters = parameters or {}
        if not self.verify_connectivity():
            return []
        with self._driver.session() as session:
            result = session.run(cypher, parameters)
            return [record.data() for record in result]

    def execute_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        parameters = parameters or {}
        if not self.verify_connectivity():
            return None
        with self._driver.session() as session:
            return session.execute_write(lambda tx: tx.run(cypher, parameters).consume())

def get_graph_client() -> Neo4jClient:
    return Neo4jClient()
