import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Faculty
from backend.app.schemas.timetable_schemas import FacultyCreate, FacultyOut

router = APIRouter(prefix="/faculty", tags=["Faculty"])

@router.get("", response_model=List[FacultyOut])
def get_faculty(db: Session = Depends(get_db)):
    items = db.query(Faculty).all()
    res = []
    for f in items:
        res.append(FacultyOut(
            id=f.id,
            name=f.name,
            short_name=f.short_name,
            email=f.email,
            department_id=f.department_id,
            unavailable_slots=json.loads(f.unavailable_slots) if f.unavailable_slots else [],
            preferred_slots=json.loads(f.preferred_slots) if f.preferred_slots else []
        ))
    return res

@router.post("", response_model=FacultyOut)
def create_faculty(req: FacultyCreate, db: Session = Depends(get_db)):
    f = Faculty(
        id=f"fac-{uuid.uuid4().hex[:8]}",
        name=req.name,
        short_name=req.short_name,
        email=req.email,
        department_id=req.department_id,
        unavailable_slots=json.dumps(req.unavailable_slots),
        preferred_slots=json.dumps(req.preferred_slots)
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return FacultyOut(
        id=f.id,
        name=f.name,
        short_name=f.short_name,
        email=f.email,
        department_id=f.department_id,
        unavailable_slots=req.unavailable_slots,
        preferred_slots=req.preferred_slots
    )

@router.put("/{faculty_id}", response_model=FacultyOut)
def update_faculty(faculty_id: str, req: FacultyCreate, db: Session = Depends(get_db)):
    f = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Faculty not found")
    f.name = req.name
    f.short_name = req.short_name
    f.email = req.email
    f.department_id = req.department_id
    f.unavailable_slots = json.dumps(req.unavailable_slots)
    f.preferred_slots = json.dumps(req.preferred_slots)
    db.commit()
    db.refresh(f)
    return FacultyOut(
        id=f.id,
        name=f.name,
        short_name=f.short_name,
        email=f.email,
        department_id=f.department_id,
        unavailable_slots=req.unavailable_slots,
        preferred_slots=req.preferred_slots
    )

@router.delete("/{faculty_id}")
def delete_faculty(faculty_id: str, db: Session = Depends(get_db)):
    f = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Faculty not found")
    db.delete(f)
    db.commit()
    return {"success": True, "message": f"Faculty '{f.name}' deleted"}
