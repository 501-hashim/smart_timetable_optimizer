import json
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

class Department(Base):
    __tablename__ = "departments"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)

class ClassSection(Base):
    __tablename__ = "class_sections"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    department_id = Column(String(50), ForeignKey("departments.id"), nullable=True)
    student_count = Column(Integer, default=60)
    academic_year = Column(String(20), default="2026-27")
    semester = Column(String(20), default="Odd")
    available_slots = Column(Text, default="[]")  # JSON list of allowed (day, period)

class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    short_name = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    department_id = Column(String(50), ForeignKey("departments.id"), nullable=True)
    unavailable_slots = Column(Text, default="[]")  # JSON list of {"day": str, "period": int}
    preferred_slots = Column(Text, default="[]")    # JSON list of {"day": str, "period": int}

class Room(Base):
    __tablename__ = "rooms"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    type = Column(String(20), default="THEORY")  # THEORY, LAB
    lab_type = Column(String(50), nullable=True)  # IOT, AI_DL, PROJECT, GENERAL
    capacity = Column(Integer, default=60)
    building = Column(String(50), default="Main Academic Block")

class Subject(Base):
    __tablename__ = "subjects"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_code = Column(String(30), nullable=False)
    name = Column(String(150), nullable=False)
    type = Column(String(30), default="THEORY")  # THEORY, LAB, ELECTIVE, HONORS, MINOR
    periods_per_week = Column(Integer, default=3)
    duration = Column(Integer, default=1)  # 1 for single period, 2/3 for multi-period labs
    consecutive = Column(Boolean, default=False)
    requires_lab = Column(Boolean, default=False)
    required_lab_type = Column(String(50), nullable=True)
    class_section_id = Column(String(50), ForeignKey("class_sections.id"), nullable=True)
    faculty_ids = Column(Text, default="[]")  # JSON list of faculty IDs
    preferred_days = Column(Text, default="[]")  # JSON list
    preferred_periods = Column(Text, default="[]")  # JSON list

    @property
    def hours_per_week(self) -> int:
        return self.periods_per_week

    @hours_per_week.setter
    def hours_per_week(self, value: int):
        self.periods_per_week = value

class FixedEvent(Base):
    __tablename__ = "fixed_events"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    class_section_id = Column(String(50), ForeignKey("class_sections.id"), nullable=True)
    day = Column(String(20), nullable=False)
    period = Column(Integer, nullable=False)
    duration = Column(Integer, default=1)
    event_type = Column(String(30), default="COMMON_ACTIVITY")  # COMMON_ACTIVITY, BREAK, ASSEMBLY

class GeneratedTimetable(Base):
    __tablename__ = "generated_timetables"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    class_section_id = Column(String(50), ForeignKey("class_sections.id"), nullable=False)
    name = Column(String(100), default="Generated Timetable")
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="VALID")
    score = Column(Float, default=100.0)
    statistics = Column(Text, default="{}")  # JSON

    entries = relationship("TimetableEntry", back_populates="timetable", cascade="all, delete-orphan")

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    timetable_id = Column(String(50), ForeignKey("generated_timetables.id"), nullable=False)
    day = Column(String(20), nullable=False)
    period = Column(Integer, nullable=False)
    duration = Column(Integer, default=1)
    class_section_id = Column(String(50), nullable=False)
    subject_id = Column(String(50), nullable=False)
    room_id = Column(String(50), nullable=False)
    faculty_ids = Column(Text, default="[]")  # JSON list

    timetable = relationship("GeneratedTimetable", back_populates="entries")
