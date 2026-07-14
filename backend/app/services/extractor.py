import logging
import uuid
from typing import List, Dict, Type
from sqlalchemy.orm import Session
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.services.parser import ParserService
from app.services.visitors import (
    BaseVisitor,
    PythonVisitor,
    JavaScriptVisitor,
    TypeScriptVisitor,
    JavaVisitor,
    CSharpVisitor,
    CppVisitor,
    GoVisitor,
    RustVisitor
)
from app.core.exceptions import RepositoryImportError

logger = logging.getLogger("app.services.extractor")

# Register Visitor mapping configurations
VISITOR_REGISTRY: Dict[str, Type[BaseVisitor]] = {
    "python": PythonVisitor,
    "javascript": JavaScriptVisitor,
    "typescript": TypeScriptVisitor,
    "java": JavaVisitor,
    "csharp": CSharpVisitor,
    "c#": CSharpVisitor,
    "go": GoVisitor,
    "rust": RustVisitor,
    "cpp": CppVisitor,
    "c++": CppVisitor,
    "c": CppVisitor
}


class ExtractionService:
    @staticmethod
    def extract_metadata(db: Session, file_id: uuid.UUID) -> List[CodeEntity]:
        """
        Parses a file path, runs the language-specific Visitor traversal over its AST,
        reconstructs parent-child scopes, and stores extracted CodeEntities in the DB.
        """
        # 1. Fetch file record from DB
        file_record = db.query(File).filter(File.id == file_id).first()
        if not file_record:
            raise RepositoryImportError(f"File record with ID {file_id} not found")

        logger.info(f"[{file_id}] Fetching file AST & starting metadata extraction...")

        # 2. Clear out any existing CodeEntity entries for this file to support clean re-runs
        try:
            db.query(CodeEntity).filter(CodeEntity.file_id == file_id).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[{file_id}] Failed to clear old extracted entities: {str(e)}")
            raise RepositoryImportError(f"Database error clearing old code entities: {str(e)}")

        # 3. Parse AST
        parsed_rep = ParserService.parse_file_path(
            absolute_path=file_record.absolute_path,
            relative_path=file_record.relative_path,
            language=file_record.language
        )

        if parsed_rep.status == "error" or not parsed_rep.root_node:
            logger.warning(f"[{file_id}] Parser returned warning/error or empty AST. Skipping extraction.")
            return []

        # 4. Resolve Visitor class
        lang_key = file_record.language.strip().lower()
        visitor_class = VISITOR_REGISTRY.get(lang_key)
        if not visitor_class:
            logger.warning(f"[{file_id}] No Visitor parser registered for language: '{file_record.language}'. Skipping.")
            return []

        # 5. Run visitor
        visitor = visitor_class()
        visitor.visit(parsed_rep.root_node)

        # 6. Map ExtractedEntities into database CodeEntity models (nested conversion)
        db_entities: List[CodeEntity] = []

        def build_entities(extracted_list: list, parent_db_id: Optional[uuid.UUID] = None):
            for ext in extracted_list:
                entity_id = uuid.uuid4()
                
                # Reconstruct FQN dynamically based on scope traversal parent naming
                fqn_parts = []
                curr = ext
                while curr:
                    fqn_parts.insert(0, curr.name)
                    curr = curr.parent
                
                # Append module context to the fully qualified name
                module_name = file_record.filename.rsplit(".", 1)[0]
                fqn_parts.insert(0, module_name)
                fully_qualified_name = ".".join(fqn_parts)

                db_entity = CodeEntity(
                    id=entity_id,
                    repository_id=file_record.repository_id,
                    file_id=file_id,
                    parent_id=parent_db_id,
                    entity_type=ext.entity_type,
                    name=ext.name,
                    fully_qualified_name=fully_qualified_name,
                    start_line=ext.start_line,
                    end_line=ext.end_line,
                    visibility=ext.visibility,
                    language=file_record.language,
                    meta_data=ext.meta_data
                )
                db_entities.append(db_entity)

                # Recursively process child nodes nested under this node's UUID
                build_entities(ext.children, parent_db_id=entity_id)

        # Retrieve root-level extracted entities (entities that have no parent scope)
        root_entities = [e for e in visitor.entities if e.parent is None]
        build_entities(root_entities)

        # 7. Persist to DB
        if db_entities:
            try:
                db.add_all(db_entities)
                db.commit()
                # Refresh all records to load updated ids
                for item in db_entities:
                    db.refresh(item)
                logger.info(f"[{file_id}] Successfully extracted and saved {len(db_entities)} code entities.")
            except Exception as e:
                db.rollback()
                logger.error(f"[{file_id}] Failed to save extracted code entities: {str(e)}")
                raise RepositoryImportError(f"Database error saving code entities: {str(e)}")
        else:
            logger.info(f"[{file_id}] Metadata extraction completed. No entities detected.")

        return db_entities
