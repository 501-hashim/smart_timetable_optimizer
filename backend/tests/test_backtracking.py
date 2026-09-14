import pytest
from types import SimpleNamespace
from backend.app.algorithms.backtracking import BacktrackingEngine

def test_valid_small_timetable():
    class_sec = SimpleNamespace(id="c_test", name="Class Test", student_count=30)
    subjects = [
        SimpleNamespace(
            id="s1", course_code="CS101", name="Subject 1", type="THEORY",
            periods_per_week=2, duration=1, requires_lab=False, required_lab_type=None,
            faculty_ids_parsed=["f1"], preferred_days_parsed=[], preferred_periods_parsed=[]
        ),
        SimpleNamespace(
            id="s2", course_code="CS102", name="Subject 2", type="THEORY",
            periods_per_week=2, duration=1, requires_lab=False, required_lab_type=None,
            faculty_ids_parsed=["f2"], preferred_days_parsed=[], preferred_periods_parsed=[]
        )
    ]
    faculty_list = [
        SimpleNamespace(id="f1", name="Faculty 1", short_name="F1", unavailable_slots_parsed=[]),
        SimpleNamespace(id="f2", name="Faculty 2", short_name="F2", unavailable_slots_parsed=[])
    ]
    rooms = [
        SimpleNamespace(id="r1", name="Room 101", type="THEORY", capacity=40)
    ]
    fixed_events = []
    days = ["Monday", "Tuesday"]
    periods = [1, 2]

    engine = BacktrackingEngine(
        class_section=class_sec,
        subjects=subjects,
        faculty_list=faculty_list,
        rooms=rooms,
        fixed_events=fixed_events,
        days=days,
        periods=periods,
        optimization_enabled=True,
        search_limit=500
    )
    success, schedule, stats, trace = engine.run()
    assert success
    assert schedule is not None
    assert len(schedule) == 4
    assert stats["hard_constraint_violations"] == 0

def test_impossible_timetable_handling():
    # Attempting to schedule 10 periods when only 2 total slots exist in the week
    class_sec = SimpleNamespace(id="c_test", name="Class Test", student_count=30)
    subjects = [
        SimpleNamespace(
            id="s1", course_code="CS101", name="Subject 1", type="THEORY",
            periods_per_week=10, duration=1, requires_lab=False, required_lab_type=None,
            faculty_ids_parsed=["f1"], preferred_days_parsed=[], preferred_periods_parsed=[]
        )
    ]
    faculty_list = [
        SimpleNamespace(id="f1", name="Faculty 1", short_name="F1", unavailable_slots_parsed=[])
    ]
    rooms = [
        SimpleNamespace(id="r1", name="Room 101", type="THEORY", capacity=40)
    ]
    fixed_events = []
    days = ["Monday"]
    periods = [1, 2]  # Only 2 slots exist

    engine = BacktrackingEngine(
        class_section=class_sec,
        subjects=subjects,
        faculty_list=faculty_list,
        rooms=rooms,
        fixed_events=fixed_events,
        days=days,
        periods=periods,
        optimization_enabled=False,
        search_limit=100
    )
    success, schedule, stats, trace = engine.run()
    assert not success
    assert schedule is None
