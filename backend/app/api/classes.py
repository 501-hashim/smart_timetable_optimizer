import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import ClassSection
from backend.app.schemas.timetable_schemas import ClassSectionCreate, ClassSectionOut

router = APIRouter(prefix="/classes", tags=["Classes"])

@router.get("", response_model=List[ClassSectionOut])
def get_classes(db: Session = Depends(get_db)):
    return db.query(ClassSection).all()

@router.post("", response_model=ClassSectionOut)
def create_class(req: ClassSectionCreate, db: Session = Depends(get_db)):
    cs = ClassSection(
        id=f"class-{uuid.uuid4().hex[:8]}",
        name=req.name,
        department_id=req.department_id,
        student_count=req.student_count,
        academic_year=req.academic_year,
        semester=req.semester
    )
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return cs

@router.delete("/{class_id}")
def delete_class(class_id: str, db: Session = Depends(get_db)):
    cs = db.query(ClassSection).filter(ClassSection.id == class_id).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Class not found")
    db.delete(cs)
    db.commit()
    return {"success": True, "message": f"Class '{cs.name}' deleted"}
