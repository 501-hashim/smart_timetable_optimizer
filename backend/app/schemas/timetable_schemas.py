from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DepartmentBase(BaseModel):
    name: str
    code: str

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentOut(DepartmentBase):
    id: str
    class Config:
        from_attributes = True

class ClassSectionBase(BaseModel):
    name: str
    department_id: Optional[str] = None
    student_count: int = 60
    academic_year: str = "2026-27"
    semester: str = "Odd"

class ClassSectionCreate(ClassSectionBase):
    pass

class ClassSectionOut(ClassSectionBase):
    id: str
    class Config:
        from_attributes = True

class FacultyBase(BaseModel):
    name: str
    short_name: str
    email: Optional[str] = None
    department_id: Optional[str] = None
    unavailable_slots: List[Dict[str, Any]] = []
    preferred_slots: List[Dict[str, Any]] = []

class FacultyCreate(FacultyBase):
    pass

class FacultyOut(FacultyBase):
    id: str
    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    name: str
    type: str = "THEORY"
    lab_type: Optional[str] = None
    capacity: int = 60
    building: str = "Main Academic Block"

class RoomCreate(RoomBase):
    pass

class RoomOut(RoomBase):
    id: str
    class Config:
        from_attributes = True

class SubjectBase(BaseModel):
    course_code: str
    name: str
    type: str = "THEORY"
    periods_per_week: int = 3
    hours_per_week: Optional[int] = None
    duration: int = 1
    consecutive: bool = False
    requires_lab: bool = False
    required_lab_type: Optional[str] = None
    class_section_id: Optional[str] = None
    faculty_ids: List[str] = []
    preferred_days: List[str] = []
    preferred_periods: List[int] = []

class SubjectCreate(SubjectBase):
    pass

class SubjectOut(SubjectBase):
    id: str
    class Config:
        from_attributes = True

class FixedEventBase(BaseModel):
    name: str
    class_section_id: Optional[str] = None
    day: str
    period: int
    duration: int = 1
    event_type: str = "COMMON_ACTIVITY"

class FixedEventCreate(FixedEventBase):
    pass

class FixedEventOut(FixedEventBase):
    id: str
    class Config:
        from_attributes = True

class SoftWeights(BaseModel):
    faculty_gap: float = 2.0
    student_gap: float = 3.0
    repeat_same_day: float = 4.0
    consecutive_faculty: float = 2.0
    non_preferred_slot: float = 1.0
    bad_lab_slot: float = 2.0

class GenerateRequest(BaseModel):
    class_section_id: str
    days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods: List[int] = [1, 2, 3, 4, 5, 6, 7]
    optimization_enabled: bool = True
    search_limit: int = 2000
    soft_weights: SoftWeights = Field(default_factory=SoftWeights)

class TimetableEntryOut(BaseModel):
    day: str
    period: int
    duration: int
    class_section_id: str
    subject_id: str
    subject_name: Optional[str] = None
    subject_code: Optional[str] = None
    subject_type: Optional[str] = None
    room_id: str
    room_name: Optional[str] = None
    faculty_ids: List[str] = []
    faculty_names: List[str] = []
    faculty_short_names: List[str] = []

class StatisticsOut(BaseModel):
    tasks: int
    candidates_tested: int
    backtracking_steps: int
    valid_assignments: int
    hard_constraint_violations: int = 0
    soft_constraint_penalty: float = 0.0
    quality_score: float = 100.0
    generation_time_ms: float = 0.0
    total_classes: Optional[int] = None
    total_subjects: Optional[int] = None
    total_weekly_teaching_hours: Optional[int] = None
    total_sessions: Optional[int] = None
    total_multi_period_blocks: Optional[int] = None
    total_faculty: Optional[int] = None
    total_rooms: Optional[int] = None

class GenerateResponse(BaseModel):
    success: bool
    timetable_id: Optional[str] = None
    score: float = 0.0
    message: str = ""
    entries: List[TimetableEntryOut] = []
    statistics: StatisticsOut
    diagnostics: Optional[Dict[str, Any]] = None

