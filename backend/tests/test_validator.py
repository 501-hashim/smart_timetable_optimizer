import pytest
from types import SimpleNamespace
from backend.app.algorithms.validator import IndependentValidator

def test_validator_detects_deliberate_conflict():
    class_sec = SimpleNamespace(id="c1", name="Class 1", student_count=40)
    subjects = [
        SimpleNamespace(id="s1", course_code="CS1", name="Sub 1", periods_per_week=2, requires_lab=False),
        SimpleNamespace(id="s2", course_code="CS2", name="Sub 2", periods_per_week=2, requires_lab=False)
    ]
    faculty = [
        SimpleNamespace(id="f1", name="Fac 1", short_name="F1", unavailable_slots_parsed=[])
    ]
    rooms = [
        SimpleNamespace(id="r1", name="Room 1", type="THEORY", capacity=50)
    ]
    fixed_events = []
    days = ["Monday"]
    periods = [1, 2]

    # Deliberately conflicting schedule: two subjects in same class at same day & period
    corrupted_entries = [
        {"day": "Monday", "period": 1, "duration": 1, "class_section_id": "c1", "subject_id": "s1", "room_id": "r1", "faculty_ids": ["f1"]},
        {"day": "Monday", "period": 1, "duration": 1, "class_section_id": "c1", "subject_id": "s2", "room_id": "r1", "faculty_ids": ["f1"]}
    ]

    report = IndependentValidator.validate(
        entries=corrupted_entries, class_section=class_sec, subjects=subjects,
        faculty_list=faculty, rooms=rooms, fixed_events=fixed_events, days=days, periods=periods
    )

    assert report.is_valid is False
    assert len(report.violations) >= 2
    rule_names = [v.rule for v in report.violations]
    assert "CLASS_CONFLICT" in rule_names
    assert "FACULTY_CONFLICT" in rule_names
