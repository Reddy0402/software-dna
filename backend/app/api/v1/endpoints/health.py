from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from app.api.deps import get_db

router = APIRouter()


@router.get("/health", status_code=200)
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Check API health and database connectivity.
    """
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "active",
        "database": db_status
    }
