# app/routes/activities.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.routes.users import get_current_user
from app.schemas.activity import ActivityResponse
from app.models.user import User
from app.models.activity import Activity

router = APIRouter()

@router.get("/my", response_model=list[ActivityResponse])
def get_my_activities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    activities = db.query(Activity).filter(
        Activity.user_id == current_user.id
    ).order_by(Activity.created_at.desc()).all()
    
    return activities