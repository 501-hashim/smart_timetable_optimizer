from typing import List, Dict, Set, Tuple, Any, Optional

class SchedulingTask:
    def __init__(
        self,
        task_id: str,
        subject_id: str,
        subject_code: str,
        subject_name: str,
        subject_type: str,
        class_section_id: str,
        duration: int,
        faculty_ids: List[str],
        requires_lab: bool,
        required_lab_type: Optional[str],
        preferred_days: Optional[List[str]] = None,
        preferred_periods: Optional[List[int]] = None,
        class_name: Optional[str] = None,
        consecutive: bool = False,
        hours_per_week: Optional[int] = None,
        session_index: int = 0
    ):
        self.task_id = task_id
        self.subject_id = subject_id
        self.subject_code = subject_code
        self.subject_name = subject_name
        self.subject_type = subject_type
        self.class_section_id = class_section_id
        self.duration = duration
        self.faculty_ids = faculty_ids
        self.requires_lab = requires_lab
        self.required_lab_type = required_lab_type
        self.preferred_days = preferred_days or []
        self.preferred_periods = preferred_periods or []
        self.class_name = class_name or class_section_id
        self.consecutive = consecutive
        self.hours_per_week = hours_per_week
        self.session_index = session_index
        self.mrv_priority = 0.0

class HardConstraintEngine:
    @staticmethod
    def is_block_crossing_breaks(day: str, start_period: int, duration: int, max_period: int = 7, session_break_after: Optional[List[int]] = None) -> bool:
        """
        Enforces realistic break and session integrity for multi-period blocks.
        A block with duration > 1 cannot cross designated session break boundaries (default: after period 2, after period 4).
        """
        end_period = start_period + duration - 1
        if end_period > max_period:
            return True

        if duration <= 1:
            return False

        breaks = session_break_after if session_break_after is not None else [2, 4]
        for b in breaks:
            if start_period <= b < end_period:
                return True
        return False

    @staticmethod
    def check_assignment(
        task: SchedulingTask,
        day: str,
        start_period: int,
        room: Any,
        class_student_count: int,
        class_occupancy: Dict[str, Set[Tuple[str, int]]],
        faculty_occupancy: Dict[str, Set[Tuple[str, int]]],
        room_occupancy: Dict[str, Set[Tuple[str, int]]],
        fixed_events_set: Set[Tuple[str, int]],
        faculty_unavailability: Dict[str, Set[Tuple[str, int]]],
        faculty_map: Optional[Dict[str, Any]] = None,
        faculty_assignment_owners: Optional[Dict[Tuple[str, str, int], str]] = None,
        room_assignment_owners: Optional[Dict[Tuple[str, str, int], str]] = None
    ) -> Tuple[bool, Optional[str]]:
        duration = task.duration
        target_slots = [(day, start_period + i) for i in range(duration)]

        # 1. Break / Boundary check
        if HardConstraintEngine.is_block_crossing_breaks(day, start_period, duration):
            return False, f"Cannot cross interval or lunch break boundary (Period {start_period} to {start_period + duration - 1})"

        # 2. Fixed Events (Interval, Lunch, Common Activity)
        for slot in target_slots:
            if slot in fixed_events_set:
                return False, f"Collides with fixed college event at {slot[0]} Period {slot[1]}"

        # 3. Room Type suitability
        if task.requires_lab:
            if room.type != "LAB":
                return False, f"Subject requires laboratory, but {room.name} is a {room.type} room"
            if task.required_lab_type and room.lab_type != task.required_lab_type:
                return False, f"Lab type mismatch: requires {task.required_lab_type}, {room.name} has {room.lab_type}"
        else:
            # Theory should not occupy specialized lab if unnecessary
            if room.type == "LAB":
                return False, f"Theory class should not be scheduled in specialized laboratory {room.name}"

        # 4. Room Capacity
        if room.capacity < class_student_count:
            return False, f"Room capacity ({room.capacity}) is smaller than class size ({class_student_count})"

        # 5. Room Occupancy Conflict
        r_occ = room_occupancy.get(room.id, set())
        for slot in target_slots:
            if slot in r_occ:
                owner = room_assignment_owners.get((room.id, slot[0], slot[1])) if room_assignment_owners else None
                owner_str = f" by {owner}" if owner else ""
                return False, f"Room {room.name} is already occupied{owner_str} on {slot[0]} Period {slot[1]}"

        # 6. Class Section Conflict
        c_occ = class_occupancy.get(task.class_section_id, set())
        for slot in target_slots:
            if slot in c_occ:
                c_name = task.class_name or task.class_section_id
                return False, f"Class {c_name} already has another scheduled subject on {slot[0]} Period {slot[1]}"

        # 7. Faculty Conflicts & Availability
        for fac_id in task.faculty_ids:
            fac_name = faculty_map[fac_id].short_name if faculty_map and fac_id in faculty_map else fac_id

            # Check availability
            unavail = faculty_unavailability.get(fac_id, set())
            for slot in target_slots:
                if slot in unavail:
                    return False, f"Faculty {fac_name} marked unavailable on {slot[0]} Period {slot[1]}"

            # Check teaching conflict
            f_occ = faculty_occupancy.get(fac_id, set())
            for slot in target_slots:
                if slot in f_occ:
                    owner = faculty_assignment_owners.get((fac_id, slot[0], slot[1])) if faculty_assignment_owners else None
                    owner_str = f" ({owner})" if owner else ""
                    return False, f"Faculty {fac_name} is already teaching another class{owner_str} on {slot[0]} Period {slot[1]}"

        return True, None
