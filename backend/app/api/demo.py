from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.seed.vast_s5_aiml import seed_vast_s5_aiml_data
from backend.app.models.entities import (
    Department, ClassSection, Faculty, Room, Subject, FixedEvent, GeneratedTimetable, TimetableEntry
)

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.post("/load")
def load_demo(db: Session = Depends(get_db)):
    result = seed_vast_s5_aiml_data(db)
    return result

@router.post("/reset")
def reset_all(db: Session = Depends(get_db)):
    db.query(TimetableEntry).delete()
    db.query(GeneratedTimetable).delete()
    db.query(Subject).delete()
    db.query(FixedEvent).delete()
    db.query(Room).delete()
    db.query(Faculty).delete()
    db.query(ClassSection).delete()
    db.query(Department).delete()
    db.commit()
    return {"status": "success", "message": "All database tables cleared"}
