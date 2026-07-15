"""
Neo4j Connection Manager
========================
Thread-safe singleton wrapper around the official Neo4j Python driver.
Provides connection pooling, query execution helpers, and graceful fallback
when Neo4j is unavailable (logs warnings instead of crashing the application).
"""
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("app.database.neo4j_connection")


class Neo4jConnection:
    """
    Manages a single Neo4j driver instance with connection pooling.
    Use as a singleton via get_neo4j_connection().
    """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database
        self._driver = None
        self._available = False

    def connect(self) -> bool:
        """
        Attempt to establish a connection to Neo4j.
        Returns True if successful, False if Neo4j is unavailable.
        """
        try:
            import neo4j
            self._driver = neo4j.GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            self._available = True
            logger.info(f"Connected to Neo4j at {self._uri}")
            return True
        except Exception as e:
            self._available = False
            logger.warning(
                f"Neo4j is not available at {self._uri}: {str(e)}. "
                f"Graph operations will be skipped."
            )
            return False

    @property
    def is_available(self) -> bool:
        """Check if Neo4j connection is active."""
        return self._available and self._driver is not None

    def close(self):
        """Close the driver and release all connections."""
        if self._driver:
            try:
                self._driver.close()
                logger.info("Neo4j connection closed.")
            except Exception as e:
                logger.warning(f"Error closing Neo4j connection: {str(e)}")
            finally:
                self._driver = None
                self._available = False

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query and return results as a list of dicts.

        Args:
            query:      Cypher query string.
            parameters: Query parameters.

        Returns:
            List of record dictionaries.
        """
        if not self.is_available:
            logger.warning("Neo4j not available. Skipping read query.")
            return []

        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(query, parameters or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Neo4j read query failed: {str(e)}")
            raise

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a write query inside a transaction.

        Args:
            query:      Cypher query string.
            parameters: Query parameters.

        Returns:
            Summary dict with counters, or None on failure.
        """
        if not self.is_available:
            logger.warning("Neo4j not available. Skipping write query.")
            return None

        try:
            with self._driver.session(database=self._database) as session:
                result = session.run(query, parameters or {})
                summary = result.consume()
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }
        except Exception as e:
            logger.error(f"Neo4j write query failed: {str(e)}")
            raise

    def execute_write_batch(
        self,
        queries: List[Dict[str, Any]],
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Execute multiple write queries in a single session.

        Args:
            queries: List of dicts with 'query' and optional 'parameters' keys.

        Returns:
            List of summary dicts.
        """
        if not self.is_available:
            logger.warning("Neo4j not available. Skipping batch write.")
            return []

        results = []
        try:
            with self._driver.session(database=self._database) as session:
                for q in queries:
                    result = session.run(
                        q["query"], q.get("parameters", {})
                    )
                    summary = result.consume()
                    results.append({
                        "nodes_created": summary.counters.nodes_created,
                        "relationships_created": summary.counters.relationships_created,
                    })
        except Exception as e:
            logger.error(f"Neo4j batch write failed: {str(e)}")
            raise

        return results


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
_neo4j_instance: Optional[Neo4jConnection] = None


def get_neo4j_connection() -> Neo4jConnection:
    """
    Get or create the singleton Neo4j connection instance.
    Uses settings from app config.
    """
    global _neo4j_instance
    if _neo4j_instance is None:
        from app.config import settings
        _neo4j_instance = Neo4jConnection(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE,
        )
        _neo4j_instance.connect()
    return _neo4j_instance


def close_neo4j_connection():
    """Close the singleton Neo4j connection."""
    global _neo4j_instance
    if _neo4j_instance:
        _neo4j_instance.close()
        _neo4j_instance = None
