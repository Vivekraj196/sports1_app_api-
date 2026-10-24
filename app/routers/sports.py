from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Sport
from app.schemas import SportResponse

router = APIRouter(prefix="/sports", tags=["Sports"])


@router.get("/", response_model=list[SportResponse])
def get_all_sports(db: Session = Depends(get_db)):
    """Return all sports registered in PlayRank."""
    sports = db.query(Sport).order_by(Sport.id).all()
    return sports