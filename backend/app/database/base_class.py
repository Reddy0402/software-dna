import re
from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically in snake_case
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Convert CamelCase to snake_case
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
