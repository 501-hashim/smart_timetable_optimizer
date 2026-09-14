import pytest
from backend.app.algorithms.constraints import SchedulingTask, HardConstraintEngine
from backend.app.models.entities import Room

def test_class_conflict_detection():
    task = SchedulingTask(
        task_id="t1", subject_id="s1", subject_code="DAA", subject_name="DAA",
        subject_type="THEORY", class_section_id="c1", duration=1, faculty_ids=["f1"],
        requires_lab=False, required_lab_type=None
    )
    room = Room(id="r1", name="Room 301", type="THEORY", capacity=60)
    class_occupancy = {"c1": {("Monday", 1)}}
    faculty_occupancy = {"f1": set()}
    room_occupancy = {"r1": set()}

    # Should detect collision on Monday Period 1
    valid, reason = HardConstraintEngine.check_assignment(
        task=task, day="Monday", start_period=1, room=room, class_student_count=50,
        class_occupancy=class_occupancy, faculty_occupancy=faculty_occupancy,
        room_occupancy=room_occupancy, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid
    assert "already has another scheduled subject" in reason

def test_faculty_conflict_detection():
    task = SchedulingTask(
        task_id="t2", subject_id="s2", subject_code="ICV", subject_name="ICV",
        subject_type="THEORY", class_section_id="c1", duration=1, faculty_ids=["f1"],
        requires_lab=False, required_lab_type=None
    )
    room = Room(id="r1", name="Room 301", type="THEORY", capacity=60)
    class_occupancy = {"c1": set()}
    faculty_occupancy = {"f1": {("Monday", 2)}}
    room_occupancy = {"r1": set()}

    # Should detect faculty f1 already teaching on Monday Period 2
    valid, reason = HardConstraintEngine.check_assignment(
        task=task, day="Monday", start_period=2, room=room, class_student_count=50,
        class_occupancy=class_occupancy, faculty_occupancy=faculty_occupancy,
        room_occupancy=room_occupancy, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid
    assert "already teaching another class" in reason

def test_room_conflict_detection():
    task = SchedulingTask(
        task_id="t3", subject_id="s3", subject_code="DL", subject_name="DL",
        subject_type="THEORY", class_section_id="c1", duration=1, faculty_ids=["f2"],
        requires_lab=False, required_lab_type=None
    )
    room = Room(id="r1", name="Room 301", type="THEORY", capacity=60)
    class_occupancy = {"c1": set()}
    faculty_occupancy = {"f2": set()}
    room_occupancy = {"r1": {("Tuesday", 3)}}

    # Should detect room r1 already occupied on Tuesday Period 3
    valid, reason = HardConstraintEngine.check_assignment(
        task=task, day="Tuesday", start_period=3, room=room, class_student_count=50,
        class_occupancy=class_occupancy, faculty_occupancy=faculty_occupancy,
        room_occupancy=room_occupancy, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid
    assert "already occupied" in reason

def test_room_type_enforcement():
    lab_task = SchedulingTask(
        task_id="t4", subject_id="s4", subject_code="IOT_LAB", subject_name="IoT Lab",
        subject_type="LAB", class_section_id="c1", duration=3, faculty_ids=["f1"],
        requires_lab=True, required_lab_type="IOT"
    )
    theory_room = Room(id="r1", name="Room 301", type="THEORY", capacity=60)
    wrong_lab_room = Room(id="r2", name="AI Lab", type="LAB", lab_type="AI_DL", capacity=60)
    correct_lab_room = Room(id="r3", name="IoT Lab", type="LAB", lab_type="IOT", capacity=60)

    # 1. Theory room fails
    valid1, reason1 = HardConstraintEngine.check_assignment(
        task=lab_task, day="Monday", start_period=5, room=theory_room, class_student_count=50,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r1": set()}, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid1
    assert "requires laboratory" in reason1

    # 2. Wrong lab type fails
    valid2, reason2 = HardConstraintEngine.check_assignment(
        task=lab_task, day="Monday", start_period=5, room=wrong_lab_room, class_student_count=50,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r2": set()}, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid2
    assert "Lab type mismatch" in reason2

    # 3. Correct lab succeeds
    valid3, reason3 = HardConstraintEngine.check_assignment(
        task=lab_task, day="Monday", start_period=5, room=correct_lab_room, class_student_count=50,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r3": set()}, fixed_events_set=set(), faculty_unavailability={}
    )
    assert valid3
    assert reason3 is None

def test_room_capacity_check():
    task = SchedulingTask(
        task_id="t5", subject_id="s5", subject_code="DAA", subject_name="DAA",
        subject_type="THEORY", class_section_id="c1", duration=1, faculty_ids=["f1"],
        requires_lab=False, required_lab_type=None
    )
    small_room = Room(id="r_small", name="Small Room", type="THEORY", capacity=30)
    valid, reason = HardConstraintEngine.check_assignment(
        task=task, day="Monday", start_period=1, room=small_room, class_student_count=60,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r_small": set()}, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid
    assert "smaller than class size" in reason

def test_consecutive_lab_break_crossing():
    # 3-period lab starting at Period 3 would end at Period 5, crossing lunch (after Period 4)
    lab_task = SchedulingTask(
        task_id="t6", subject_id="s6", subject_code="DL_LAB", subject_name="DL Lab",
        subject_type="LAB", class_section_id="c1", duration=3, faculty_ids=["f1"],
        requires_lab=True, required_lab_type="AI_DL"
    )
    room = Room(id="r_dl", name="DL Lab", type="LAB", lab_type="AI_DL", capacity=60)
    valid, reason = HardConstraintEngine.check_assignment(
        task=lab_task, day="Monday", start_period=3, room=room, class_student_count=60,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r_dl": set()}, fixed_events_set=set(), faculty_unavailability={}
    )
    assert not valid
    assert "Cannot cross interval or lunch break" in reason

def test_fixed_event_protection():
    task = SchedulingTask(
        task_id="t7", subject_id="s7", subject_code="DAA", subject_name="DAA",
        subject_type="THEORY", class_section_id="c1", duration=1, faculty_ids=["f1"],
        requires_lab=False, required_lab_type=None
    )
    room = Room(id="r1", name="Room 301", type="THEORY", capacity=60)
    fixed_set = {("Friday", 7)}  # Common activity

    valid, reason = HardConstraintEngine.check_assignment(
        task=task, day="Friday", start_period=7, room=room, class_student_count=50,
        class_occupancy={"c1": set()}, faculty_occupancy={"f1": set()},
        room_occupancy={"r1": set()}, fixed_events_set=fixed_set, faculty_unavailability={}
    )
    assert not valid
    assert "Collides with fixed college event" in reason

def test_multi_faculty_lab_availability():
    lab_task = SchedulingTask(
        task_id="t8", subject_id="s8", subject_code="IOT_LAB", subject_name="IoT Lab",
        subject_type="LAB", class_section_id="c1", duration=3, faculty_ids=["fac1", "fac2"],
        requires_lab=True, required_lab_type="IOT"
    )
    room = Room(id="r_iot", name="IoT Lab", type="LAB", lab_type="IOT", capacity=60)
    faculty_unavail = {
        "fac1": set(),
        "fac2": {("Wednesday", 6)}  # fac2 unavailable during Period 6
    }
    valid, reason = HardConstraintEngine.check_assignment(
        task=lab_task, day="Wednesday", start_period=5, room=room, class_student_count=50,
        class_occupancy={"c1": set()},
        faculty_occupancy={"fac1": set(), "fac2": set()},
        room_occupancy={"r_iot": set()},
        fixed_events_set=set(),
        faculty_unavailability=faculty_unavail
    )
    assert not valid
    assert "marked unavailable" in reason
