import logging
from typing import List, Optional, Tuple
from app.services.parser import ASTNode

logger = logging.getLogger("app.services.visitors")


class ExtractedEntity:
    """
    Intermediate representation of a programming construct extracted during AST traversal.
    """
    def __init__(
        self,
        entity_type: str,
        name: str,
        start_line: int,
        end_line: int,
        visibility: str = "public",
        meta_data: Optional[dict] = None,
        parent: Optional["ExtractedEntity"] = None
    ):
        self.entity_type = entity_type
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.visibility = visibility
        self.meta_data = meta_data or {}
        self.parent = parent
        self.children: List["ExtractedEntity"] = []


class BaseVisitor:
    """
    Base visitor class containing common AST traversal algorithms, scope management,
    and fully qualified name (FQN) generation helper hooks.
    """
    def __init__(self):
        self.entities: List[ExtractedEntity] = []
        self.scope_stack: List[ExtractedEntity] = []

    def visit(self, node: Optional[ASTNode]):
        if not node:
            return
        
        # Dispatch to visit_{node_type} if it exists
        method_name = f"visit_{node.type}"
        visitor_method = getattr(self, method_name, self.default_visit)
        visitor_method(node)

    def default_visit(self, node: ASTNode):
        for child in node.children:
            self.visit(child)

    # Scope Helpers
    def current_parent(self) -> Optional[ExtractedEntity]:
        return self.scope_stack[-1] if self.scope_stack else None

    def push_scope(self, entity: ExtractedEntity):
        parent = self.current_parent()
        if parent:
            parent.children.append(entity)
            entity.parent = parent
        self.entities.append(entity)
        self.scope_stack.append(entity)

    def pop_scope(self):
        if self.scope_stack:
            self.scope_stack.pop()

    # AST Helper Lookups
    @staticmethod
    def find_child_by_type(node: ASTNode, type_name: str) -> Optional[ASTNode]:
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    @staticmethod
    def find_all_children_by_type(node: ASTNode, type_name: str) -> List[ASTNode]:
        return [c for c in node.children if c.type == type_name]


