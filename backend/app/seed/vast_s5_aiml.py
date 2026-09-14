import json
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Department, ClassSection, Faculty, Room, Subject, FixedEvent, GeneratedTimetable, TimetableEntry
)

def seed_vast_s5_aiml_data(db: Session) -> dict:
    """
    Seeds or resets the database with the authoritative VAST S5 AIML reference dataset.
    Vidya Academy of Science & Technology (VAST)
    Department: AIML
    Class: S5 AIML (2026-27 Odd Semester)
    """
    # 1. Clear existing demo data
    db.query(TimetableEntry).delete()
    db.query(GeneratedTimetable).delete()
    db.query(Subject).delete()
    db.query(FixedEvent).delete()
    db.query(Room).delete()
    db.query(Faculty).delete()
    db.query(ClassSection).delete()
    db.query(Department).delete()
    db.commit()

    # 2. Department
    dept_aiml = Department(
        id="dept-aiml",
        name="Department of Artificial Intelligence & Machine Learning",
        code="AIML"
    )
    db.add(dept_aiml)
    db.flush()

    # 3. Class Section: S5 AIML
    class_s5_aiml = ClassSection(
        id="class-s5-aiml",
        name="S5 AIML",
        department_id=dept_aiml.id,
        student_count=60,
        academic_year="2026-27",
        semester="Odd Semester"
    )
    db.add(class_s5_aiml)
    db.flush()

    # 4. Rooms (Lecture Halls and Laboratories)
    rooms_data = [
        Room(
            id="room-301",
            name="Room 301 (AIML Core Lecture Hall)",
            type="THEORY",
            capacity=70,
            building="Aryabhata Academic Block - 3rd Floor"
        ),
        Room(
            id="room-302",
            name="Room 302 (Elective & Tutorial Hall)",
            type="THEORY",
            capacity=65,
            building="Aryabhata Academic Block - 3rd Floor"
        ),
        Room(
            id="lab-iot",
            name="IoT & Embedded Systems Laboratory",
            type="LAB",
            lab_type="IOT",
            capacity=60,
            building="Advanced Computing Block - 1st Floor"
        ),
        Room(
            id="lab-dl",
            name="Deep Learning & AI Laboratory (GPU Cluster)",
            type="LAB",
            lab_type="AI_DL",
            capacity=60,
            building="Advanced Computing Block - 2nd Floor"
        ),
        Room(
            id="lab-project",
            name="Project & Advanced Computing Lab",
            type="LAB",
            lab_type="PROJECT",
            capacity=60,
            building="Advanced Computing Block - 2nd Floor"
        )
    ]
    for r in rooms_data:
        db.add(r)
    db.flush()

    # 5. Faculty Assignments (from VAST S5 AIML Reference)
    faculty_data = [
        Faculty(
            id="fac-akp",
            name="Ms. Anju K P",
            short_name="AKP",
            email="anju.kp@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-rr",
            name="Ms. Riya Roy",
            short_name="RR",
            email="riya.roy@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-np",
            name="Mr. Nisanth P",
            short_name="NP",
            email="nisanth.p@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-aer",
            name="Ms. Aswathi E R",
            short_name="AER",
            email="aswathi.er@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-dm",
            name="Ms. Deepa M",
            short_name="DM",
            email="deepa.m@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-pk",
            name="Mr. Praveen K",
            short_name="PK",
            email="praveen.k@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-ss",
            name="Dr. Sunitha S",
            short_name="SS",
            email="sunitha.s@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-mf",
            name="Minor Faculty Coordinator",
            short_name="MF",
            email="minor.coord@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        # Lab and Project Support Faculty
        Faculty(
            id="fac-li1",
            name="Mr. Manu K (Lab Instructor)",
            short_name="MK (LI)",
            email="manu.k@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-li2",
            name="Ms. Sona P (Lab Instructor)",
            short_name="SP (LI)",
            email="sona.p@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        ),
        Faculty(
            id="fac-pg",
            name="Dr. Arun M (Project Guide)",
            short_name="AM (PG)",
            email="arun.m@vidyaacademy.ac.in",
            department_id=dept_aiml.id,
            unavailable_slots=json.dumps([]),
            preferred_slots=json.dumps([])
        )
    ]
    for f in faculty_data:
        db.add(f)
    db.flush()

    # 6. Subjects & Course Requirements
    subjects_data = [
        # DAA - Design and Analysis of Algorithms (4 theory periods)
        Subject(
            id="sub-daa",
            course_code="CST 301",
            name="Design and Analysis of Algorithms",
            type="THEORY",
            periods_per_week=4,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-akp"])
        ),
        # ICV - Introduction to Computer Vision (4 theory periods)
        Subject(
            id="sub-icv",
            course_code="CST 303",
            name="Introduction to Computer Vision",
            type="THEORY",
            periods_per_week=4,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-rr"])
        ),
        # DL - Deep Learning Concepts (4 theory periods)
        Subject(
            id="sub-dl",
            course_code="CST 305",
            name="Deep Learning Concepts",
            type="THEORY",
            periods_per_week=4,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-np"])
        ),
        # IOT - Introduction to Internet of Things (3 theory periods)
        Subject(
            id="sub-iot",
            course_code="CST 307",
            name="Introduction to Internet of Things",
            type="THEORY",
            periods_per_week=3,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-aer"])
        ),
        # DM - Data Mining (Elective, 3 theory periods)
        Subject(
            id="sub-dm",
            course_code="CST 311",
            name="Data Mining (Elective)",
            type="ELECTIVE",
            periods_per_week=3,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-dm"])
        ),
        # IOT LAB - Internet of Things Lab (3 consecutive periods)
        # Multiple faculty: Ms. Aswathi E R + Mr. Manu K (LI)
        Subject(
            id="sub-iot-lab",
            course_code="CSL 331",
            name="Internet of Things Lab",
            type="LAB",
            periods_per_week=3,
            duration=3,
            requires_lab=True,
            required_lab_type="IOT",
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-aer", "fac-li1"])
        ),
        # DL LAB - Deep Learning Lab (3 consecutive periods)
        # Multiple faculty: Mr. Nisanth P + Ms. Sona P (LI)
        Subject(
            id="sub-dl-lab",
            course_code="CSL 333",
            name="Deep Learning Lab",
            type="LAB",
            periods_per_week=3,
            duration=3,
            requires_lab=True,
            required_lab_type="AI_DL",
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-np", "fac-li2"])
        ),
        # ICV PROJECT - Introduction to Computer Vision Project (3 consecutive periods)
        # Multiple faculty: Ms. Riya Roy + Dr. Arun M (PG)
        Subject(
            id="sub-icv-proj",
            course_code="CSP 335",
            name="Introduction to Computer Vision (Project)",
            type="LAB",
            periods_per_week=3,
            duration=3,
            requires_lab=True,
            required_lab_type="PROJECT",
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-rr", "fac-pg"])
        ),
        # MINOR (3 theory periods)
        Subject(
            id="sub-minor",
            course_code="VAC 301",
            name="Minor Program",
            type="MINOR",
            periods_per_week=3,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-mf"])
        ),
        # HONORS - Applied NLP (3 theory periods)
        Subject(
            id="sub-anlp",
            course_code="VAC 303",
            name="Applied Natural Language Processing (Honors)",
            type="HONORS",
            periods_per_week=3,
            duration=1,
            requires_lab=False,
            class_section_id=class_s5_aiml.id,
            faculty_ids=json.dumps(["fac-ss"])
        )
    ]
    for s in subjects_data:
        db.add(s)
    db.flush()

    # 7. Fixed Events (Common Activity on Friday Period VII)
    fixed_events_data = [
        FixedEvent(
            id="fix-common-act",
            name="Common Activity / Association / Forum",
            class_section_id=class_s5_aiml.id,
            day="Friday",
            period=7,
            duration=1,
            event_type="COMMON_ACTIVITY"
        )
    ]
    for fe in fixed_events_data:
        db.add(fe)
    db.commit()

    return {
        "status": "success",
        "message": "VAST S5 AIML reference dataset seeded successfully",
        "department": dept_aiml.name,
        "class": class_s5_aiml.name,
        "subjects_count": len(subjects_data),
        "faculty_count": len(faculty_data),
        "rooms_count": len(rooms_data),
        "fixed_events_count": len(fixed_events_data)
    }
