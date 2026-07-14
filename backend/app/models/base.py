# Import all models here so that Alembic can auto-detect them.
from app.database.base_class import Base  # noqa
from app.models.repository import Repository  # noqa
from app.models.file import File  # noqa
