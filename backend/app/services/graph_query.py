import uuid
import logging
from typing import Dict, List, Any, Optional
from app.database.neo4j_connection import get_neo4j_connection

logger = logging.getLogger("app.services.graph_query")

class GraphQueryService:
    """
    Read-only query service for traversing and analyzing the Neo4j knowledge graph.
    """

    @staticmethod
    def get_entity_dependencies(entity_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retrieves direct inbound and outbound dependencies for a given entity.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"error": "Neo4j is not available"}

        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[out]->(target:Entity)
        OPTIONAL MATCH (source:Entity)-[in]->(e)
        RETURN e {.*, labels: labels(e)} AS entity,
               collect(distinct {
                   relationship: type(out),
                   target: target {.*, labels: labels(target)}
               }) AS dependencies_out,
               collect(distinct {
                   relationship: type(in),
                   source: source {.*, labels: labels(source)}
               }) AS dependencies_in
        """
        results = neo4j_conn.execute_query(query, {"entity_id": str(entity_id)})
        if not results:
            return {"entity": None, "dependencies_out": [], "dependencies_in": []}

        # Filter out empty records (e.g. if target or source is null)
        record = results[0]
        deps_out = [d for d in record.get("dependencies_out", []) if d.get("target") is not None]
        deps_in = [d for d in record.get("dependencies_in", []) if d.get("source") is not None]

        return {
            "entity": record.get("entity"),
            "dependencies_out": deps_out,
            "dependencies_in": deps_in
        }

    @staticmethod
    def get_dependency_chain(entity_id: uuid.UUID, depth: int = 3) -> Dict[str, Any]:
        """
        Traverses downstream dependency paths up to the specified depth.
        Returns a flat list of nodes and relationships representing the subgraph.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"nodes": [], "edges": []}

        # Limit depth to avoid performance degradation
        clamped_depth = max(1, min(depth, 5))

        query = f"""
        MATCH path = (e:Entity {{id: $entity_id}})-[*1..{clamped_depth}]->(target:Entity)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        RETURN collect(distinct n {{.*, labels: labels(n)}}) AS nodes,
               collect(distinct {{
                   id: r.id,
                   source_id: startNode(r).id,
                   target_id: endNode(r).id,
                   type: type(r),
                   confidence: r.confidence,
                   source_file: r.source_file,
                   line_number: r.line_number
               }}) AS edges
        """
        results = neo4j_conn.execute_query(query, {"entity_id": str(entity_id)})
        if not results:
            # Try to return at least the starting node
            start_node_query = "MATCH (e:Entity {id: $entity_id}) RETURN e {.*, labels: labels(e)} AS node"
            start_node_res = neo4j_conn.execute_query(start_node_query, {"entity_id": str(entity_id)})
            if start_node_res:
                return {"nodes": [start_node_res[0]["node"]], "edges": []}
            return {"nodes": [], "edges": []}

        return {
            "nodes": results[0].get("nodes", []),
            "edges": results[0].get("edges", [])
        }

    @staticmethod
    def get_repository_graph_summary(repository_id: uuid.UUID) -> Dict[str, Any]:
        """
        Aggregates summary counts of graph nodes (grouped by label) and edges (grouped by type)
        for a specific repository.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"nodes_count": 0, "edges_count": 0, "nodes_by_label": {}, "edges_by_type": {}}

        # Query node counts by labels
        node_query = """
        MATCH (r:Repository {id: $repo_id})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e:Entity)
        WITH f, e
        UNWIND labels(e) AS label
        RETURN label, count(distinct e) AS count
        """
        node_results = neo4j_conn.execute_query(node_query, {"repo_id": str(repository_id)})

        nodes_by_label = {}
        total_nodes = 0
        for record in node_results:
            label = record.get("label")
            count = record.get("count", 0)
            if label:
                nodes_by_label[label] = count
                total_nodes += count

        # Query relationship counts by type
        edge_query = """
        MATCH (r:Repository {id: $repo_id})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e1:Entity)-[rel]->(e2:Entity)
        RETURN type(rel) AS type, count(rel) AS count
        """
        edge_results = neo4j_conn.execute_query(edge_query, {"repo_id": str(repository_id)})

        edges_by_type = {}
        total_edges = 0
        for record in edge_results:
            rel_type = record.get("type")
            count = record.get("count", 0)
            if rel_type:
                edges_by_type[rel_type] = count
                total_edges += count

        return {
            "repository_id": repository_id,
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_label": nodes_by_label,
            "edges_by_type": edges_by_type
        }

    @staticmethod
    def find_shortest_path(source_id: uuid.UUID, target_id: uuid.UUID) -> Dict[str, Any]:
        """
        Finds the shortest dependency path between two entities in the graph.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"path_found": False, "nodes": [], "edges": []}

        query = """
        MATCH (source:Entity {id: $source_id}), (target:Entity {id: $target_id})
        MATCH p = shortestPath((source)-[*..15]->(target))
        RETURN [n IN nodes(p) | n {.*, labels: labels(n)}] AS nodes,
               [r IN relationships(p) | {
                   id: r.id,
                   source_id: startNode(r).id,
                   target_id: endNode(r).id,
                   type: type(r)
               }] AS edges
        """
        results = neo4j_conn.execute_query(query, {
            "source_id": str(source_id),
            "target_id": str(target_id)
        })

        if not results or not results[0].get("nodes"):
            return {"path_found": False, "nodes": [], "edges": []}

        return {
            "path_found": True,
            "nodes": results[0].get("nodes", []),
            "edges": results[0].get("edges", [])
        }

    @staticmethod
    def detect_circular_dependencies(repository_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        Detects circular dependency cycles within the repository's entities.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return []

        # Find cycles: entity references itself via a chain of relationships.
        # We enforce repo scoping by matching the starting node.
        # id(a) = min(id(n)) filters out shift permutations of the same cycle.
        query = """
        MATCH (a:Entity)-[:DEFINED_IN]->(f:File)-[:BELONGS_TO]->(r:Repository {id: $repo_id})
        MATCH path = (a)-[:CALLS|IMPORTS|EXTENDS|IMPLEMENTS|USES*1..5]->(a)
        WITH path, nodes(path) AS cycle_nodes
        WHERE id(a) = min(id(cycle_nodes))
        RETURN [n IN cycle_nodes | n {.*, labels: labels(n)}] AS cycle
        """
        results = neo4j_conn.execute_query(query, {"repo_id": str(repository_id)})

        cycles = []
        for record in results:
            cycle = record.get("cycle", [])
            # Cycle node list starts and ends with the same node, we can filter or clean it
            if len(cycle) > 1:
                cycles.append({
                    "cycle_length": len(cycle) - 1,
                    "entities": cycle
                })
        return cycles
