import json
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.entities import (
    GeneratedTimetable, ClassSection, Subject, Faculty, Room, FixedEvent, Department, TimetableEntry
)
from backend.app.schemas.timetable_schemas import (
    GenerateRequest, GenerateResponse, ValidateResponse, VisualizerResponse,
    FacultyCreate, RoomCreate, SubjectCreate, FixedEventCreate,
    MultiClassWizardRequest, CombinedTimetableOut, FacultyScheduleOut, RoomScheduleOut, CollisionReportOut
)
from backend.app.services.timetable_service import TimetableService, parse_model_json
from backend.app.services.export_service import generate_excel_timetable, generate_pdf_timetable

router = APIRouter(prefix="/timetable", tags=["Timetable"])

class FullTimetableWizardRequest(BaseModel):
    department_name: str
    department_code: str
    class_name: str
    student_count: int = 60
    academic_year: str = "2026-27"
    semester: str = "Even"
    days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods: List[int] = [1, 2, 3, 4, 5, 6, 7]
    faculty: List[Dict[str, Any]] = []
    rooms: List[Dict[str, Any]] = []
    subjects: List[Dict[str, Any]] = []
    fixed_events: List[Dict[str, Any]] = []
    generate_now: bool = True

@router.get("/list/all")
def list_all_timetables(db: Session = Depends(get_db)):
    tt_list = db.query(GeneratedTimetable).order_by(GeneratedTimetable.created_at.desc()).all()
    classes = {c.id: c.name for c in db.query(ClassSection).all()}
    res = []
    for tt in tt_list:
        res.append({
            "id": tt.id,
            "name": tt.name,
            "class_section_id": tt.class_section_id,
            "class_name": classes.get(tt.class_section_id, "Unknown"),
            "score": tt.score,
            "status": tt.status,
            "created_at": tt.created_at.strftime("%Y-%m-%d %H:%M:%S") if tt.created_at else ""
        })
    return res

@router.post("/wizard/setup")
def setup_and_generate_new_timetable(req: FullTimetableWizardRequest, db: Session = Depends(get_db)):
    # 1. Department
    dept = db.query(Department).filter(Department.code == req.department_code.strip().upper()).first()
    if not dept:
        dept = Department(
            id=f"dept-{uuid.uuid4().hex[:8]}",
            name=req.department_name.strip(),
            code=req.department_code.strip().upper()
        )
        db.add(dept)
        db.flush()

    # 2. ClassSection
    class_sec = ClassSection(
        id=f"class-{uuid.uuid4().hex[:8]}",
        name=req.class_name.strip(),
        department_id=dept.id,
        student_count=req.student_count,
        academic_year=req.academic_year.strip(),
        semester=req.semester.strip()
    )
    db.add(class_sec)
    db.flush()

    # 3. Faculty
    faculty_id_map = {}
    for f_data in req.faculty:
        short = f_data.get("short_name", "").strip().upper()
        fac = db.query(Faculty).filter(Faculty.short_name == short).first()
        if not fac:
            fac = Faculty(
                id=f"fac-{uuid.uuid4().hex[:8]}",
                name=f_data.get("name", "").strip(),
                short_name=short,
                email=f_data.get("email", ""),
                department_id=dept.id,
                unavailable_slots=json.dumps(f_data.get("unavailable_slots", [])),
                preferred_slots=json.dumps(f_data.get("preferred_slots", []))
            )
            db.add(fac)
            db.flush()
        faculty_id_map[short] = fac.id
        faculty_id_map[f_data.get("name", "")] = fac.id

    # 4. Rooms
    room_id_map = {}
    for r_data in req.rooms:
        r_name = r_data.get("name", "").strip()
        room = db.query(Room).filter(Room.name == r_name).first()
        if not room:
            room = Room(
                id=f"room-{uuid.uuid4().hex[:8]}",
                name=r_name,
                type=r_data.get("type", "THEORY"),
                lab_type=r_data.get("lab_type"),
                capacity=r_data.get("capacity", 60),
                building=r_data.get("building", "Academic Block")
            )
            db.add(room)
            db.flush()
        room_id_map[r_name] = room.id

    # 5. Subjects
    for s_data in req.subjects:
        # Resolve faculty IDs
        fac_shorts = s_data.get("faculty_shorts", [])
        fac_ids = []
        for sh in fac_shorts:
            if sh in faculty_id_map:
                fac_ids.append(faculty_id_map[sh])

        sub = Subject(
            id=f"sub-{uuid.uuid4().hex[:8]}",
            course_code=s_data.get("course_code", "").strip(),
            name=s_data.get("name", "").strip(),
            type=s_data.get("type", "THEORY"),
            periods_per_week=int(s_data.get("periods_per_week", 3)),
            duration=int(s_data.get("duration", 1)),
            requires_lab=bool(s_data.get("requires_lab", False)),
            required_lab_type=s_data.get("required_lab_type"),
            class_section_id=class_sec.id,
            faculty_ids=json.dumps(fac_ids),
            preferred_days=json.dumps(s_data.get("preferred_days", [])),
            preferred_periods=json.dumps(s_data.get("preferred_periods", []))
        )
        db.add(sub)

    # 6. Fixed Events
    for fe_data in req.fixed_events:
        fe = FixedEvent(
            id=f"fix-{uuid.uuid4().hex[:8]}",
            name=fe_data.get("name", "College Event"),
            class_section_id=class_sec.id,
            day=fe_data.get("day", "Friday"),
            period=int(fe_data.get("period", 7)),
            duration=int(fe_data.get("duration", 1)),
            event_type=fe_data.get("event_type", "COMMON_ACTIVITY")
        )
        db.add(fe)

    db.commit()

    # 7. Generate if requested
    if req.generate_now:
        gen_req = GenerateRequest(
            class_section_id=class_sec.id,
            days=req.days,
            periods=req.periods,
            optimization_enabled=True,
            search_limit=2000
        )
        gen_result = TimetableService.generate(db, gen_req)
        return {
            "success": gen_result.success,
            "class_section_id": class_sec.id,
            "class_name": class_sec.name,
            "timetable_id": gen_result.timetable_id,
            "score": gen_result.score,
            "statistics": gen_result.statistics,
            "message": f"New timetable configuration for '{class_sec.name}' created and generated!"
        }

    return {
        "success": True,
        "class_section_id": class_sec.id,
        "class_name": class_sec.name,
        "message": f"New timetable configuration for '{class_sec.name}' created successfully!"
    }

