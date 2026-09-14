from typing import List, Dict, Any, Tuple
from backend.app.schemas.timetable_schemas import ValidationViolation, ValidateResponse
from backend.app.algorithms.scoring import calculate_timetable_quality
from backend.app.algorithms.constraints import HardConstraintEngine

class IndependentValidator:
    """
    Completely independent verification engine for validating an academic timetable.
    Checks all mandatory hard constraints and computes quality score.
    """
    @staticmethod
    def validate(
        entries: List[Dict[str, Any]],
        class_section: Any,
        subjects: List[Any],
        faculty_list: List[Any],
        rooms: List[Any],
        fixed_events: List[Any],
        days: List[str],
        periods: List[int],
        soft_weights: Any = None
    ) -> ValidateResponse:
        violations: List[ValidationViolation] = []
        passed_checks: List[str] = []

        faculty_map = {f.id: f for f in faculty_list}
        room_map = {r.id: r for r in rooms}
        subject_map = {s.id: s for s in subjects}

        # 1. Check Fixed Events collisions
        fixed_slots: Dict[Tuple[str, int], str] = {}
        for fe in fixed_events:
            for p in range(fe.period, fe.period + fe.duration):
                fixed_slots[(fe.day, p)] = fe.name

        fixed_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            for p in range(p_start, p_start + dur):
                if (d, p) in fixed_slots:
                    fixed_violated = True
                    violations.append(ValidationViolation(
                        rule="FIXED_EVENT_OVERWRITE",
                        severity="ERROR",
                        message=f"Subject {entry.get('subject_code', entry['subject_id'])} overlaps with fixed event '{fixed_slots[(d, p)]}' on {d} Period {p}"
                    ))
        if not fixed_violated:
            passed_checks.append("Fixed college events (Lunch, Interval, Common Activity) fully preserved")

        # 2. Check Class Overlaps
        class_slots: Dict[Tuple[str, int], str] = {}
        class_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            for p in range(p_start, p_start + dur):
                slot = (d, p)
                if slot in class_slots:
                    class_violated = True
                    violations.append(ValidationViolation(
                        rule="CLASS_CONFLICT",
                        severity="ERROR",
                        message=f"Class {class_section.name} has double booking on {d} Period {p}"
                    ))
                else:
                    class_slots[slot] = entry["subject_id"]
        if not class_violated:
            passed_checks.append("No class/section schedule collisions")

        # 3. Check Faculty Overlaps and Availability
        faculty_slots: Dict[Tuple[str, str, int], str] = {}
        fac_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            for fid in entry.get("faculty_ids", []):
                # Availability
                fac_obj = faculty_map.get(fid)
                if fac_obj:
                    unavail = getattr(fac_obj, "unavailable_slots_parsed", [])
                    for u in unavail:
                        if u["day"] == d and int(u["period"]) in range(p_start, p_start + dur):
                            fac_violated = True
                            violations.append(ValidationViolation(
                                rule="FACULTY_UNAVAILABLE",
                                severity="ERROR",
                                message=f"Faculty {fac_obj.name} ({fac_obj.short_name}) is scheduled during marked unavailable slot on {d} Period {u['period']}"
                            ))

                # Collision
                for p in range(p_start, p_start + dur):
                    fkey = (fid, d, p)
                    if fkey in faculty_slots:
                        fac_violated = True
                        fac_name = fac_obj.short_name if fac_obj else fid
                        violations.append(ValidationViolation(
                            rule="FACULTY_CONFLICT",
                            severity="ERROR",
                            message=f"Faculty {fac_name} is double-booked on {d} Period {p}"
                        ))
                    else:
                        faculty_slots[fkey] = entry["subject_id"]
        if not fac_violated:
            passed_checks.append("No faculty teaching conflicts & availability respected")

        # 4. Check Room Overlaps, Type, and Capacity
        room_slots: Dict[Tuple[str, str, int], str] = {}
        room_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            rid = entry["room_id"]
            room = room_map.get(rid)
            sub = subject_map.get(entry["subject_id"])

            if room:
                if room.capacity < class_section.student_count:
                    room_violated = True
                    violations.append(ValidationViolation(
                        rule="ROOM_CAPACITY",
                        severity="ERROR",
                        message=f"Room {room.name} capacity ({room.capacity}) insufficient for class size ({class_section.student_count})"
                    ))

                if sub:
                    if sub.requires_lab and room.type != "LAB":
                        room_violated = True
                        violations.append(ValidationViolation(
                            rule="ROOM_TYPE_MISMATCH",
                            severity="ERROR",
                            message=f"Lab subject {sub.name} scheduled in non-laboratory room {room.name}"
                        ))

            for p in range(p_start, p_start + dur):
                rkey = (rid, d, p)
                if rkey in room_slots:
                    room_violated = True
                    violations.append(ValidationViolation(
                        rule="ROOM_CONFLICT",
                        severity="ERROR",
                        message=f"Room {room.name if room else rid} is double-booked on {d} Period {p}"
                    ))
                else:
                    room_slots[rkey] = entry["subject_id"]
        if not room_violated:
            passed_checks.append("No room collisions, room types & capacities valid")

        # 5. Check Subject Weekly Hours Requirements
        subj_periods_scheduled: Dict[str, int] = {}
        for entry in entries:
            sid = entry["subject_id"]
            subj_periods_scheduled[sid] = subj_periods_scheduled.get(sid, 0) + entry["duration"]

        req_violated = False
        for sub in subjects:
            scheduled = subj_periods_scheduled.get(sub.id, 0)
            req_hours = getattr(sub, "hours_per_week", None)
            if req_hours is None:
                req_hours = sub.periods_per_week
            if scheduled != req_hours:
                req_violated = True
                violations.append(ValidationViolation(
                    rule="REQUIRED_HOURS_MISMATCH",
                    severity="ERROR",
                    message=f"Subject {sub.course_code} ({sub.name}) requires {req_hours} hours/week but only {scheduled} were scheduled"
                ))
        if not req_violated:
            passed_checks.append("All subject weekly teaching hours exactly satisfied")

        # 6. Check Multi-Period Lab Continuity and Break Boundaries
        lab_break_violated = False
        for entry in entries:
            dur = entry.get("duration", 1)
            if dur > 1:
                d = entry["day"]
                p_start = entry["period"]
                if HardConstraintEngine.is_block_crossing_breaks(d, p_start, dur):
                    lab_break_violated = True
                    violations.append(ValidationViolation(
                        rule="BLOCK_CROSSING_BREAK",
                        severity="ERROR",
                        message=f"Multi-period session for {entry.get('subject_id')} crosses break boundary on {d} Period {p_start} (duration {dur})"
                    ))
        if not lab_break_violated:
            passed_checks.append("All laboratory and multi-period sessions are continuous on same day without crossing breaks")

        is_valid = len(violations) == 0
        quality_score, _, _ = calculate_timetable_quality(entries, soft_weights, days, periods)

        summary = (
            "VALID TIMETABLE: All hard constraints satisfied with 0 conflicts."
            if is_valid
            else f"INVALID TIMETABLE: Detected {len(violations)} constraint violation(s)."
        )

        return ValidateResponse(
            is_valid=is_valid,
            quality_score=quality_score,
            violations=violations,
            passed_checks=passed_checks,
            summary=summary
        )

    @staticmethod
    def validate_multiclass(
        entries: List[Dict[str, Any]],
        class_sections: List[Any],
        subjects: List[Any],
        faculty_list: List[Any],
        rooms: List[Any],
        fixed_events: List[Any],
        days: List[str],
        periods: List[int],
        soft_weights: Any = None
    ) -> ValidateResponse:
        violations: List[ValidationViolation] = []
        passed_checks: List[str] = []

        class_map = {c.id: c for c in class_sections}
        faculty_map = {f.id: f for f in faculty_list}
        room_map = {r.id: r for r in rooms}
        subject_map = {s.id: s for s in subjects}

        # 1. Check Fixed Events collisions across all classes
        fixed_slots: Dict[Tuple[str, int], str] = {}
        for fe in fixed_events:
            for p in range(fe.period, fe.period + fe.duration):
                fixed_slots[(fe.day, p)] = fe.name

        fixed_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            cid = entry.get("class_section_id")
            cls = class_map.get(cid)
            cls_name = cls.name if cls else (cid or "Class")
            sub = subject_map.get(entry.get("subject_id"))
            sub_code = sub.course_code if sub else entry.get("subject_id", "")
            for p in range(p_start, p_start + dur):
                if (d, p) in fixed_slots:
                    fixed_violated = True
                    violations.append(ValidationViolation(
                        rule="FIXED_EVENT_OVERWRITE",
                        severity="ERROR",
                        message=f"Class {cls_name} subject {sub_code} overlaps with fixed event '{fixed_slots[(d, p)]}' on {d} Period {p}"
                    ))
        if not fixed_violated:
            passed_checks.append("Fixed college events (Lunch, Interval, Common Activity) fully preserved across all classes")

        # 2. Check Class Overlaps (No internal class collision)
        class_slots: Dict[Tuple[str, str, int], str] = {}
        class_violated = False
        for entry in entries:
            cid = entry.get("class_section_id")
            cls = class_map.get(cid)
            cls_name = cls.name if cls else (cid or "Class")
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            for p in range(p_start, p_start + dur):
                slot = (cid, d, p)
                if slot in class_slots:
                    class_violated = True
                    violations.append(ValidationViolation(
                        rule="CLASS_CONFLICT",
                        severity="ERROR",
                        message=f"Class {cls_name} has double booking on {d} Period {p}"
                    ))
                else:
                    class_slots[slot] = entry.get("subject_id")
        if not class_violated:
            passed_checks.append("No class/section schedule collisions (all class slots non-overlapping)")

        # 3. Check Cross-Class Faculty Overlaps and Availability
        faculty_slots: Dict[Tuple[str, str, int], Dict[str, str]] = {}
        fac_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            cid = entry.get("class_section_id")
            cls = class_map.get(cid)
            cls_name = cls.name if cls else (cid or "Class")
            sub = subject_map.get(entry.get("subject_id"))
            sub_code = sub.course_code if sub else ""

            for fid in entry.get("faculty_ids", []):
                fac_obj = faculty_map.get(fid)
                fac_name = fac_obj.short_name if fac_obj else fid
                if fac_obj:
                    unavail = getattr(fac_obj, "unavailable_slots_parsed", [])
                    for u in unavail:
                        if u["day"] == d and int(u["period"]) in range(p_start, p_start + dur):
                            fac_violated = True
                            violations.append(ValidationViolation(
                                rule="FACULTY_UNAVAILABLE",
                                severity="ERROR",
                                message=f"Faculty {fac_obj.name} ({fac_name}) is scheduled during marked unavailable slot on {d} Period {u['period']} for {cls_name}"
                            ))

                for p in range(p_start, p_start + dur):
                    fkey = (fid, d, p)
                    if fkey in faculty_slots:
                        fac_violated = True
                        prev = faculty_slots[fkey]
                        violations.append(ValidationViolation(
                            rule="FACULTY_CONFLICT",
                            severity="ERROR",
                            message=f"Shared Faculty {fac_name} has cross-class conflict on {d} Period {p}: scheduled in {prev['class_name']} ({prev['subject']}) and {cls_name} ({sub_code})"
                        ))
                    else:
                        faculty_slots[fkey] = {
                            "class_name": cls_name,
                            "subject": sub_code
                        }
        if not fac_violated:
            passed_checks.append("Zero cross-class faculty conflicts (all shared faculty non-overlapping)")

        # 4. Check Room Overlaps, Type, and Capacity across classes
        room_slots: Dict[Tuple[str, str, int], Dict[str, str]] = {}
        room_violated = False
        for entry in entries:
            d = entry["day"]
            p_start = entry["period"]
            dur = entry["duration"]
            rid = entry.get("room_id")
            room = room_map.get(rid)
            room_name = room.name if room else rid
            cid = entry.get("class_section_id")
            cls = class_map.get(cid)
            cls_name = cls.name if cls else (cid or "Class")
            sub = subject_map.get(entry.get("subject_id"))
            sub_code = sub.course_code if sub else ""

            if room and cls:
                if room.capacity < cls.student_count:
                    room_violated = True
                    violations.append(ValidationViolation(
                        rule="ROOM_CAPACITY",
                        severity="ERROR",
                        message=f"Room {room.name} capacity ({room.capacity}) insufficient for {cls_name} size ({cls.student_count})"
                    ))
            if room and sub:
                if sub.requires_lab and room.type != "LAB":
                    room_violated = True
                    violations.append(ValidationViolation(
                        rule="ROOM_TYPE_MISMATCH",
                        severity="ERROR",
                        message=f"Lab subject {sub.name} for {cls_name} scheduled in non-laboratory room {room.name}"
                    ))

            for p in range(p_start, p_start + dur):
                rkey = (rid, d, p)
                if rkey in room_slots:
                    room_violated = True
                    prev = room_slots[rkey]
                    violations.append(ValidationViolation(
                        rule="ROOM_CONFLICT",
                        severity="ERROR",
                        message=f"Room {room_name} has cross-class conflict on {d} Period {p}: double-booked for {prev['class_name']} ({prev['subject']}) and {cls_name} ({sub_code})"
                    ))
                else:
                    room_slots[rkey] = {
                        "class_name": cls_name,
                        "subject": sub_code
                    }
        if not room_violated:
            passed_checks.append("Zero room collisions, room types & capacities valid across all classes")

        # 5. Check Subject Weekly Hours Requirements
        subj_periods_scheduled: Dict[str, int] = {}
        for entry in entries:
            sid = entry.get("subject_id")
            subj_periods_scheduled[sid] = subj_periods_scheduled.get(sid, 0) + entry["duration"]

        req_violated = False
        for sub in subjects:
            scheduled = subj_periods_scheduled.get(sub.id, 0)
            req_hours = getattr(sub, "hours_per_week", None)
            if req_hours is None:
                req_hours = sub.periods_per_week
            if scheduled != req_hours:
                req_violated = True
                cls = class_map.get(sub.class_section_id)
                cls_str = f" for {cls.name}" if cls else ""
                violations.append(ValidationViolation(
                    rule="REQUIRED_HOURS_MISMATCH",
                    severity="ERROR",
                    message=f"Subject {sub.course_code} ({sub.name}){cls_str} requires {req_hours} hours/week but only {scheduled} were scheduled"
                ))
        if not req_violated:
            passed_checks.append("All subject weekly teaching hours exactly satisfied across all classes")

        # 6. Check Multi-Period Lab Continuity and Break Boundaries across classes
        lab_break_violated = False
        for entry in entries:
            dur = entry.get("duration", 1)
            if dur > 1:
                d = entry["day"]
                p_start = entry["period"]
                if HardConstraintEngine.is_block_crossing_breaks(d, p_start, dur):
                    lab_break_violated = True
                    cid = entry.get("class_section_id")
                    cls = class_map.get(cid)
                    cls_name = cls.name if cls else (cid or "Class")
                    sub = subject_map.get(entry.get("subject_id"))
                    sub_name = sub.name if sub else entry.get("subject_id", "")
                    violations.append(ValidationViolation(
                        rule="BLOCK_CROSSING_BREAK",
                        severity="ERROR",
                        message=f"Multi-period lab session for {cls_name} ({sub_name}) crosses break boundary on {d} Period {p_start} (duration {dur})"
                    ))
        if not lab_break_violated:
            passed_checks.append("All laboratory and multi-period sessions are continuous on same day without crossing breaks")

        is_valid = len(violations) == 0
        quality_score, _, _ = calculate_timetable_quality(entries, soft_weights, days, periods)

        summary = (
            f"GLOBAL VALIDATION PASSED: All hard constraints satisfied across all {len(class_sections)} classes with 0 collisions."
            if is_valid
            else f"GLOBAL VALIDATION FAILED: Detected {len(violations)} cross-class or schedule violation(s)."
        )

        return ValidateResponse(
            is_valid=is_valid,
            quality_score=quality_score,
            violations=violations,
            passed_checks=passed_checks,
            summary=summary
        )

