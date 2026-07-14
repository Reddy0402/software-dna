from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Determine engine arguments based on database dialect
engine_kwargs = {"pool_pre_ping": True}
if settings.SQLALCHEMY_DATABASE_URI and not settings.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# Create engine
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    **engine_kwargs
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
