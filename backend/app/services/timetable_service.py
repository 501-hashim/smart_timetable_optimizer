import json
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    ClassSection, Subject, Faculty, Room, FixedEvent, GeneratedTimetable, TimetableEntry, Department
)
from backend.app.schemas.timetable_schemas import (
    GenerateRequest, GenerateResponse, ValidateResponse, VisualizerResponse,
    MultiClassWizardRequest, CombinedTimetableOut, FacultyScheduleOut, RoomScheduleOut, CollisionReportOut
)
from backend.app.algorithms.backtracking import BacktrackingEngine
from backend.app.algorithms.validator import IndependentValidator

def parse_model_json(obj: Any, field_name: str, default: Any):
    val = getattr(obj, field_name, None)
    if not val:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default

def prepare_subjects(db_subjects: List[Subject]) -> List[Subject]:
    for s in db_subjects:
        s.faculty_ids_parsed = parse_model_json(s, "faculty_ids", [])
        s.preferred_days_parsed = parse_model_json(s, "preferred_days", [])
        s.preferred_periods_parsed = parse_model_json(s, "preferred_periods", [])
        s.consecutive = getattr(s, "consecutive", False)
        s.hours_per_week = s.periods_per_week
    return db_subjects

def prepare_faculty(db_faculty: List[Faculty]) -> List[Faculty]:
    for f in db_faculty:
        f.unavailable_slots_parsed = parse_model_json(f, "unavailable_slots", [])
        f.preferred_slots_parsed = parse_model_json(f, "preferred_slots", [])
    return db_faculty

