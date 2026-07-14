import os
import sys
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import tree_sitter
from tree_sitter import Language, Parser

logger = logging.getLogger("app.services.parser")

# Increase recursion limit to safely handle deeply nested ASTs in large source files
sys.setrecursionlimit(10000)


class ASTNode:
    """
    Represents a single node in the normalized Abstract Syntax Tree.
    Includes references to its parent and children for in-memory traversal.
    """
    def __init__(
        self,
        node_id: int,
        node_type: str,
        text: str,
        start_line: int,
        end_line: int,
        start_column: int,
        end_column: int,
        parent: Optional["ASTNode"] = None
    ):
        self.id = node_id
        self.type = node_type
        self.text = text
        self.start_line = start_line
        self.end_line = end_line
        self.start_column = start_column
        self.end_column = end_column
        self.parent = parent
        self.children: List["ASTNode"] = []


class ParsedFileRepresentation:
    """
    Wrapper holding the metadata, status, and AST root for a parsed file.
    """
    def __init__(self, filename: str, relative_path: str, language: str):
        self.filename = filename
        self.relative_path = relative_path
        self.language = language
        self.status = "success"  # "success", "warning", "error"
        self.syntax_errors = 0
        self.root_node: Optional[ASTNode] = None

    def to_dict(self) -> dict:
        """
        Serializes the AST into a flat list of nodes referencing parent/child IDs.
        This prevents circular reference RecursionErrors during JSON serialization.
        """
        flat_nodes = []

        def serialize_node(node: ASTNode):
            node_dict = {
                "id": node.id,
                "type": node.type,
                "text": node.text,
                "start_line": node.start_line,
                "end_line": node.end_line,
                "start_column": node.start_column,
                "end_column": node.end_column,
                "parent_id": node.parent.id if node.parent else None,
                "child_ids": [c.id for c in node.children]
            }
            flat_nodes.append(node_dict)
            for child in node.children:
                serialize_node(child)

        if self.root_node:
            serialize_node(self.root_node)

        return {
            "filename": self.filename,
            "relative_path": self.relative_path,
            "language": self.language,
            "status": self.status,
            "syntax_errors_count": self.syntax_errors,
            "root_node_id": self.root_node.id if self.root_node else None,
            "nodes": flat_nodes
        }


class ParserFactory:
    """
    Registry for loading and caching Tree-sitter Language and Parser instances.
    Implements reuse to optimize memory allocations and CPU overhead.
    """
    _languages = {}
    _parsers = {}

    @classmethod
    def get_language(cls, language_name: str, extension: str = "") -> Language:
        lang_lower = language_name.strip().lower()
        ext_lower = extension.strip().lower()

        # Unique key distinguishing TSX files from standard TS files
        cache_key = f"{lang_lower}_tsx" if lang_lower == "typescript" and ext_lower == "tsx" else lang_lower

        if cache_key in cls._languages:
            return cls._languages[cache_key]

        # Lazy load appropriate grammar bindings
        try:
            if lang_lower == "python":
                import tree_sitter_python
                lang = Language(tree_sitter_python.language())
            elif lang_lower == "javascript":
                import tree_sitter_javascript
                lang = Language(tree_sitter_javascript.language())
            elif lang_lower == "typescript":
                import tree_sitter_typescript
                if ext_lower == "tsx":
                    lang = Language(tree_sitter_typescript.language_tsx())
                else:
                    lang = Language(tree_sitter_typescript.language_typescript())
            elif lang_lower == "java":
                import tree_sitter_java
                lang = Language(tree_sitter_java.language())
            elif lang_lower in ("cpp", "c++"):
                import tree_sitter_cpp
                lang = Language(tree_sitter_cpp.language())
            elif lang_lower == "c":
                import tree_sitter_c
                lang = Language(tree_sitter_c.language())
            elif lang_lower == "go":
                import tree_sitter_go
                lang = Language(tree_sitter_go.language())
            elif lang_lower == "rust":
                import tree_sitter_rust
                lang = Language(tree_sitter_rust.language())
            elif lang_lower in ("csharp", "c#"):
                import tree_sitter_c_sharp
                lang = Language(tree_sitter_c_sharp.language())
            else:
                raise ValueError(f"Unsupported tree-sitter language: '{language_name}'")
        except ImportError as e:
            logger.error(f"Failed to import tree-sitter grammar for '{language_name}': {str(e)}")
            raise

        cls._languages[cache_key] = lang
        return lang

    @classmethod
    def get_parser(cls, language_name: str, extension: str = "") -> Parser:
        lang_lower = language_name.strip().lower()
        ext_lower = extension.strip().lower()
        cache_key = f"{lang_lower}_tsx" if lang_lower == "typescript" and ext_lower == "tsx" else lang_lower

        if cache_key in cls._parsers:
            return cls._parsers[cache_key]

        lang = cls.get_language(language_name, extension)
        parser = Parser(lang)
        cls._parsers[cache_key] = parser
        return parser