class ValidationViolation(BaseModel):
    rule: str
    severity: str  # ERROR, WARNING
    message: str
    details: Optional[Dict[str, Any]] = None

class ValidateResponse(BaseModel):
    is_valid: bool
    quality_score: float
    violations: List[ValidationViolation] = []
    passed_checks: List[str] = []
    summary: str

class VisualizerStepOut(BaseModel):
    step_index: int
    action: str  # SELECT_TASK, EVALUATE_CANDIDATE, ASSIGN, CONFLICT, BACKTRACK, COMPLETE
    task_name: str
    class_name: Optional[str] = None
    duration: int
    day: Optional[str] = None
    period: Optional[int] = None
    room_name: Optional[str] = None
    faculty_names: List[str] = []
    is_valid: bool = False
    reason: Optional[str] = None
    current_assigned_count: int = 0
    backtrack_count: int = 0
    tested_count: int = 0

class VisualizerResponse(BaseModel):
    success: bool
    total_steps: int
    steps: List[VisualizerStepOut]
    final_stats: StatisticsOut

# ----------------- Multi-Class Setup & Result Schemas -----------------

class ClassConfigItem(BaseModel):
    name: str
    department_code: str
    department_name: Optional[str] = None
    student_count: int = 60
    academic_year: str = "2026-27"
    semester: str = "Odd"

class FacultyConfigItem(BaseModel):
    name: str
    short_name: str
    department_code: Optional[str] = None
    email: Optional[str] = None
    unavailable_slots: List[Dict[str, Any]] = []
    preferred_slots: List[Dict[str, Any]] = []

class RoomConfigItem(BaseModel):
    name: str
    type: str = "THEORY"
    lab_type: Optional[str] = None
    capacity: int = 60
    building: str = "Academic Block"

class SubjectConfigItem(BaseModel):
    class_name: str
    course_code: str
    name: str
    type: str = "THEORY"
    periods_per_week: int = 3
    hours_per_week: Optional[int] = None
    duration: int = 1
    consecutive: bool = False
    requires_lab: bool = False
    required_lab_type: Optional[str] = None
    faculty_shorts: List[str] = []
    preferred_days: List[str] = []
    preferred_periods: List[int] = []

class FixedEventConfigItem(BaseModel):
    name: str
    day: str
    period: int
    duration: int = 1
    event_type: str = "COMMON_ACTIVITY"
    class_name: Optional[str] = None  # None applies to all classes

class MultiClassWizardRequest(BaseModel):
    classes: List[ClassConfigItem]
    faculty: List[FacultyConfigItem]
    rooms: List[RoomConfigItem]
    subjects: List[SubjectConfigItem]
    fixed_events: List[FixedEventConfigItem] = []
    days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods: List[int] = [1, 2, 3, 4, 5, 6, 7]
    optimization_enabled: bool = True
    search_limit: int = 4000
    soft_weights: SoftWeights = Field(default_factory=SoftWeights)

class CombinedTimetableOut(BaseModel):
    days: List[str]
    periods: List[int]
    classes: List[Dict[str, Any]]
    matrix: Dict[str, Dict[int, Dict[str, Any]]] # day -> period -> class_id -> entry or null

class FacultyScheduleOut(BaseModel):
    faculty_id: str
    name: str
    short_name: str
    total_teaching_periods: int
    schedule: List[Dict[str, Any]]

class RoomScheduleOut(BaseModel):
    room_id: str
    name: str
    type: str
    capacity: int
    total_occupied_periods: int
    schedule: List[Dict[str, Any]]

class CollisionReportOut(BaseModel):
    total_classes: int
    total_faculty: int
    total_rooms: int
    total_entries: int
    is_conflict_free: bool
    faculty_collisions: List[str] = []
    room_collisions: List[str] = []
    class_collisions: List[str] = []
    summary: str
    faculty_verification_table: List[Dict[str, Any]] = []

