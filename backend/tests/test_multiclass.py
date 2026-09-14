import pytest
from backend.app.algorithms.backtracking import BacktrackingEngine
from backend.app.algorithms.validator import IndependentValidator

class MockClassSection:
    def __init__(self, id, name, student_count=60, academic_year="2026-27", semester="Odd"):
        self.id = id
        self.name = name
        self.student_count = student_count
        self.academic_year = academic_year
        self.semester = semester

class MockFaculty:
    def __init__(self, id, name, short_name, unavailable_slots=None):
        self.id = id
        self.name = name
        self.short_name = short_name
        self.unavailable_slots_parsed = unavailable_slots or []

class MockRoom:
    def __init__(self, id, name, type="THEORY", capacity=70):
        self.id = id
        self.name = name
        self.type = type
        self.capacity = capacity

class MockSubject:
    def __init__(self, id, code, name, class_section_id, periods_per_week, duration=1, requires_lab=False, faculty_ids=None, type="THEORY", required_lab_type=None):
        self.id = id
        self.course_code = code
        self.name = name
        self.type = type
        self.required_lab_type = required_lab_type
        self.class_section_id = class_section_id
        self.periods_per_week = periods_per_week
        self.duration = duration
        self.requires_lab = requires_lab
        self.faculty_ids_parsed = faculty_ids or []
        self.preferred_days_parsed = []
        self.preferred_periods_parsed = []

class MockFixedEvent:
    def __init__(self, name, day, period, duration=1, class_section_id=None):
        self.name = name
        self.day = day
        self.period = period
        self.duration = duration
        self.class_section_id = class_section_id

def test_simultaneous_multiclass_scheduling_zero_conflicts():
    # 1. Three distinct classes
    c1 = MockClassSection("c1", "S5 AIML", 60)
    c2 = MockClassSection("c2", "S6 CSE A", 60)
    c3 = MockClassSection("c3", "S6 CSE B", 60)
    classes = [c1, c2, c3]

    # 2. Shared faculty
    f_akp = MockFaculty("f_akp", "Arun Kumar P", "AKP")
    f_krn = MockFaculty("f_krn", "Kavitha R Nair", "KRN")
    f_jsm = MockFaculty("f_jsm", "Jisha S M", "JSM")
    f_vkr = MockFaculty("f_vkr", "Vijayakumar R", "VKR")
    faculty_list = [f_akp, f_krn, f_jsm, f_vkr]

    # 3. Rooms: 3 Theory rooms, 1 Shared Computer Lab CC1
    r_301 = MockRoom("r_301", "Room 301", "THEORY", 65)
    r_302 = MockRoom("r_302", "Room 302", "THEORY", 65)
    r_303 = MockRoom("r_303", "Room 303", "THEORY", 65)
    r_cc1 = MockRoom("r_cc1", "Computing Center 1", "LAB", 70)
    rooms = [r_301, r_302, r_303, r_cc1]

    # 4. Subjects
    s1_1 = MockSubject("s1_1", "AIML301", "Machine Learning", "c1", periods_per_week=3, faculty_ids=["f_krn"])
    s1_2 = MockSubject("s1_2", "AIML302", "Deep Learning", "c1", periods_per_week=3, faculty_ids=["f_akp"])
    s1_lab = MockSubject("s1_lab", "AIML303", "AI Lab", "c1", periods_per_week=3, duration=3, requires_lab=True, faculty_ids=["f_krn", "f_vkr"])

    s2_1 = MockSubject("s2_1", "CSE301", "Data Structures", "c2", periods_per_week=3, faculty_ids=["f_akp"])
    s2_2 = MockSubject("s2_2", "CSE302", "Operating Systems", "c2", periods_per_week=3, faculty_ids=["f_jsm"])
    s2_lab = MockSubject("s2_lab", "CSE303", "OS Lab", "c2", periods_per_week=3, duration=3, requires_lab=True, faculty_ids=["f_jsm", "f_vkr"])

    s3_1 = MockSubject("s3_1", "CSE304", "Database Systems", "c3", periods_per_week=3, faculty_ids=["f_krn"])
    s3_2 = MockSubject("s3_2", "CSE305", "Computer Networks", "c3", periods_per_week=3, faculty_ids=["f_jsm"])
    s3_3 = MockSubject("s3_3", "CSE306", "Web Tech", "c3", periods_per_week=3, faculty_ids=["f_vkr"])

    subjects = [s1_1, s1_2, s1_lab, s2_1, s2_2, s2_lab, s3_1, s3_2, s3_3]

    # 5. Fixed events (Lunch at P4, Interval at P2)
    fixed_events = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    for d in days:
        fixed_events.append(MockFixedEvent("Interval", d, 2, 1))
        fixed_events.append(MockFixedEvent("Lunch", d, 4, 1))

    # 6. Run Backtracking Engine
    engine = BacktrackingEngine(
        class_sections=classes,
        subjects=subjects,
        faculty_list=faculty_list,
        rooms=rooms,
        fixed_events=fixed_events,
        days=days,
        periods=periods,
        optimization_enabled=True,
        search_limit=3000
    )

    success, schedule, stats, trace = engine.run()
    assert success is True, "Multi-class scheduling failed to find a valid solution!"
    assert schedule is not None
    assert len(schedule) > 0

    # 7. Verify cross-class faculty non-overlapping
    faculty_slots = {}
    for entry in schedule:
        d = entry["day"]
        p_start = entry["period"]
        dur = entry["duration"]
        c_id = entry["class_section_id"]
        for fid in entry["faculty_ids"]:
            for p in range(p_start, p_start + dur):
                key = (fid, d, p)
                assert key not in faculty_slots, f"Faculty {fid} is double-booked on {d} P{p} between {faculty_slots[key]} and {c_id}"
                faculty_slots[key] = (c_id, entry["subject_id"])

    # 8. Verify room non-overlapping (especially shared CC1)
    room_slots = {}
    for entry in schedule:
        d = entry["day"]
        p_start = entry["period"]
        dur = entry["duration"]
        r_id = entry["room_id"]
        c_id = entry["class_section_id"]
        for p in range(p_start, p_start + dur):
            key = (r_id, d, p)
            assert key not in room_slots, f"Room {r_id} is double-booked on {d} P{p} between {room_slots[key]} and {c_id}"
            room_slots[key] = c_id

    # 9. Verify each class has no internal overlap
    class_slots = {}
    for entry in schedule:
        d = entry["day"]
        p_start = entry["period"]
        dur = entry["duration"]
        c_id = entry["class_section_id"]
        for p in range(p_start, p_start + dur):
            key = (c_id, d, p)
            assert key not in class_slots, f"Class {c_id} has internal double booking on {d} P{p}"
            class_slots[key] = entry["subject_id"]

    # 10. Verify IndependentValidator passes with zero violations
    val_res = IndependentValidator.validate_multiclass(
        entries=schedule,
        class_sections=classes,
        subjects=subjects,
        faculty_list=faculty_list,
        rooms=rooms,
        fixed_events=fixed_events,
        days=days,
        periods=periods
    )

    assert val_res.is_valid is True, f"Validation violations: {[v.message for v in val_res.violations]}"
    assert len(val_res.violations) == 0
