import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import Subject
from backend.app.schemas.timetable_schemas import SubjectCreate, SubjectOut

router = APIRouter(prefix="/subjects", tags=["Subjects"])

@router.get("", response_model=List[SubjectOut])
def get_subjects(class_id: str = None, db: Session = Depends(get_db)):
    q = db.query(Subject)
    if class_id:
        q = q.filter(Subject.class_section_id == class_id)
    items = q.all()
    res = []
    for s in items:
        out = SubjectOut(
            id=s.id,
            course_code=s.course_code,
            name=s.name,
            type=s.type,
            periods_per_week=s.periods_per_week,
            duration=s.duration,
            requires_lab=s.requires_lab,
            required_lab_type=s.required_lab_type,
            class_section_id=s.class_section_id,
            faculty_ids=json.loads(s.faculty_ids) if s.faculty_ids else [],
            preferred_days=json.loads(s.preferred_days) if s.preferred_days else [],
            preferred_periods=json.loads(s.preferred_periods) if s.preferred_periods else []
        )
        res.append(out)
    return res

@router.post("", response_model=SubjectOut)
def create_subject(req: SubjectCreate, db: Session = Depends(get_db)):
    s = Subject(
        id=f"sub-{uuid.uuid4().hex[:8]}",
        course_code=req.course_code,
        name=req.name,
        type=req.type,
        periods_per_week=req.periods_per_week,
        duration=req.duration,
        requires_lab=req.requires_lab,
        required_lab_type=req.required_lab_type,
        class_section_id=req.class_section_id,
        faculty_ids=json.dumps(req.faculty_ids),
        preferred_days=json.dumps(req.preferred_days),
        preferred_periods=json.dumps(req.preferred_periods)
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return SubjectOut(
        id=s.id,
        course_code=s.course_code,
        name=s.name,
        type=s.type,
        periods_per_week=s.periods_per_week,
        duration=s.duration,
        requires_lab=s.requires_lab,
        required_lab_type=s.required_lab_type,
        class_section_id=s.class_section_id,
        faculty_ids=req.faculty_ids,
        preferred_days=req.preferred_days,
        preferred_periods=req.preferred_periods
    )

@router.delete("/{subject_id}")
def delete_subject(subject_id: str, db: Session = Depends(get_db)):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found")
    db.delete(s)
    db.commit()
    return {"success": True, "message": f"Subject '{s.name}' deleted"}