class ParserService:
    """
    Orchestrates syntax parsing, AST construction, and error logging.
    """
    @staticmethod
    def parse_file_content(
        content: bytes,
        filename: str,
        relative_path: str,
        language: str
    ) -> ParsedFileRepresentation:
        """
        Parses source code bytes and builds the traversing ASTNode tree structure.
        """
        representation = ParsedFileRepresentation(
            filename=filename,
            relative_path=relative_path,
            language=language
        )

        if not content:
            # Handle empty files by returning an empty representation
            representation.status = "success"
            return representation

        _, ext = os.path.splitext(filename.lower())

        start_time = datetime.now(timezone.utc)
        try:
            parser = ParserFactory.get_parser(language, ext)
            tree = parser.parse(content)
        except Exception as e:
            logger.error(f"Failed to initialize parser for '{language}': {str(e)}")
            representation.status = "error"
            return representation

        if not tree or not tree.root_node:
            representation.status = "error"
            return representation

        # Recursive builder variables
        counter = [0]
        error_counter = [0]

        def build_ast(ts_node: tree_sitter.Node, parent_ast: Optional[ASTNode] = None) -> ASTNode:
            node_id = counter[0]
            counter[0] += 1

            if ts_node.type == "ERROR":
                error_counter[0] += 1

            # Extract source slice and decode safely
            node_text = content[ts_node.start_byte : ts_node.end_byte].decode("utf-8", errors="replace")

            ast_node = ASTNode(
                node_id=node_id,
                node_type=ts_node.type,
                text=node_text,
                start_line=ts_node.start_point.row,
                end_line=ts_node.end_point.row,
                start_column=ts_node.start_point.column,
                end_column=ts_node.end_point.column,
                parent=parent_ast
            )

            for child in ts_node.children:
                child_ast = build_ast(child, parent_ast=ast_node)
                ast_node.children.append(child_ast)

            return ast_node

        try:
            representation.root_node = build_ast(tree.root_node)
            representation.syntax_errors = error_counter[0]
            
            # Mark status: success, or warning if syntax errors exist
            if error_counter[0] > 0:
                representation.status = "warning"
            else:
                representation.status = "success"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Parsed file '{relative_path}' in {duration:.4f}s. "
                f"Nodes: {counter[0]}, Errors: {error_counter[0]}, Status: {representation.status}"
            )
        except Exception as e:
            logger.error(f"Failed to construct AST tree for '{relative_path}': {str(e)}")
            representation.status = "error"

        return representation

    @staticmethod
    def parse_file_path(
        absolute_path: str,
        relative_path: str,
        language: str
    ) -> ParsedFileRepresentation:
        """
        Reads a file from disk and parses its content.
        """
        filename = os.path.basename(absolute_path)
        try:
            with open(absolute_path, "rb") as f:
                content = f.read()
            return ParserService.parse_file_content(content, filename, relative_path, language)
        except Exception as e:
            logger.error(f"Failed to read file from disk '{absolute_path}': {str(e)}")
            rep = ParsedFileRepresentation(filename=filename, relative_path=relative_path, language=language)
            rep.status = "error"
            return rep
