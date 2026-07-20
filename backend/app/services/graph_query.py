import uuid
import logging
from typing import Dict, List, Any, Optional
from app.database.neo4j_connection import get_neo4j_connection

logger = logging.getLogger("app.services.graph_query")


class GraphQueryService:
    """
    Read-only query service for traversing and analyzing the Neo4j knowledge graph.
    All methods return normalized dictionaries suitable for JSON serialization.
    """

    # -----------------------------------------------------------------
    # Existing methods (Sprint 4)
    # -----------------------------------------------------------------

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

    # -----------------------------------------------------------------
    # New methods (Sprint 5 — Graph Explorer)
    # -----------------------------------------------------------------

    @staticmethod
    def _normalize_node(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw Neo4j node map into a normalized GraphNode dict."""
        labels = raw.get("labels", [])
        # Determine the entity type from labels (prefer specific over generic)
        entity_type = "unknown"
        specific_labels = [l for l in labels if l not in ("Entity", "External")]
        if specific_labels:
            entity_type = specific_labels[0].lower()
        elif "External" in labels:
            entity_type = "external"
        elif "File" in labels:
            entity_type = "file"
        elif "Repository" in labels:
            entity_type = "repository"

        return {
            "id": raw.get("id", ""),
            "label": raw.get("name", ""),
            "name": raw.get("name", ""),
            "entity_type": entity_type,
            "fully_qualified_name": raw.get("fully_qualified_name", ""),
            "language": raw.get("language", ""),
            "file_path": raw.get("relative_path", ""),
            "start_line": raw.get("start_line"),
            "end_line": raw.get("end_line"),
            "visibility": raw.get("visibility", ""),
            "metadata": {
                k: v for k, v in raw.items()
                if k not in (
                    "id", "name", "fully_qualified_name", "language",
                    "relative_path", "start_line", "end_line", "visibility",
                    "labels",
                )
            },
        }

    @staticmethod
    def _normalize_edge(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a raw Neo4j relationship map into a normalized GraphEdge dict."""
        return {
            "id": raw.get("id", ""),
            "source": raw.get("source_id", ""),
            "target": raw.get("target_id", ""),
            "relationship_type": raw.get("type", ""),
            "confidence": raw.get("confidence", 1.0),
            "source_file": raw.get("source_file", ""),
            "line_number": raw.get("line_number", 0),
        }

    @staticmethod
    def get_repository_graph(
        repository_id: uuid.UUID,
        node_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Retrieve the full repository graph with pagination and optional filtering
        by node types and relationship types.
        Returns { nodes, edges, total_nodes, total_edges, has_more }.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"nodes": [], "edges": [], "total_nodes": 0, "total_edges": 0, "has_more": False}

        clamped_limit = max(1, min(limit, 500))
        clamped_offset = max(0, offset)

        # Build optional WHERE clause for node type filtering
        node_type_filter = ""
        if node_types:
            # Accept labels like "Class", "Method", etc.
            labels_list = ", ".join(f"'{t}'" for t in node_types)
            node_type_filter = f"AND any(l IN labels(e) WHERE l IN [{labels_list}])"

        # ---- Count total entities ----
        count_query = f"""
        MATCH (r:Repository {{id: $repo_id}})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e:Entity)
        WHERE e IS NOT NULL {node_type_filter}
        RETURN count(DISTINCT e) AS total_entities, count(DISTINCT f) AS total_files
        """
        count_results = neo4j_conn.execute_query(count_query, {"repo_id": str(repository_id)})
        total_entities = count_results[0].get("total_entities", 0) if count_results else 0
        total_files = count_results[0].get("total_files", 0) if count_results else 0

        # ---- Fetch File nodes ----
        file_query = """
        MATCH (r:Repository {id: $repo_id})<-[:BELONGS_TO]-(f:File)
        RETURN f {.*, labels: labels(f)} AS node
        """
        file_results = neo4j_conn.execute_query(file_query, {"repo_id": str(repository_id)})
        file_nodes = [GraphQueryService._normalize_node(r["node"]) for r in file_results if r.get("node")]

        # ---- Fetch Entity nodes with pagination and filtering ----
        entity_query = f"""
        MATCH (r:Repository {{id: $repo_id}})<-[:BELONGS_TO]-(f:File)<-[:DEFINED_IN]-(e:Entity)
        WHERE true {node_type_filter}
        RETURN e {{.*, labels: labels(e), file_path: f.relative_path}} AS node
        ORDER BY e.name
        SKIP $offset LIMIT $limit
        """
        entity_results = neo4j_conn.execute_query(entity_query, {
            "repo_id": str(repository_id),
            "offset": clamped_offset,
            "limit": clamped_limit,
        })
        entity_nodes = [GraphQueryService._normalize_node(r["node"]) for r in entity_results if r.get("node")]

        all_nodes = file_nodes + entity_nodes
        node_ids = {n["id"] for n in all_nodes}

        # ---- Fetch edges between visible nodes ----
        rel_type_filter = ""
        if relationship_types:
            types_list = ", ".join(f"'{t}'" for t in relationship_types)
            rel_type_filter = f"AND type(rel) IN [{types_list}]"

        edge_query = f"""
        MATCH (r:Repository {{id: $repo_id}})<-[:BELONGS_TO]-(f:File)<-[:DEFINED_IN]-(e1:Entity)-[rel]->(e2:Entity)
        WHERE true {rel_type_filter}
        RETURN {{
            id: rel.id,
            source_id: e1.id,
            target_id: e2.id,
            type: type(rel),
            confidence: rel.confidence,
            source_file: rel.source_file,
            line_number: rel.line_number
        }} AS edge
        """
        edge_results = neo4j_conn.execute_query(edge_query, {"repo_id": str(repository_id)})
        # Only include edges where both endpoints are in the visible node set
        all_edges = []
        for r in edge_results:
            edge = r.get("edge")
            if edge and edge.get("source_id") in node_ids and edge.get("target_id") in node_ids:
                all_edges.append(GraphQueryService._normalize_edge(edge))

        # Also add structural edges (DEFINED_IN) between entities and files
        for en in entity_nodes:
            file_path = en.get("file_path") or en.get("metadata", {}).get("file_path", "")
            # Find the matching file node
            for fn in file_nodes:
                if fn.get("file_path") == file_path or fn.get("metadata", {}).get("relative_path") == file_path:
                    all_edges.append({
                        "id": f"defined_in_{en['id']}_{fn['id']}",
                        "source": en["id"],
                        "target": fn["id"],
                        "relationship_type": "DEFINED_IN",
                        "confidence": 1.0,
                        "source_file": "",
                        "line_number": 0,
                    })
                    break

        total_count = total_entities + total_files
        has_more = (clamped_offset + clamped_limit) < total_entities

        return {
            "nodes": all_nodes,
            "edges": all_edges,
            "total_nodes": total_count,
            "total_edges": len(all_edges),
            "has_more": has_more,
        }

    @staticmethod
    def get_node_neighbors(
        entity_id: uuid.UUID,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both",
        depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Retrieve the immediate neighborhood of a node for lazy expansion.
        direction: 'in', 'out', or 'both'
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"nodes": [], "edges": []}

        clamped_depth = max(1, min(depth, 3))

        rel_filter = ""
        if relationship_types:
            types_str = "|".join(relationship_types)
            rel_filter = f":{types_str}"

        if direction == "out":
            pattern = f"(e)-[rel{rel_filter}*1..{clamped_depth}]->(neighbor)"
        elif direction == "in":
            pattern = f"(neighbor)-[rel{rel_filter}*1..{clamped_depth}]->(e)"
        else:
            pattern = f"(e)-[rel{rel_filter}*1..{clamped_depth}]-(neighbor)"

        query = f"""
        MATCH (e {{id: $entity_id}})
        OPTIONAL MATCH path = {pattern}
        WHERE neighbor IS NOT NULL
        WITH e, path, nodes(path) AS path_nodes, relationships(path) AS path_rels
        UNWIND path_nodes AS n
        UNWIND path_rels AS r
        RETURN collect(DISTINCT n {{.*, labels: labels(n)}}) AS neighbors,
               collect(DISTINCT {{
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
            return {"nodes": [], "edges": []}

        raw_neighbors = results[0].get("neighbors", [])
        raw_edges = results[0].get("edges", [])

        nodes = [GraphQueryService._normalize_node(n) for n in raw_neighbors if n]
        edges = [GraphQueryService._normalize_edge(e) for e in raw_edges if e and e.get("type")]

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def search_entities(
        repository_id: uuid.UUID,
        query_text: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search entities by name or fully_qualified_name using case-insensitive
        CONTAINS matching. Returns a list of search result dicts.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return []

        clamped_limit = max(1, min(limit, 50))
        search_term = query_text.strip()
        if not search_term:
            return []

        type_filter = ""
        if entity_types:
            labels_list = ", ".join(f"'{t}'" for t in entity_types)
            type_filter = f"AND any(l IN labels(e) WHERE l IN [{labels_list}])"

        cypher = f"""
        MATCH (r:Repository {{id: $repo_id}})<-[:BELONGS_TO]-(f:File)<-[:DEFINED_IN]-(e:Entity)
        WHERE (toLower(e.name) CONTAINS toLower($search)
               OR toLower(e.fully_qualified_name) CONTAINS toLower($search))
        {type_filter}
        RETURN e {{.*, labels: labels(e), file_path: f.relative_path}} AS entity,
               CASE
                   WHEN toLower(e.name) = toLower($search) THEN 'exact_name'
                   WHEN toLower(e.name) STARTS WITH toLower($search) THEN 'name_prefix'
                   WHEN toLower(e.fully_qualified_name) CONTAINS toLower($search) THEN 'fqn_match'
                   ELSE 'name_contains'
               END AS match_field
        ORDER BY
            CASE
                WHEN toLower(e.name) = toLower($search) THEN 0
                WHEN toLower(e.name) STARTS WITH toLower($search) THEN 1
                WHEN toLower(e.fully_qualified_name) CONTAINS toLower($search) THEN 2
                ELSE 3
            END,
            e.name
        LIMIT $limit
        """
        results = neo4j_conn.execute_query(cypher, {
            "repo_id": str(repository_id),
            "search": search_term,
            "limit": clamped_limit,
        })

        search_results = []
        for r in results:
            entity_raw = r.get("entity")
            if entity_raw:
                search_results.append({
                    "entity": GraphQueryService._normalize_node(entity_raw),
                    "match_field": r.get("match_field", "name_contains"),
                })
        return search_results

    @staticmethod
    def get_entity_detail(entity_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve full detail for a single entity, including its file context
        and all incoming/outgoing relationships.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return None

        query = """
        MATCH (e:Entity {id: $entity_id})
        OPTIONAL MATCH (e)-[:DEFINED_IN]->(f:File)
        OPTIONAL MATCH (e)-[out]->(target)
        OPTIONAL MATCH (source)-[inc]->(e)
        RETURN e {.*, labels: labels(e)} AS entity,
               f {.*, labels: labels(f)} AS file,
               collect(DISTINCT {
                   relationship_type: type(out),
                   target: target {.*, labels: labels(target)}
               }) AS outgoing,
               collect(DISTINCT {
                   relationship_type: type(inc),
                   source: source {.*, labels: labels(source)}
               }) AS incoming
        """
        results = neo4j_conn.execute_query(query, {"entity_id": str(entity_id)})
        if not results:
            return None

        record = results[0]
        entity_raw = record.get("entity")
        if not entity_raw:
            return None

        file_raw = record.get("file")
        outgoing = [
            {
                "relationship_type": o.get("relationship_type", ""),
                "target": GraphQueryService._normalize_node(o["target"]),
            }
            for o in record.get("outgoing", [])
            if o.get("target") is not None and o.get("relationship_type") is not None
        ]
        incoming = [
            {
                "relationship_type": i.get("relationship_type", ""),
                "source": GraphQueryService._normalize_node(i["source"]),
            }
            for i in record.get("incoming", [])
            if i.get("source") is not None and i.get("relationship_type") is not None
        ]

        entity_node = GraphQueryService._normalize_node(entity_raw)
        file_info = None
        if file_raw:
            file_info = {
                "id": file_raw.get("id", ""),
                "relative_path": file_raw.get("relative_path", ""),
                "filename": file_raw.get("filename", ""),
                "language": file_raw.get("language", ""),
                "size_bytes": file_raw.get("size_bytes", 0),
            }

        return {
            "entity": entity_node,
            "file": file_info,
            "outgoing_relationships": outgoing,
            "incoming_relationships": incoming,
            "outgoing_count": len(outgoing),
            "incoming_count": len(incoming),
        }

    @staticmethod
    def get_repository_hierarchy(repository_id: uuid.UUID) -> Dict[str, Any]:
        """
        Return a tree-structured hierarchy: Repository -> Files -> Entities.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"repository": None, "children": []}

        # Fetch repository
        repo_query = """
        MATCH (r:Repository {id: $repo_id})
        RETURN r {.*, labels: labels(r)} AS repo
        """
        repo_results = neo4j_conn.execute_query(repo_query, {"repo_id": str(repository_id)})
        if not repo_results:
            return {"repository": None, "children": []}

        repo_raw = repo_results[0].get("repo")

        # Fetch files with their entities
        hierarchy_query = """
        MATCH (r:Repository {id: $repo_id})<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e:Entity)
        RETURN f {.*, labels: labels(f)} AS file,
               collect(e {.*, labels: labels(e)}) AS entities
        ORDER BY f.relative_path
        """
        hierarchy_results = neo4j_conn.execute_query(hierarchy_query, {"repo_id": str(repository_id)})

        children = []
        for record in hierarchy_results:
            file_raw = record.get("file")
            if not file_raw:
                continue
            entities_raw = record.get("entities", [])
            entity_children = [
                GraphQueryService._normalize_node(e)
                for e in entities_raw if e and e.get("id")
            ]
            children.append({
                "file": GraphQueryService._normalize_node(file_raw),
                "entities": entity_children,
                "entity_count": len(entity_children),
            })

        return {
            "repository": {
                "id": repo_raw.get("id", ""),
                "name": repo_raw.get("name", ""),
                "url": repo_raw.get("url", ""),
            },
            "children": children,
            "total_files": len(children),
            "total_entities": sum(c["entity_count"] for c in children),
        }

    @staticmethod
    def get_incoming_relationships(
        entity_id: uuid.UUID,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """All inbound edges for an entity, optionally filtered by type."""
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return []

        rel_filter = ""
        if relationship_types:
            types_str = "|".join(relationship_types)
            rel_filter = f":{types_str}"

        query = f"""
        MATCH (source)-[r{rel_filter}]->(e:Entity {{id: $entity_id}})
        RETURN {{
            id: r.id,
            source_id: source.id,
            target_id: e.id,
            type: type(r),
            confidence: r.confidence,
            source_file: r.source_file,
            line_number: r.line_number,
            source_name: source.name,
            source_labels: labels(source)
        }} AS edge
        """
        results = neo4j_conn.execute_query(query, {"entity_id": str(entity_id)})
        return [GraphQueryService._normalize_edge(r["edge"]) for r in results if r.get("edge")]

    @staticmethod
    def get_outgoing_relationships(
        entity_id: uuid.UUID,
        relationship_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """All outbound edges for an entity, optionally filtered by type."""
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return []

        rel_filter = ""
        if relationship_types:
            types_str = "|".join(relationship_types)
            rel_filter = f":{types_str}"

        query = f"""
        MATCH (e:Entity {{id: $entity_id}})-[r{rel_filter}]->(target)
        RETURN {{
            id: r.id,
            source_id: e.id,
            target_id: target.id,
            type: type(r),
            confidence: r.confidence,
            source_file: r.source_file,
            line_number: r.line_number,
            target_name: target.name,
            target_labels: labels(target)
        }} AS edge
        """
        results = neo4j_conn.execute_query(query, {"entity_id": str(entity_id)})
        return [GraphQueryService._normalize_edge(r["edge"]) for r in results if r.get("edge")]

    @staticmethod
    def get_dependency_path(
        source_id: uuid.UUID,
        target_id: uuid.UUID,
        max_depth: int = 10,
    ) -> Dict[str, Any]:
        """
        Shortest path between two entities with a configurable max depth.
        Returns normalized nodes and edges.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {"path_found": False, "nodes": [], "edges": [], "length": 0}

        clamped = max(1, min(max_depth, 15))

        query = f"""
        MATCH (source:Entity {{id: $source_id}}), (target:Entity {{id: $target_id}})
        MATCH p = shortestPath((source)-[*..{clamped}]->(target))
        RETURN [n IN nodes(p) | n {{.*, labels: labels(n)}}] AS nodes,
               [r IN relationships(p) | {{
                   id: r.id,
                   source_id: startNode(r).id,
                   target_id: endNode(r).id,
                   type: type(r),
                   confidence: r.confidence,
                   source_file: r.source_file,
                   line_number: r.line_number
               }}] AS edges
        """
        results = neo4j_conn.execute_query(query, {
            "source_id": str(source_id),
            "target_id": str(target_id),
        })

        if not results or not results[0].get("nodes"):
            return {"path_found": False, "nodes": [], "edges": [], "length": 0}

        raw_nodes = results[0].get("nodes", [])
        raw_edges = results[0].get("edges", [])
        nodes = [GraphQueryService._normalize_node(n) for n in raw_nodes]
        edges = [GraphQueryService._normalize_edge(e) for e in raw_edges]

        return {
            "path_found": True,
            "nodes": nodes,
            "edges": edges,
            "length": len(edges),
        }

    @staticmethod
    def get_graph_statistics(repository_id: uuid.UUID) -> Dict[str, Any]:
        """
        Comprehensive graph statistics including node/edge counts, density,
        and complexity metrics.
        """
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            return {
                "repository_id": str(repository_id),
                "total_nodes": 0, "total_edges": 0,
                "total_files": 0, "nodes_by_type": {},
                "edges_by_type": {}, "density": 0.0,
                "avg_degree": 0.0, "languages": {},
                "complexity": {"cyclomatic": 0, "depth": 0},
            }

        # Node counts by type
        node_query = """
        MATCH (r:Repository {id: $repo_id})<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e:Entity)
        WITH collect(DISTINCT f) AS files, collect(DISTINCT e) AS entities
        UNWIND entities AS ent
        UNWIND labels(ent) AS label
        WITH files, entities, label, count(DISTINCT ent) AS cnt
        RETURN size(files) AS total_files,
               size(entities) AS total_entities,
               collect({label: label, count: cnt}) AS type_counts
        """
        node_results = neo4j_conn.execute_query(node_query, {"repo_id": str(repository_id)})

        total_files = 0
        total_entities = 0
        nodes_by_type = {}
        if node_results:
            r = node_results[0]
            total_files = r.get("total_files", 0)
            total_entities = r.get("total_entities", 0)
            for tc in r.get("type_counts", []):
                label = tc.get("label")
                if label and label != "Entity":
                    nodes_by_type[label] = tc.get("count", 0)

        # Edge counts by type
        edge_query = """
        MATCH (r:Repository {id: $repo_id})<-[:BELONGS_TO]-(f:File)<-[:DEFINED_IN]-(e1:Entity)-[rel]->(e2:Entity)
        RETURN type(rel) AS rel_type, count(rel) AS cnt
        """
        edge_results = neo4j_conn.execute_query(edge_query, {"repo_id": str(repository_id)})
        edges_by_type = {}
        total_edges = 0
        for r in edge_results:
            rt = r.get("rel_type")
            c = r.get("cnt", 0)
            if rt:
                edges_by_type[rt] = c
                total_edges += c

        # Language distribution
        lang_query = """
        MATCH (r:Repository {id: $repo_id})<-[:BELONGS_TO]-(f:File)
        RETURN f.language AS lang, count(f) AS cnt
        """
        lang_results = neo4j_conn.execute_query(lang_query, {"repo_id": str(repository_id)})
        languages = {}
        for r in lang_results:
            lang = r.get("lang")
            if lang:
                languages[lang] = r.get("cnt", 0)

        # Compute density: edges / (nodes * (nodes - 1)) for directed graph
        total_nodes = total_entities + total_files
        density = 0.0
        if total_nodes > 1:
            density = round(total_edges / (total_nodes * (total_nodes - 1)), 6)

        avg_degree = 0.0
        if total_nodes > 0:
            avg_degree = round((2 * total_edges) / total_nodes, 2)

        return {
            "repository_id": str(repository_id),
            "total_nodes": total_nodes,
            "total_files": total_files,
            "total_entities": total_entities,
            "total_edges": total_edges,
            "nodes_by_type": nodes_by_type,
            "edges_by_type": edges_by_type,
            "density": density,
            "avg_degree": avg_degree,
            "languages": languages,
            "complexity": {
                "files": total_files,
                "entities": total_entities,
                "relationships": total_edges,
                "types_used": len(nodes_by_type),
                "relationship_types_used": len(edges_by_type),
            },
        }
