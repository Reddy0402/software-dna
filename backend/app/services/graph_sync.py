import uuid
import logging
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency
from app.database.neo4j_connection import get_neo4j_connection
from app.core.exceptions import GraphSyncError

logger = logging.getLogger("app.services.graph_sync")

# Mapping of database entity types to Neo4j Node Labels
ENTITY_TYPE_LABEL_MAP = {
    "class": "Class",
    "interface": "Interface",
    "function": "Function",
    "method": "Method",
    "import": "Import",
    "struct": "Struct",
    "namespace": "Namespace",
    "constructor": "Constructor",
    "module": "Module",
}

class GraphSyncService:
    """
    Stateless database synchronization orchestrator.
    Synchronizes repository metadata, files, code entities, and dependencies
    from PostgreSQL to Neo4j.
    """

    @staticmethod
    def sync_repository(db: Session, repository_id: uuid.UUID) -> Dict:
        """
        Runs the full Neo4j graph synchronization pipeline.
        Updates Repository.graph_status during the process.
        """
        logger.info(f"[{repository_id}] Starting Neo4j graph synchronization...")

        # 1. Fetch Repository
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise GraphSyncError(f"Repository with ID {repository_id} not found")

        # Check Neo4j connection
        neo4j_conn = get_neo4j_connection()
        if not neo4j_conn or not neo4j_conn.is_available:
            error_msg = "Neo4j driver is not connected or unavailable."
            repo.graph_status = "failed"
            repo.last_error = error_msg
            db.commit()
            raise GraphSyncError(error_msg)

        try:
            repo.graph_status = "syncing"
            repo.last_error = None
            db.commit()

            # 2. Fetch Files, Entities, and Dependencies
            files = db.query(File).filter(File.repository_id == repository_id).all()
            entities = db.query(CodeEntity).filter(CodeEntity.repository_id == repository_id).all()
            dependencies = db.query(Dependency).filter(Dependency.repository_id == repository_id).all()

            logger.info(f"[{repository_id}] Data retrieved from PostgreSQL. "
                        f"Files: {len(files)}, Entities: {len(entities)}, Dependencies: {len(dependencies)}")

            # Step 1: Clear stale repository graph data
            GraphSyncService._clear_repository_graph(neo4j_conn, repository_id)

            # Step 2: Sync Repository & File nodes
            GraphSyncService._sync_repo_and_file_nodes(neo4j_conn, repo, files)

            # Step 3: Sync Entity nodes
            GraphSyncService._sync_entity_nodes(neo4j_conn, entities)

            # Step 4: Sync structural relationships (BELONGS_TO, DEFINED_IN)
            GraphSyncService._sync_structural_relationships(neo4j_conn, repo.id, files, entities)

            # Step 5: Sync dependency relationships (CONTAINS, DEFINES, CALLS, etc.)
            GraphSyncService._sync_dependency_relationships(neo4j_conn, repo.id, dependencies, entities)

            repo.graph_status = "completed"
            repo.last_error = None
            db.commit()

            logger.info(f"[{repository_id}] Neo4j graph synchronization completed successfully.")
            return {
                "repository_id": repository_id,
                "status": "completed",
                "files_synced": len(files),
                "entities_synced": len(entities),
                "dependencies_synced": len(dependencies),
            }

        except Exception as e:
            db.rollback()
            error_msg = f"Graph synchronization failed: {str(e)}"
            logger.error(f"[{repository_id}] {error_msg}", exc_info=True)
            repo.graph_status = "failed"
            repo.last_error = error_msg
            db.commit()
            raise GraphSyncError(error_msg)

    @staticmethod
    def _clear_repository_graph(neo4j_conn, repo_id: uuid.UUID):
        """Removes all nodes and relationships associated with the repository."""
        logger.info(f"[{repo_id}] Clearing existing graph data in Neo4j...")
        # Delete relationships first to avoid database locking/errors in some Neo4j versions,
        # though DETACH DELETE handles it, we can query nodes belonging to this repo.
        query = """
        MATCH (r:Repository {id: $repo_id})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        OPTIONAL MATCH (f)<-[:DEFINED_IN]-(e:Entity)
        DETACH DELETE r, f, e
        """
        neo4j_conn.execute_write(query, {"repo_id": str(repo_id)})

    @staticmethod
    def _sync_repo_and_file_nodes(neo4j_conn, repo: Repository, files: List[File]):
        """Creates/merges Repository and File nodes in Neo4j."""
        logger.info(f"[{repo.id}] Syncing Repository and File nodes...")

        # Sync Repository Node
        repo_query = """
        MERGE (r:Repository {id: $repo_id})
        SET r.name = $name,
            r.url = $url,
            r.owner = $owner
        """
        neo4j_conn.execute_write(repo_query, {
            "repo_id": str(repo.id),
            "name": repo.name,
            "url": repo.url,
            "owner": repo.owner or ""
        })

        # Sync File Nodes in batches
        file_query = """
        UNWIND $files AS file_data
        MERGE (f:File {id: file_data.id})
        SET f.relative_path = file_data.relative_path,
            f.filename = file_data.filename,
            f.extension = file_data.extension,
            f.language = file_data.language,
            f.size_bytes = file_data.size_bytes
        """
        batch_size = 100
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            files_data = [
                {
                    "id": str(f.id),
                    "relative_path": f.relative_path,
                    "filename": f.filename,
                    "extension": f.extension,
                    "language": f.language,
                    "size_bytes": f.size_bytes
                }
                for f in batch
            ]
            neo4j_conn.execute_write(file_query, {"files": files_data})

    @staticmethod
    def _sync_entity_nodes(neo4j_conn, entities: List[CodeEntity]):
        """Creates/merges Entity nodes in Neo4j with language-independent type labels."""
        logger.info("Syncing CodeEntity nodes...")
        if not entities:
            return

        # We can dynamically add labels based on entity_type using Cypher's APOC or
        # by partitioning entities by type and running separate queries for each type.
        # Running separate queries for each type is safe and doesn't require APOC.
        entities_by_type: Dict[str, List[CodeEntity]] = {}
        for e in entities:
            # Map type to a standard Neo4j Label, fallback to Module if unknown
            raw_type = e.entity_type.lower()
            label = ENTITY_TYPE_LABEL_MAP.get(raw_type, "Module")
            entities_by_type.setdefault(label, []).append(e)

        batch_size = 100
        for label, batch_entities in entities_by_type.items():
            # Query template with dynamic label insertion
            # We use MERGE on id, and set properties.
            query = f"""
            UNWIND $entities AS ent
            MERGE (e:Entity {{"id": ent.id}})
            SET e :{label}
            SET e.name = ent.name,
                e.fully_qualified_name = ent.fully_qualified_name,
                e.visibility = ent.visibility,
                e.language = ent.language,
                e.start_line = ent.start_line,
                e.end_line = ent.end_line
            """
            for i in range(0, len(batch_entities), batch_size):
                batch = batch_entities[i:i + batch_size]
                entities_data = [
                    {
                        "id": str(ent.id),
                        "name": ent.name,
                        "fully_qualified_name": ent.fully_qualified_name,
                        "visibility": ent.visibility or "public",
                        "language": ent.language,
                        "start_line": ent.start_line,
                        "end_line": ent.end_line
                    }
                    for ent in batch
                ]
                neo4j_conn.execute_write(query, {"entities": entities_data})

    @staticmethod
    def _sync_structural_relationships(neo4j_conn, repo_id: uuid.UUID, files: List[File], entities: List[CodeEntity]):
        """Creates BELONGS_TO and DEFINED_IN relationships."""
        logger.info("Syncing structural relationships (BELONGS_TO, DEFINED_IN)...")

        # 1. File -[:BELONGS_TO]-> Repository
        belongs_to_query = """
        UNWIND $file_ids AS file_id
        MATCH (f:File {id: file_id})
        MATCH (r:Repository {id: $repo_id})
        MERGE (f)-[:BELONGS_TO]->(r)
        """
        file_ids = [str(f.id) for f in files]
        batch_size = 100
        for i in range(0, len(file_ids), batch_size):
            batch = file_ids[i:i + batch_size]
            neo4j_conn.execute_write(belongs_to_query, {"repo_id": str(repo_id), "file_ids": batch})

        # 2. Entity -[:DEFINED_IN]-> File
        defined_in_query = """
        UNWIND $mappings AS mapping
        MATCH (e:Entity {id: mapping.entity_id})
        MATCH (f:File {id: mapping.file_id})
        MERGE (e)-[:DEFINED_IN]->(f)
        """
        mappings = [{"entity_id": str(e.id), "file_id": str(e.file_id)} for e in entities]
        for i in range(0, len(mappings), batch_size):
            batch = mappings[i:i + batch_size]
            neo4j_conn.execute_write(defined_in_query, {"mappings": batch})

    @staticmethod
    def _sync_dependency_relationships(
        neo4j_conn,
        repo_id: uuid.UUID,
        dependencies: List[Dependency],
        entities: List[CodeEntity]
    ):
        """Creates relationships (CALLS, EXTENDS, etc.) based on dependency records."""
        logger.info("Syncing dependency relationships...")
        if not dependencies:
            return

        # Prepare lookup maps
        entities_by_id = {str(e.id): e for e in entities}

        # Partition dependencies by relationship_type to write matching edges cleanly
        deps_by_type: Dict[str, List[Dependency]] = {}
        for dep in dependencies:
            deps_by_type.setdefault(dep.relationship_type.upper(), []).append(dep)

        batch_size = 100
        for rel_type, batch_deps in deps_by_type.items():
            # For each relationship type, we can have resolved targets and unresolved targets (dummy/external)
            # Resolved: source_entity_id -> target_entity_id
            # Unresolved: source_entity_id -> target_fqn (create placeholder if needed)

            resolved_batch = []
            unresolved_batch = []

            for d in batch_deps:
                dep_data = {
                    "id": str(d.id),
                    "source_id": str(d.source_entity_id),
                    "confidence": d.confidence,
                    "source_file": d.source_file,
                    "line_number": d.line_number,
                    "meta_data": d.meta_data or {}
                }
                if d.target_entity_id:
                    dep_data["target_id"] = str(d.target_entity_id)
                    resolved_batch.append(dep_data)
                elif d.target_fqn:
                    # Unresolved external dependency
                    # Last part of FQN can be the name of the external node
                    fqn = d.target_fqn
                    name = fqn.split(".")[-1] if "." in fqn else fqn
                    dep_data["target_fqn"] = fqn
                    dep_data["target_name"] = name
                    unresolved_batch.append(dep_data)

            # Sync resolved relationships
            resolved_query = f"""
            UNWIND $relationships AS rel
            MATCH (source:Entity {{id: rel.source_id}})
            MATCH (target:Entity {{id: rel.target_id}})
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.id = rel.id,
                r.confidence = rel.confidence,
                r.source_file = rel.source_file,
                r.line_number = rel.line_number,
                r.meta_data = rel.meta_data
            """
            for i in range(0, len(resolved_batch), batch_size):
                batch = resolved_batch[i:i + batch_size]
                neo4j_conn.execute_write(resolved_query, {"relationships": batch})

            # Sync unresolved/external relationships
            unresolved_query = f"""
            UNWIND $relationships AS rel
            MATCH (source:Entity {{id: rel.source_id}})
            MERGE (target:Entity:External {{fully_qualified_name: rel.target_fqn}})
            ON CREATE SET target.name = rel.target_name, target.id = apoc.create.uuid()
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.id = rel.id,
                r.confidence = rel.confidence,
                r.source_file = rel.source_file,
                r.line_number = rel.line_number,
                r.meta_data = rel.meta_data
            """
            # Wait, apoc.create.uuid() might not be installed or enabled on all Neo4j instances!
            # Let's avoid apoc to keep it portable, and set target.id directly from the client or use fully_qualified_name as key.
            # Cypher MERGE on fully_qualified_name:
            unresolved_query_no_apoc = f"""
            UNWIND $relationships AS rel
            MATCH (source:Entity {{id: rel.source_id}})
            MERGE (target:Entity:External {{fully_qualified_name: rel.target_fqn}})
            ON CREATE SET target.name = rel.target_name, target.id = rel.id
            MERGE (source)-[r:{rel_type}]->(target)
            SET r.id = rel.id,
                r.confidence = rel.confidence,
                r.source_file = rel.source_file,
                r.line_number = rel.line_number,
                r.meta_data = rel.meta_data
            """
            for i in range(0, len(unresolved_batch), batch_size):
                batch = unresolved_batch[i:i + batch_size]
                neo4j_conn.execute_write(unresolved_query_no_apoc, {"relationships": batch})