class TimetableService:
    @staticmethod
    def generate(db: Session, req: GenerateRequest) -> GenerateResponse:
        class_sec = db.query(ClassSection).filter(ClassSection.id == req.class_section_id).first()
        if not class_sec:
            return GenerateResponse(
                success=False,
                message=f"Class section '{req.class_section_id}' not found",
                statistics={"tasks": 0, "candidates_tested": 0, "backtracking_steps": 0, "valid_assignments": 0}
            )

        subjects = prepare_subjects(db.query(Subject).filter(Subject.class_section_id == class_sec.id).all())
        if not subjects:
            return GenerateResponse(
                success=False,
                message="No subjects found for this class section. Please add subjects first.",
                statistics={"tasks": 0, "candidates_tested": 0, "backtracking_steps": 0, "valid_assignments": 0}
            )

        faculty_list = prepare_faculty(db.query(Faculty).all())
        rooms = db.query(Room).all()
        fixed_events = db.query(FixedEvent).filter(
            (FixedEvent.class_section_id == class_sec.id) | (FixedEvent.class_section_id == None)
        ).all()

        engine = BacktrackingEngine(
            class_section=class_sec,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=req.days,
            periods=req.periods,
            soft_weights=req.soft_weights,
            optimization_enabled=req.optimization_enabled,
            search_limit=req.search_limit
        )

        success, schedule, stats, trace = engine.run()

        if not success or schedule is None:
            return GenerateResponse(
                success=False,
                message="No valid timetable could be generated with the current constraints.",
                statistics=stats,
                diagnostics={"top_failure_reasons": engine.diagnostic_failures}
            )

        # Clear previous timetables for this class
        old_tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id == class_sec.id).all()
        for tt in old_tt:
            db.delete(tt)
        db.flush()

        # Save to database
        tt_id = f"tt-{uuid.uuid4().hex[:8]}"
        new_tt = GeneratedTimetable(
            id=tt_id,
            class_section_id=class_sec.id,
            name=f"{class_sec.name} Optimized Timetable",
            status="VALID",
            score=stats.get("quality_score", 100.0),
            statistics=json.dumps(stats)
        )
        db.add(new_tt)
        db.flush()

        entries_out = []
        for e in schedule:
            db_entry = TimetableEntry(
                id=f"entry-{uuid.uuid4().hex[:8]}",
                timetable_id=tt_id,
                day=e["day"],
                period=e["period"],
                duration=e["duration"],
                class_section_id=class_sec.id,
                subject_id=e["subject_id"],
                room_id=e["room_id"],
                faculty_ids=json.dumps(e["faculty_ids"])
            )
            db.add(db_entry)
            entries_out.append(e)

        db.commit()

        return GenerateResponse(
            success=True,
            timetable_id=tt_id,
            score=stats.get("quality_score", 100.0),
            message="Timetable generated successfully using custom Backtracking Algorithm.",
            entries=entries_out,
            statistics=stats
        )

    @staticmethod
    def get_visualization(db: Session, class_section_id: str, days: List[str], periods: List[int]) -> VisualizerResponse:
        class_sec = db.query(ClassSection).filter(ClassSection.id == class_section_id).first()
        subjects = prepare_subjects(db.query(Subject).filter(Subject.class_section_id == class_section_id).all())
        faculty_list = prepare_faculty(db.query(Faculty).all())
        rooms = db.query(Room).all()
        fixed_events = db.query(FixedEvent).filter(
            (FixedEvent.class_section_id == class_section_id) | (FixedEvent.class_section_id == None)
        ).all()

        engine = BacktrackingEngine(
            class_section=class_sec,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=days,
            periods=periods,
            optimization_enabled=False,  # Single path for visualization
            search_limit=500
        )
        success, schedule, stats, trace = engine.run()

        return VisualizerResponse(
            success=success,
            total_steps=len(trace),
            steps=trace,
            final_stats=stats
        )

    @staticmethod
    def validate(db: Session, timetable_id: str) -> ValidateResponse:
        tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.id == timetable_id).first()
        if not tt:
            return ValidateResponse(
                is_valid=False,
                quality_score=0.0,
                violations=[],
                passed_checks=[],
                summary=f"Timetable '{timetable_id}' not found"
            )

        class_sec = db.query(ClassSection).filter(ClassSection.id == tt.class_section_id).first()
        subjects = prepare_subjects(db.query(Subject).filter(Subject.class_section_id == class_sec.id).all())
        faculty_list = prepare_faculty(db.query(Faculty).all())
        rooms = db.query(Room).all()
        fixed_events = db.query(FixedEvent).filter(
            (FixedEvent.class_section_id == class_sec.id) | (FixedEvent.class_section_id == None)
        ).all()

        entries_data = []
        for e in tt.entries:
            entries_data.append({
                "day": e.day,
                "period": e.period,
                "duration": e.duration,
                "class_section_id": e.class_section_id,
                "subject_id": e.subject_id,
                "room_id": e.room_id,
                "faculty_ids": parse_model_json(e, "faculty_ids", [])
            })

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = [1, 2, 3, 4, 5, 6, 7]

        return IndependentValidator.validate(
            entries=entries_data,
            class_section=class_sec,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=days,
            periods=periods
        )

    @staticmethod
    def setup_and_generate_multiclass(db: Session, req: MultiClassWizardRequest) -> Dict[str, Any]:
        # 1. Departments & Class Sections
        class_name_to_obj = {}
        class_ids = []
        for c_data in req.classes:
            dept_code = c_data.department_code.strip().upper()
            dept = db.query(Department).filter(Department.code == dept_code).first()
            if not dept:
                dept = Department(
                    id=f"dept-{uuid.uuid4().hex[:8]}",
                    name=c_data.department_name.strip() if c_data.department_name else dept_code,
                    code=dept_code
                )
                db.add(dept)
                db.flush()

            class_sec = db.query(ClassSection).filter(ClassSection.name == c_data.name.strip()).first()
            if not class_sec:
                class_sec = ClassSection(
                    id=f"class-{uuid.uuid4().hex[:8]}",
                    name=c_data.name.strip(),
                    department_id=dept.id,
                    student_count=c_data.student_count,
                    academic_year=c_data.academic_year.strip(),
                    semester=c_data.semester.strip()
                )
                db.add(class_sec)
                db.flush()
            else:
                class_sec.department_id = dept.id
                class_sec.student_count = c_data.student_count
                class_sec.academic_year = c_data.academic_year.strip()
                class_sec.semester = c_data.semester.strip()
                db.flush()

            class_name_to_obj[class_sec.name] = class_sec
            class_ids.append(class_sec.id)

        # 2. Shared Faculty Directory
        fac_short_map = {}
        for f_data in req.faculty:
            short = f_data.short_name.strip().upper()
            fac = db.query(Faculty).filter(Faculty.short_name == short).first()
            if not fac:
                fac = Faculty(
                    id=f"fac-{uuid.uuid4().hex[:8]}",
                    name=f_data.name.strip(),
                    short_name=short,
                    email=f_data.email or "",
                    unavailable_slots=json.dumps(f_data.unavailable_slots),
                    preferred_slots=json.dumps(f_data.preferred_slots)
                )
                db.add(fac)
                db.flush()
            else:
                fac.name = f_data.name.strip()
                fac.unavailable_slots = json.dumps(f_data.unavailable_slots)
                fac.preferred_slots = json.dumps(f_data.preferred_slots)
                db.flush()
            fac_short_map[short] = fac.id

        # 3. Classrooms & Laboratories Directory
        room_name_map = {}
        for r_data in req.rooms:
            r_name = r_data.name.strip()
            room = db.query(Room).filter(Room.name == r_name).first()
            if not room:
                room = Room(
                    id=f"room-{uuid.uuid4().hex[:8]}",
                    name=r_name,
                    type=r_data.type.strip().upper(),
                    lab_type=r_data.lab_type,
                    capacity=r_data.capacity,
                    building=r_data.building
                )
                db.add(room)
                db.flush()
            else:
                room.type = r_data.type.strip().upper()
                room.lab_type = r_data.lab_type
                room.capacity = r_data.capacity
                room.building = r_data.building
                db.flush()
            room_name_map[r_name] = room.id

        # 4. Subjects per Class
        db.query(Subject).filter(Subject.class_section_id.in_(class_ids)).delete(synchronize_session=False)
        db.flush()

        for s_data in req.subjects:
            target_class = class_name_to_obj.get(s_data.class_name.strip())
            if not target_class:
                continue
            fac_ids = [fac_short_map[sh.strip().upper()] for sh in s_data.faculty_shorts if sh.strip().upper() in fac_short_map]
            hours = int(s_data.hours_per_week) if s_data.hours_per_week is not None else int(s_data.periods_per_week)
            is_consec = bool(getattr(s_data, "consecutive", False)) or (int(s_data.duration) > 1)
            sub = Subject(
                id=f"sub-{uuid.uuid4().hex[:8]}",
                course_code=s_data.course_code.strip(),
                name=s_data.name.strip(),
                type=s_data.type.strip().upper(),
                periods_per_week=hours,
                duration=int(s_data.duration),
                consecutive=is_consec,
                requires_lab=bool(s_data.requires_lab),
                required_lab_type=s_data.required_lab_type,
                class_section_id=target_class.id,
                faculty_ids=json.dumps(fac_ids),
                preferred_days=json.dumps(s_data.preferred_days),
                preferred_periods=json.dumps(s_data.preferred_periods)
            )
            db.add(sub)
        db.flush()

        # 5. Fixed Events
        db.query(FixedEvent).filter(
            (FixedEvent.class_section_id.in_(class_ids)) | (FixedEvent.class_section_id == None)
        ).delete(synchronize_session=False)
        db.flush()

        if req.fixed_events:
            for fe_data in req.fixed_events:
                cid = None
                if fe_data.class_name and fe_data.class_name.upper() != "ALL":
                    matched_cls = class_name_to_obj.get(fe_data.class_name.strip())
                    if matched_cls:
                        cid = matched_cls.id
                fe = FixedEvent(
                    id=f"fix-{uuid.uuid4().hex[:8]}",
                    name=fe_data.name.strip(),
                    class_section_id=cid,
                    day=fe_data.day.strip(),
                    period=int(fe_data.period),
                    duration=int(fe_data.duration),
                    event_type=fe_data.event_type
                )
                db.add(fe)
            db.flush()

        db.commit()

        # 6. Prepare All Entities for Simultaneous Solving
        classes = db.query(ClassSection).filter(ClassSection.id.in_(class_ids)).all()
        subjects = prepare_subjects(db.query(Subject).filter(Subject.class_section_id.in_(class_ids)).all())
        if fac_short_map:
            faculty_list = prepare_faculty(db.query(Faculty).filter(Faculty.id.in_(list(fac_short_map.values()))).all())
        else:
            faculty_list = prepare_faculty(db.query(Faculty).all())

        if room_name_map:
            rooms = db.query(Room).filter(Room.id.in_(list(room_name_map.values()))).all()
        else:
            rooms = db.query(Room).all()

        fixed_events = db.query(FixedEvent).filter(
            (FixedEvent.class_section_id.in_(class_ids)) | (FixedEvent.class_section_id == None)
        ).all()

        # 7. Run Simultaneous Multi-Class Backtracking
        engine = BacktrackingEngine(
            class_sections=classes,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=req.days,
            periods=req.periods,
            soft_weights=req.soft_weights,
            optimization_enabled=req.optimization_enabled,
            search_limit=req.search_limit
        )
        success, schedule, stats, trace = engine.run()

        if not success or schedule is None:
            return {
                "success": False,
                "message": "Unable to schedule all classes simultaneously without constraint violations. Try adjusting constraints or increasing search limit.",
                "statistics": stats,
                "diagnostics": {"top_failure_reasons": engine.diagnostic_failures}
            }

        # 8. Clear previous generated timetables for these classes
        db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id.in_(class_ids)).delete(synchronize_session=False)
        db.flush()

        class_tt_map = {}
        for cls in classes:
            tt_id = f"tt-{uuid.uuid4().hex[:8]}"
            new_tt = GeneratedTimetable(
                id=tt_id,
                class_section_id=cls.id,
                name=f"{cls.name} Schedule",
                status="VALID",
                score=stats.get("quality_score", 100.0),
                statistics=json.dumps(stats)
            )
            db.add(new_tt)
            class_tt_map[cls.id] = tt_id
        db.flush()

        # 9. Insert TimetableEntry rows
        entries_out = []
        for e in schedule:
            cid = e["class_section_id"]
            tt_id = class_tt_map[cid]
            db_entry = TimetableEntry(
                id=f"entry-{uuid.uuid4().hex[:8]}",
                timetable_id=tt_id,
                day=e["day"],
                period=e["period"],
                duration=e["duration"],
                class_section_id=cid,
                subject_id=e["subject_id"],
                room_id=e["room_id"],
                faculty_ids=json.dumps(e["faculty_ids"])
            )
            db.add(db_entry)
            entries_out.append(e)

        db.commit()

        # 10. Run Independent Multi-Class Validation
        val_res = IndependentValidator.validate_multiclass(
            entries=entries_out,
            class_sections=classes,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=req.days,
            periods=req.periods
        )

        return {
            "success": True,
            "message": f"All {len(classes)} classes scheduled simultaneously with 0 cross-class conflicts!",
            "classes": [{"id": c.id, "name": c.name, "timetable_id": class_tt_map[c.id]} for c in classes],
            "statistics": stats,
            "validation": {
                "is_valid": val_res.is_valid,
                "quality_score": val_res.quality_score,
                "violations": [v.dict() if hasattr(v, 'dict') else v.model_dump() for v in val_res.violations],
                "passed_checks": val_res.passed_checks,
                "summary": val_res.summary
            }
        }

    @staticmethod
    def get_multiclass_visualization(db: Session, days: List[str], periods: List[int]) -> VisualizerResponse:
        classes = db.query(ClassSection).all()
        class_ids = [c.id for c in classes]
        subjects = prepare_subjects(db.query(Subject).filter(Subject.class_section_id.in_(class_ids)).all())
        faculty_list = prepare_faculty(db.query(Faculty).all())
        rooms = db.query(Room).all()
        fixed_events = db.query(FixedEvent).filter(
            (FixedEvent.class_section_id.in_(class_ids)) | (FixedEvent.class_section_id == None)
        ).all()

        engine = BacktrackingEngine(
            class_sections=classes,
            subjects=subjects,
            faculty_list=faculty_list,
            rooms=rooms,
            fixed_events=fixed_events,
            days=days,
            periods=periods,
            optimization_enabled=False,
            search_limit=600
        )
        success, schedule, stats, trace = engine.run()

        return VisualizerResponse(
            success=success,
            total_steps=len(trace),
            steps=trace,
            final_stats=stats
        )

    @staticmethod
    def get_combined_view(db: Session) -> Dict[str, Any]:
        classes = db.query(ClassSection).order_by(ClassSection.name).all()
        class_map = {c.id: c for c in classes}
        faculty_map = {f.id: f for f in db.query(Faculty).all()}
        room_map = {r.id: r for r in db.query(Room).all()}
        subject_map = {s.id: s for s in db.query(Subject).all()}

        active_entries = []
        for cls in classes:
            tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id == cls.id).order_by(GeneratedTimetable.created_at.desc()).first()
            if tt:
                for e in tt.entries:
                    active_entries.append(e)

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        periods = [1, 2, 3, 4, 5, 6, 7]

        # matrix[day][period][class_id]
        matrix = {d: {p: {} for p in periods} for d in days}

        for e in active_entries:
            sub = subject_map.get(e.subject_id)
            room = room_map.get(e.room_id)
            fac_ids = parse_model_json(e, "faculty_ids", [])
            fac_names = [faculty_map[fid].short_name for fid in fac_ids if fid in faculty_map]

            for p in range(e.period, e.period + e.duration):
                if e.day in matrix and p in matrix[e.day]:
                    matrix[e.day][p][e.class_section_id] = {
                        "subject_name": sub.name if sub else "Unknown",
                        "subject_code": sub.course_code if sub else "N/A",
                        "subject_type": sub.type if sub else "THEORY",
                        "room_name": room.name if room else "N/A",
                        "faculty_short_names": fac_names,
                        "duration": e.duration,
                        "start_period": e.period,
                        "is_head": (p == e.period)
                    }

        return {
            "days": days,
            "periods": periods,
            "classes": [{"id": c.id, "name": c.name, "student_count": c.student_count, "academic_year": c.academic_year, "semester": c.semester} for c in classes],
            "matrix": matrix
        }

    @staticmethod
    def get_faculty_view(db: Session, faculty_id: Optional[str] = None) -> List[Dict[str, Any]]:
        faculties = db.query(Faculty).order_by(Faculty.short_name).all()
        if faculty_id:
            faculties = [f for f in faculties if f.id == faculty_id or f.short_name == faculty_id]

        class_map = {c.id: c.name for c in db.query(ClassSection).all()}
        room_map = {r.id: r.name for r in db.query(Room).all()}
        subject_map = {s.id: s for s in db.query(Subject).all()}

        active_entries = []
        for cid in class_map:
            tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id == cid).order_by(GeneratedTimetable.created_at.desc()).first()
            if tt:
                for e in tt.entries:
                    active_entries.append(e)

        result = []
        for fac in faculties:
            schedule_items = []
            total_periods = 0
            for e in active_entries:
                fids = parse_model_json(e, "faculty_ids", [])
                if fac.id in fids:
                    sub = subject_map.get(e.subject_id)
                    schedule_items.append({
                        "day": e.day,
                        "period": e.period,
                        "duration": e.duration,
                        "class_id": e.class_section_id,
                        "class_name": class_map.get(e.class_section_id, "Unknown"),
                        "subject_code": sub.course_code if sub else "N/A",
                        "subject_name": sub.name if sub else "Unknown",
                        "room_name": room_map.get(e.room_id, "N/A")
                    })
                    total_periods += e.duration

            result.append({
                "faculty_id": fac.id,
                "name": fac.name,
                "short_name": fac.short_name,
                "total_teaching_periods": total_periods,
                "schedule": schedule_items
            })
        return result

    @staticmethod
    def get_room_view(db: Session, room_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rooms = db.query(Room).order_by(Room.name).all()
        if room_id:
            rooms = [r for r in rooms if r.id == room_id or r.name == room_id]

        class_map = {c.id: c.name for c in db.query(ClassSection).all()}
        faculty_map = {f.id: f.short_name for f in db.query(Faculty).all()}
        subject_map = {s.id: s for s in db.query(Subject).all()}

        active_entries = []
        for cid in class_map:
            tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id == cid).order_by(GeneratedTimetable.created_at.desc()).first()
            if tt:
                for e in tt.entries:
                    active_entries.append(e)

        result = []
        for r in rooms:
            schedule_items = []
            total_periods = 0
            for e in active_entries:
                if e.room_id == r.id:
                    sub = subject_map.get(e.subject_id)
                    fids = parse_model_json(e, "faculty_ids", [])
                    fac_shorts = [faculty_map.get(fid, fid) for fid in fids]
                    schedule_items.append({
                        "day": e.day,
                        "period": e.period,
                        "duration": e.duration,
                        "class_id": e.class_section_id,
                        "class_name": class_map.get(e.class_section_id, "Unknown"),
                        "subject_code": sub.course_code if sub else "N/A",
                        "subject_name": sub.name if sub else "Unknown",
                        "faculty_names": fac_shorts
                    })
                    total_periods += e.duration

            result.append({
                "room_id": r.id,
                "name": r.name,
                "type": r.type,
                "capacity": r.capacity,
                "total_occupied_periods": total_periods,
                "schedule": schedule_items
            })
        return result

    @staticmethod
    def get_collision_report(db: Session) -> Dict[str, Any]:
        classes = db.query(ClassSection).all()
        class_map = {c.id: c.name for c in classes}
        faculty_list = db.query(Faculty).all()
        faculty_map = {f.id: f for f in faculty_list}
        room_list = db.query(Room).all()
        room_map = {r.id: r.name for r in room_list}
        subject_map = {s.id: s for s in db.query(Subject).all()}

        active_entries = []
        for c in classes:
            tt = db.query(GeneratedTimetable).filter(GeneratedTimetable.class_section_id == c.id).order_by(GeneratedTimetable.created_at.desc()).first()
            if tt:
                for e in tt.entries:
                    active_entries.append(e)

        faculty_slots = {}
        room_slots = {}
        class_slots = {}

        faculty_collisions = []
        room_collisions = []
        class_collisions = []

        faculty_stats = {f.id: {"name": f.name, "short_name": f.short_name, "periods": 0, "classes": set(), "conflicts": 0} for f in faculty_list}

        for e in active_entries:
            d = e.day
            p_start = e.period
            dur = e.duration
            cid = e.class_section_id
            cname = class_map.get(cid, "Unknown")
            sub = subject_map.get(e.subject_id)
            sub_code = sub.course_code if sub else "N/A"
            rname = room_map.get(e.room_id, "N/A")
            fids = parse_model_json(e, "faculty_ids", [])

            for p in range(p_start, p_start + dur):
                cslot = (cid, d, p)
                if cslot in class_slots:
                    class_collisions.append(f"Class {cname} double-booked on {d} Period {p}")
                else:
                    class_slots[cslot] = sub_code

                rslot = (e.room_id, d, p)
                if rslot in room_slots:
                    prev = room_slots[rslot]
                    room_collisions.append(f"Room {rname} double-booked on {d} Period {p}: {prev} vs {cname} ({sub_code})")
                else:
                    room_slots[rslot] = f"{cname} ({sub_code})"

                for fid in fids:
                    if fid in faculty_stats:
                        faculty_stats[fid]["classes"].add(cname)
                    fslot = (fid, d, p)
                    if fslot in faculty_slots:
                        prev = faculty_slots[fslot]
                        fac_name = faculty_map[fid].short_name if fid in faculty_map else fid
                        faculty_collisions.append(f"Faculty {fac_name} double-booked on {d} Period {p}: {prev} vs {cname} ({sub_code})")
                        if fid in faculty_stats:
                            faculty_stats[fid]["conflicts"] += 1
                    else:
                        faculty_slots[fslot] = f"{cname} ({sub_code})"

            for fid in fids:
                if fid in faculty_stats:
                    faculty_stats[fid]["periods"] += dur

        faculty_verification_table = []
        for fid, fstat in sorted(faculty_stats.items(), key=lambda x: x[1]["short_name"]):
            classes_list = sorted(list(fstat["classes"]))
            classes_str = ", ".join(classes_list) if classes_list else "None"
            status = "Conflict-Free" if fstat["conflicts"] == 0 else f"{fstat['conflicts']} Conflicts"
            faculty_verification_table.append({
                "faculty_id": fid,
                "name": fstat["name"],
                "short_name": fstat["short_name"],
                "weekly_periods": fstat["periods"],
                "classes_taught": classes_str,
                "conflicts_detected": fstat["conflicts"],
                "status": status
            })

        total_conflicts = len(faculty_collisions) + len(room_collisions) + len(class_collisions)
        is_conflict_free = (total_conflicts == 0)

        if is_conflict_free:
            summary = f"ZERO CONFLICTS: Verified all {len(classes)} classes, {len(faculty_list)} shared faculty, and {len(room_list)} rooms. Perfect multi-class timetable."
        else:
            summary = f"WARNING: Detected {total_conflicts} conflict(s) across schedules."

        return {
            "total_classes": len(classes),
            "total_faculty": len(faculty_list),
            "total_rooms": len(room_list),
            "total_entries": len(active_entries),
            "is_conflict_free": is_conflict_free,
            "faculty_collisions": faculty_collisions,
            "room_collisions": room_collisions,
            "class_collisions": class_collisions,
            "summary": summary,
            "faculty_verification_table": faculty_verification_table
        }