@router.post("/generate", response_model=GenerateResponse)
def generate_timetable(req: GenerateRequest, db: Session = Depends(get_db)):
    return TimetableService.generate(db, req)

@router.get("/visualize/multiclass", response_model=VisualizerResponse)
def get_multiclass_visualization(db: Session = Depends(get_db)):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    return TimetableService.get_multiclass_visualization(db, days, periods)

@router.get("/visualize/{class_id}", response_model=VisualizerResponse)
def get_visualization(class_id: str, db: Session = Depends(get_db)):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    return TimetableService.get_visualization(db, class_id, days, periods)

@router.get("/{timetable_id}")
def get_timetable(timetable_id: str, db: Session = Depends(get_db)):
    tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.id == timetable_id).first()
    if not tt:
        raise HTTPException(status_code=404, detail="Timetable not found")

    faculty_map = {f.id: f for f in db.query(Faculty).all()}
    room_map = {r.id: r for r in db.query(Room).all()}
    subject_map = {s.id: s for s in db.query(Subject).all()}
    class_sec = db.query(ClassSection).filter(ClassSection.id == tt.class_section_id).first()

    entries_out = []
    for e in tt.entries:
        fac_ids = parse_model_json(e, "faculty_ids", [])
        sub = subject_map.get(e.subject_id)
        room = room_map.get(e.room_id)
        entries_out.append({
            "day": e.day,
            "period": e.period,
            "duration": e.duration,
            "class_section_id": e.class_section_id,
            "subject_id": e.subject_id,
            "subject_name": sub.name if sub else "Unknown",
            "subject_code": sub.course_code if sub else "N/A",
            "subject_type": sub.type if sub else "THEORY",
            "room_id": e.room_id,
            "room_name": room.name if room else "Unknown",
            "faculty_ids": fac_ids,
            "faculty_names": [faculty_map[fid].name for fid in fac_ids if fid in faculty_map],
            "faculty_short_names": [faculty_map[fid].short_name for fid in fac_ids if fid in faculty_map]
        })

    return {
        "id": tt.id,
        "class_section_id": tt.class_section_id,
        "class_name": class_sec.name if class_sec else "Unknown",
        "academic_year": class_sec.academic_year if class_sec else "2026-27",
        "name": tt.name,
        "status": tt.status,
        "score": tt.score,
        "statistics": json.loads(tt.statistics) if tt.statistics else {},
        "entries": entries_out
    }

@router.post("/validate/{timetable_id}", response_model=ValidateResponse)
def validate_timetable(timetable_id: str, db: Session = Depends(get_db)):
    return TimetableService.validate(db, timetable_id)

@router.get("/{timetable_id}/export/excel")
@router.get("/export/excel/{timetable_id}")
def export_excel(timetable_id: str, db: Session = Depends(get_db)):
    tt_data = get_timetable(timetable_id, db)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    fixed_events = db.query(FixedEvent).filter(
        (FixedEvent.class_section_id == tt_data["class_section_id"]) | (FixedEvent.class_section_id == None)
    ).all()

    excel_bytes = generate_excel_timetable(
        class_name=tt_data["class_name"],
        academic_year=tt_data["academic_year"],
        entries=tt_data["entries"],
        days=days,
        periods=periods,
        fixed_events=fixed_events
    )

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={tt_data['class_name']}_timetable.xlsx"}
    )

@router.get("/{timetable_id}/export/pdf")
@router.get("/export/pdf/{timetable_id}")
def export_pdf(timetable_id: str, db: Session = Depends(get_db)):
    tt_data = get_timetable(timetable_id, db)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    fixed_events = db.query(FixedEvent).filter(
        (FixedEvent.class_section_id == tt_data["class_section_id"]) | (FixedEvent.class_section_id == None)
    ).all()

    pdf_bytes = generate_pdf_timetable(
        class_name=tt_data["class_name"],
        academic_year=tt_data["academic_year"],
        entries=tt_data["entries"],
        days=days,
        periods=periods,
        fixed_events=fixed_events
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={tt_data['class_name']}_timetable.pdf"}
    )

# ----------------- Multi-Class Endpoints -----------------

@router.post("/wizard/setup-multiclass")
def setup_and_generate_multiclass_timetables(req: MultiClassWizardRequest, db: Session = Depends(get_db)):
    return TimetableService.setup_and_generate_multiclass(db, req)

@router.get("/view/combined")
def get_combined_all_classes_view(db: Session = Depends(get_db)):
    return TimetableService.get_combined_view(db)

@router.get("/view/faculty")
def get_faculty_schedule_view(faculty_id: Optional[str] = None, db: Session = Depends(get_db)):
    return TimetableService.get_faculty_view(db, faculty_id)

@router.get("/view/rooms")
def get_room_schedule_view(room_id: Optional[str] = None, db: Session = Depends(get_db)):
    return TimetableService.get_room_view(db, room_id)

@router.get("/reports/collisions")
def get_collision_audit_report(db: Session = Depends(get_db)):
    return TimetableService.get_collision_report(db)

