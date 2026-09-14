import pytest
from backend.app.models.entities import ClassSection, Subject, Faculty, Room, FixedEvent
from backend.app.algorithms.backtracking import BacktrackingEngine
from backend.app.algorithms.validator import IndependentValidator
from backend.app.schemas.timetable_schemas import (
    MultiClassWizardRequest, ClassConfigItem, FacultyConfigItem, RoomConfigItem, SubjectConfigItem
)
from backend.app.database.session import SessionLocal
from backend.app.services.timetable_service import TimetableService

def test_subject_expansion_and_period_diversity():
    # Class
    c = ClassSection(id="c1", name="CS Section A", student_count=60)

    # 3 Theory subjects with 4 hours/week, duration=1
    # 1 Lab with 3 hours/week, duration=3, consecutive=True
    s1 = Subject(
        id="s1", course_code="MATH101", name="Calculus & Linear Algebra",
        type="THEORY", periods_per_week=4, duration=1, consecutive=False,
        class_section_id="c1"
    )
    s2 = Subject(
        id="s2", course_code="CS101", name="Data Structures & Algorithms",
        type="THEORY", periods_per_week=4, duration=1, consecutive=False,
        class_section_id="c1"
    )
    s3 = Subject(
        id="s3", course_code="CS102", name="Operating Systems",
        type="THEORY", periods_per_week=4, duration=1, consecutive=False,
        class_section_id="c1"
    )
    s_lab = Subject(
        id="slab", course_code="CSL101", name="Data Structures Lab",
        type="LAB", periods_per_week=3, duration=3, consecutive=True,
        requires_lab=True, required_lab_type="CS_LAB", class_section_id="c1"
    )

    subjects = [s1, s2, s3, s_lab]
    for s in subjects:
        s.faculty_ids_parsed = []
        s.preferred_days_parsed = []
        s.preferred_periods_parsed = []

    rooms = [
        Room(id="r1", name="Room 101", type="THEORY", capacity=60),
        Room(id="rlab", name="Lab 1", type="LAB", lab_type="CS_LAB", capacity=60)
    ]

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]

    engine = BacktrackingEngine(
        class_section=c,
        subjects=subjects,
        faculty_list=[],
        rooms=rooms,
        fixed_events=[],
        days=days,
        periods=periods,
        optimization_enabled=True,
        search_limit=4000
    )

    # Check tasks expansion
    # s1 -> 4 tasks, s2 -> 4 tasks, s3 -> 4 tasks, s_lab -> 1 task (duration 3)
    assert len(engine.tasks) == 4 + 4 + 4 + 1
    lab_tasks = [t for t in engine.tasks if t.subject_id == "slab"]
    assert len(lab_tasks) == 1
    assert lab_tasks[0].duration == 3

    success, schedule, stats, _ = engine.run()
    assert success is True
    assert schedule is not None

    # Check that Lab is placed as 3 continuous periods on a single day
    lab_entries = [e for e in schedule if e["subject_id"] == "slab"]
    assert len(lab_entries) == 1
    assert lab_entries[0]["duration"] == 3
    lab_start = lab_entries[0]["period"]
    assert lab_start in [1, 3, 5]

    # Check MATH101 period diversity: 4 sessions should NOT all be on Period 1!
    math_entries = [e for e in schedule if e["subject_id"] == "s1"]
    assert len(math_entries) == 4
    math_periods = [e["period"] for e in math_entries]
    math_days = [e["day"] for e in math_entries]

    # Must be on 4 distinct days
    assert len(set(math_days)) == 4, f"Math days should be spread: {math_days}"
    # Must NOT all be period 1 (period diversity across days)
    assert len(set(math_periods)) >= 2, f"Math periods should vary across days: {math_periods}"

    # Check metrics
    assert stats["total_classes"] == 1
    assert stats["total_subjects"] == 4
    assert stats["total_weekly_teaching_hours"] == 15  # 4+4+4+3
    assert stats["total_multi_period_blocks"] == 1

    # Validate with IndependentValidator
    val = IndependentValidator.validate(
        entries=schedule,
        class_section=c,
        subjects=subjects,
        faculty_list=[],
        rooms=rooms,
        fixed_events=[],
        days=days,
        periods=periods
    )
    assert val.is_valid is True
    assert len(val.violations) == 0

def test_validator_detects_weekly_hours_mismatch():
    c = ClassSection(id="c1", name="CS Section A", student_count=60)
    s1 = Subject(
        id="s1", course_code="CS101", name="Algorithms",
        type="THEORY", periods_per_week=4, duration=1,
        class_section_id="c1"
    )
    s1.hours_per_week = 4

    # Artificially create a schedule with only 3 periods scheduled
    entries = [
        {"day": "Monday", "period": 1, "duration": 1, "subject_id": "s1", "class_section_id": "c1", "room_id": "r1", "faculty_ids": []},
        {"day": "Tuesday", "period": 2, "duration": 1, "subject_id": "s1", "class_section_id": "c1", "room_id": "r1", "faculty_ids": []},
        {"day": "Wednesday", "period": 3, "duration": 1, "subject_id": "s1", "class_section_id": "c1", "room_id": "r1", "faculty_ids": []},
    ]

    val = IndependentValidator.validate(
        entries=entries,
        class_section=c,
        subjects=[s1],
        faculty_list=[],
        rooms=[Room(id="r1", name="Room 1", type="THEORY", capacity=60)],
        fixed_events=[],
        days=["Monday", "Tuesday", "Wednesday"],
        periods=[1, 2, 3]
    )

    assert val.is_valid is False
    mismatch_violations = [v for v in val.violations if v.rule == "REQUIRED_HOURS_MISMATCH"]
    assert len(mismatch_violations) == 1
    assert "requires 4 hours/week but only 3 were scheduled" in mismatch_violations[0].message