# ----------------------------------------------------
# Python Extractor Visitor
# ----------------------------------------------------
class PythonVisitor(BaseVisitor):
    def visit_class_definition(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousClass"
        
        if name.startswith("__") and name.endswith("__"):
            visibility = "public"
        elif name.startswith("__"):
            visibility = "private"
        elif name.startswith("_"):
            visibility = "protected"
        else:
            visibility = "public"

        # Base inheritance extraction
        bases = []
        arg_list = self.find_child_by_type(node, "argument_list")
        if arg_list:
            bases = [child.text for child in arg_list.children if child.type in ("identifier", "attribute")]

        entity = ExtractedEntity(
            entity_type="class",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line,
            visibility=visibility,
            meta_data={"bases": bases}
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_function_definition(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        if name.startswith("__") and name.endswith("__"):
            visibility = "public"
        elif name.startswith("__"):
            visibility = "private"
        elif name.startswith("_"):
            visibility = "protected"
        else:
            visibility = "public"

        parent = self.current_parent()
        entity_type = "method" if parent and parent.entity_type == "class" else "function"

        # Parameters extraction
        params = []
        param_list = self.find_child_by_type(node, "parameters")
        if param_list:
            params = [c.text for c in param_list.children if c.type in ("identifier", "typed_parameter", "dictionary_splat_pattern", "list_splat_pattern")]

        entity = ExtractedEntity(
            entity_type=entity_type,
            name=name,
            start_line=node.start_line,
            end_line=node.end_line,
            visibility=visibility,
            meta_data={"parameters": params}
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_import_statement(self, node: ASTNode):
        entity = ExtractedEntity(
            entity_type="import",
            name=node.text,
            start_line=node.start_line,
            end_line=node.end_line,
            meta_data={"raw_import": node.text}
        )
        self.entities.append(entity)

    def visit_import_from_statement(self, node: ASTNode):
        entity = ExtractedEntity(
            entity_type="import",
            name=node.text,
            start_line=node.start_line,
            end_line=node.end_line,
            meta_data={"raw_import": node.text}
        )
        self.entities.append(entity)


# ----------------------------------------------------
# JavaScript & TypeScript Extractor Visitor
# ----------------------------------------------------
class JavaScriptVisitor(BaseVisitor):
    def visit_class_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        if not name_node:
            name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousClass"

        entity = ExtractedEntity(
            entity_type="class",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_function_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="function",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_method_definition(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "property_identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="method",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_import_statement(self, node: ASTNode):
        entity = ExtractedEntity(
            entity_type="import",
            name=node.text,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.entities.append(entity)


class TypeScriptVisitor(JavaScriptVisitor):
    def visit_interface_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        name = name_node.text if name_node else "AnonymousInterface"

        entity = ExtractedEntity(
            entity_type="interface",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()


# ----------------------------------------------------
# Java Extractor Visitor
# ----------------------------------------------------
class JavaVisitor(BaseVisitor):
    def visit_class_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousClass"

        entity = ExtractedEntity(
            entity_type="class",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_interface_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousInterface"

        entity = ExtractedEntity(
            entity_type="interface",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_method_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="method",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_constructor_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "constructor"

        entity = ExtractedEntity(
            entity_type="constructor",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_import_declaration(self, node: ASTNode):
        entity = ExtractedEntity(
            entity_type="import",
            name=node.text,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.entities.append(entity)


# ----------------------------------------------------
# C# Extractor Visitor
# ----------------------------------------------------
class CSharpVisitor(BaseVisitor):
    def visit_class_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousClass"

        entity = ExtractedEntity(
            entity_type="class",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_interface_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "AnonymousInterface"

        entity = ExtractedEntity(
            entity_type="interface",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_method_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="method",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_using_directive(self, node: ASTNode):
        entity = ExtractedEntity(
            entity_type="import",
            name=node.text,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.entities.append(entity)


# ----------------------------------------------------
# Go Extractor Visitor
# ----------------------------------------------------
class GoVisitor(BaseVisitor):
    def visit_function_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="function",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_method_declaration(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "field_identifier")
        if not name_node:
            name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="method",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_type_spec(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        name = name_node.text if name_node else "AnonymousType"

        struct_node = self.find_child_by_type(node, "struct_type")
        interface_node = self.find_child_by_type(node, "interface_type")
        entity_type = "struct" if struct_node else ("interface" if interface_node else "class")

        entity = ExtractedEntity(
            entity_type=entity_type,
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()


# ----------------------------------------------------
# Rust Extractor Visitor
# ----------------------------------------------------
class RustVisitor(BaseVisitor):
    def visit_struct_item(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        name = name_node.text if name_node else "AnonymousStruct"

        entity = ExtractedEntity(
            entity_type="struct",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_function_item(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="function",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_impl_item(self, node: ASTNode):
        # Implementation block - we do not push it as a distinct entity,
        # but descend so that methods are processed under the parent scope
        self.default_visit(node)


# ----------------------------------------------------
# C / C++ Extractor Visitor
# ----------------------------------------------------
class CppVisitor(BaseVisitor):
    def visit_class_specifier(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        name = name_node.text if name_node else "AnonymousClass"

        entity = ExtractedEntity(
            entity_type="class",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_struct_specifier(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "type_identifier")
        name = name_node.text if name_node else "AnonymousStruct"

        entity = ExtractedEntity(
            entity_type="struct",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_function_definition(self, node: ASTNode):
        # In C/C++, function definition has a declarator child containing name identifier
        declarator = self.find_child_by_type(node, "function_declarator")
        name = "anonymous"
        if declarator:
            name_node = self.find_child_by_type(declarator, "field_identifier")
            if not name_node:
                name_node = self.find_child_by_type(declarator, "identifier")
            if name_node:
                name = name_node.text

        entity = ExtractedEntity(
            entity_type="function",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()

    def visit_namespace_definition(self, node: ASTNode):
        name_node = self.find_child_by_type(node, "identifier")
        name = name_node.text if name_node else "anonymous"

        entity = ExtractedEntity(
            entity_type="namespace",
            name=name,
            start_line=node.start_line,
            end_line=node.end_line
        )
        self.push_scope(entity)
        self.default_visit(node)
        self.pop_scope()
