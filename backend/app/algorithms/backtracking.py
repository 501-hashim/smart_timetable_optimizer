import time
import copy
from typing import List, Dict, Set, Tuple, Any, Optional
from backend.app.algorithms.constraints import SchedulingTask, HardConstraintEngine
from backend.app.algorithms.scoring import calculate_timetable_quality
from backend.app.algorithms.tracer import AlgorithmTracer

class BacktrackingEngine:
    def __init__(
        self,
        class_section: Any = None,
        class_sections: Optional[List[Any]] = None,
        subjects: List[Any] = None,
        faculty_list: List[Any] = None,
        rooms: List[Any] = None,
        fixed_events: List[Any] = None,
        days: List[str] = None,
        periods: List[int] = None,
        soft_weights: Any = None,
        optimization_enabled: bool = True,
        search_limit: int = 3000,
        time_limit_sec: float = 8.0
    ):
        # Support both single class (legacy) and multi-class
        if class_sections:
            self.class_sections = class_sections
        elif class_section:
            self.class_sections = [class_section]
        else:
            self.class_sections = []

        self.class_section = self.class_sections[0] if self.class_sections else None
        self.class_map = {c.id: c for c in self.class_sections}

        self.subjects = subjects or []
        self.faculty_list = faculty_list or []
        self.rooms = rooms or []
        self.fixed_events = fixed_events or []
        self.days = days or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.periods = periods or [1, 2, 3, 4, 5, 6, 7]
        self.soft_weights = soft_weights
        self.optimization_enabled = optimization_enabled
        self.search_limit = search_limit
        self.time_limit_sec = time_limit_sec

        # Lookup dictionaries
        self.faculty_map = {f.id: f for f in self.faculty_list}
        self.room_map = {r.id: r for r in self.rooms}
        self.subject_map = {s.id: s for s in self.subjects}

        # Fixed events set: (day, period) - per class and global
        self.fixed_events_set: Set[Tuple[str, int]] = set()
        self.class_fixed_events_set: Dict[str, Set[Tuple[str, int]]] = {c.id: set() for c in self.class_sections}
        for fe in self.fixed_events:
            for p_offset in range(fe.duration):
                slot = (fe.day, fe.period + p_offset)
                if fe.class_section_id:
                    if fe.class_section_id in self.class_fixed_events_set:
                        self.class_fixed_events_set[fe.class_section_id].add(slot)
                else:
                    self.fixed_events_set.add(slot)

        # Faculty unavailable set
        self.faculty_unavailability: Dict[str, Set[Tuple[str, int]]] = {}
        for f in self.faculty_list:
            self.faculty_unavailability[f.id] = set()
            unavail = getattr(f, "unavailable_slots_parsed", [])
            for u in unavail:
                self.faculty_unavailability[f.id].add((u["day"], int(u["period"])))

        # Global state tracking
        self.class_occupancy: Dict[str, Set[Tuple[str, int]]] = {c.id: set() for c in self.class_sections}
        self.faculty_occupancy: Dict[str, Set[Tuple[str, int]]] = {f.id: set() for f in self.faculty_list}
        self.room_occupancy: Dict[str, Set[Tuple[str, int]]] = {r.id: set() for r in self.rooms}

        # Maps (resource_id, day, period) -> "ClassName • SubjectCode" for detailed conflict explanation
        self.faculty_assignment_owners: Dict[Tuple[str, str, int], str] = {}
        self.room_assignment_owners: Dict[Tuple[str, str, int], str] = {}

        # Global tasks to schedule
        self.tasks: List[SchedulingTask] = []
        self._prepare_tasks()

        # Engine statistics & tracer
        self.tracer = AlgorithmTracer()
        self.iteration_count = 0
        self.start_time = 0.0
        self.best_schedule: Optional[List[Dict[str, Any]]] = None
        self.best_score: float = -1.0
        self.diagnostic_failures: Dict[str, int] = {}

    def _prepare_tasks(self):
        """Converts subject requirements across all classes into discrete scheduling tasks."""
        self.tasks = []
        for s in self.subjects:
            total_hours = getattr(s, "hours_per_week", None)
            if total_hours is None:
                total_hours = s.periods_per_week

            dur = s.duration if s.duration > 0 else 1
            is_consecutive = getattr(s, "consecutive", False) or (dur > 1)
            c_id = getattr(s, "class_section_id", None) or (self.class_section.id if self.class_section else "default")
            c_obj = self.class_map.get(c_id, self.class_section)
            c_name = c_obj.name if c_obj else c_id

            # Determine session durations summing exactly to total_hours
            session_durations = []
            remaining = total_hours
            while remaining > 0:
                cur_dur = min(dur, remaining)
                session_durations.append(cur_dur)
                remaining -= cur_dur

            if not session_durations:
                session_durations = [dur]

            for t_idx, s_dur in enumerate(session_durations):
                task = SchedulingTask(
                    task_id=f"{s.id}-task-{t_idx+1}",
                    subject_id=s.id,
                    subject_code=s.course_code,
                    subject_name=s.name,
                    subject_type=getattr(s, "type", "THEORY"),
                    class_section_id=c_id,
                    duration=s_dur,
                    faculty_ids=getattr(s, "faculty_ids_parsed", []),
                    requires_lab=getattr(s, "requires_lab", False),
                    required_lab_type=getattr(s, "required_lab_type", None),
                    preferred_days=getattr(s, "preferred_days_parsed", []),
                    preferred_periods=getattr(s, "preferred_periods_parsed", []),
                    class_name=c_name,
                    consecutive=is_consecutive,
                    hours_per_week=total_hours,
                    session_index=t_idx
                )
                self.tasks.append(task)

        # Apply Global MRV (Most Constrained Variable First) heuristic
        self._calculate_mrv_priorities()
        self.tasks.sort(key=lambda t: t.mrv_priority, reverse=True)

    def _calculate_mrv_priorities(self):
        """
        Calculates priority score for MRV heuristic across the multi-class global task pool.
        Tasks with longer duration (labs), multi-faculty sessions, shared faculty with
        tight schedules, and specialized rooms are scheduled earlier.
        """
        # Count total workload per faculty to prioritize shared heavily-loaded faculty
        faculty_load: Dict[str, int] = {}
        for t in self.tasks:
            for fid in t.faculty_ids:
                faculty_load[fid] = faculty_load.get(fid, 0) + t.duration

        for t in self.tasks:
            priority = 0.0
            # 1. Labs and multi-period blocks are hardest to fit
            priority += t.duration * 120.0
            if t.requires_lab:
                priority += 80.0

            # 2. Multi-faculty sessions are constrained
            priority += len(t.faculty_ids) * 40.0

            # 3. Shared faculty with high total weekly teaching hours
            for fid in t.faculty_ids:
                priority += faculty_load.get(fid, 0) * 15.0

            # 4. Suitable room availability
            c_obj = self.class_map.get(t.class_section_id, self.class_section)
            c_students = c_obj.student_count if c_obj else 60
            suitable_rooms = [
                r for r in self.rooms
                if (not t.requires_lab and r.type != "LAB" and r.capacity >= c_students) or
                   (t.requires_lab and r.type == "LAB" and (not t.required_lab_type or r.lab_type == t.required_lab_type) and r.capacity >= c_students)
            ]
            if len(suitable_rooms) > 0:
                priority += (10.0 / len(suitable_rooms))

            t.mrv_priority = priority

    def _generate_candidates_for_task(self, task: SchedulingTask, current_schedule: List[Dict[str, Any]]) -> List[Tuple[str, int, Any]]:
        """Generates possible (day, start_period, room) assignments ordered by heuristic."""
        c_obj = self.class_map.get(task.class_section_id, self.class_section)
        student_count = c_obj.student_count if c_obj else 60

        # Track periods and days already occupied by this subject in this class
        subject_period_counts: Dict[int, int] = {}
        days_already_having_subject: Set[str] = set()
        for entry in current_schedule:
            if entry["class_section_id"] == task.class_section_id and entry["subject_id"] == task.subject_id:
                days_already_having_subject.add(entry["day"])
                p_start = entry["period"]
                for p_offset in range(entry["duration"]):
                    p_val = p_start + p_offset
                    subject_period_counts[p_val] = subject_period_counts.get(p_val, 0) + 1

        # Valid rooms with capacity for this class
        if task.requires_lab:
            suitable_rooms = [
                r for r in self.rooms
                if r.type == "LAB" and (not task.required_lab_type or r.lab_type == task.required_lab_type) and r.capacity >= student_count
            ]
        else:
            suitable_rooms = [
                r for r in self.rooms
                if r.type != "LAB" and r.capacity >= student_count
            ]
        if not suitable_rooms:
            suitable_rooms = [r for r in self.rooms if r.capacity >= student_count]

        # Valid starting periods (break protection)
        max_p = max(self.periods) if self.periods else 7
        valid_start_periods = []
        for p in self.periods:
            if not HardConstraintEngine.is_block_crossing_breaks("", p, task.duration, max_period=max_p):
                valid_start_periods.append(p)

        day_index_map = {day: idx for idx, day in enumerate(self.days)}

        raw_candidates: List[Tuple[str, int, Any]] = []
        for d in self.days:
            for p in valid_start_periods:
                for r in suitable_rooms:
                    raw_candidates.append((d, p, r))

        # Rank candidates using composite heuristic to prevent monotone period repetition
        def candidate_sort_key(item: Tuple[str, int, Any]):
            day, period, room = item
            d_idx = day_index_map.get(day, 0)

            # 1. Prefer days not yet having this subject
            day_spread_penalty = 100 if day in days_already_having_subject else 0

            # 2. Prefer periods not yet used by this subject on other days
            period_repeat_penalty = subject_period_counts.get(period, 0) * 20

            # 3. Lab / multi-period afternoon preference
            if task.duration > 1 or task.requires_lab:
                lab_pref_penalty = 0 if period >= 5 else 10
            else:
                lab_pref_penalty = 0

            # 4. Period rotation dispersion across sessions to avoid clumping in period 1
            if valid_start_periods:
                rot_target = (task.session_index * 2 + d_idx) % len(valid_start_periods)
                p_idx = valid_start_periods.index(period) if period in valid_start_periods else 0
                rot_dist = (p_idx - rot_target) % len(valid_start_periods)
            else:
                rot_dist = 0

            # 5. Preferred days and periods
            pref_penalty = 0
            if task.preferred_days and day not in task.preferred_days:
                pref_penalty += 10
            if task.preferred_periods and period not in task.preferred_periods:
                pref_penalty += 10

            return (day_spread_penalty, period_repeat_penalty, lab_pref_penalty, rot_dist, pref_penalty)

        raw_candidates.sort(key=candidate_sort_key)
        return raw_candidates

    def run(self) -> Tuple[bool, Optional[List[Dict[str, Any]]], Dict[str, Any], List[Dict[str, Any]]]:
        """Executes the global backtracking algorithm across all configured classes."""
        self.start_time = time.time()
        self.iteration_count = 0
        current_schedule: List[Dict[str, Any]] = []

        found_valid = self._backtrack(0, current_schedule)

        elapsed_ms = round((time.time() - self.start_time) * 1000, 2)

        # Compute generation summary metrics
        total_classes = len(self.class_sections)
        total_subjects = len(self.subjects)
        total_weekly_hours = sum(
            (getattr(s, "hours_per_week", None) or s.periods_per_week)
            for s in self.subjects
        )

        assigned = self.best_schedule or []
        total_sessions = len(assigned)
        multi_period_blocks = sum(1 for e in assigned if e.get("duration", 1) > 1)

        assigned_faculty = set()
        assigned_rooms = set()
        for e in assigned:
            for fid in e.get("faculty_ids", []):
                assigned_faculty.add(fid)
            assigned_rooms.add(e.get("room_id"))

        stats = {
            "classes_scheduled": total_classes,
            "tasks": len(self.tasks),
            "candidates_tested": self.tracer.total_candidates_tested,
            "backtracking_steps": self.tracer.total_backtracks,
            "valid_assignments": self.tracer.total_assignments,
            "hard_constraint_violations": 0,
            "soft_constraint_penalty": round(100.0 - self.best_score, 2) if self.best_score >= 0 else 0.0,
            "quality_score": self.best_score if self.best_score >= 0 else 0.0,
            "generation_time_ms": elapsed_ms,
            "total_classes": total_classes,
            "total_subjects": total_subjects,
            "total_weekly_teaching_hours": total_weekly_hours,
            "total_sessions": total_sessions,
            "total_multi_period_blocks": multi_period_blocks,
            "total_faculty": len(assigned_faculty),
            "total_rooms": len(assigned_rooms)
        }

        # If a valid schedule was found, return the best schedule
        if self.best_schedule is not None:
            return True, self.best_schedule, stats, self.tracer.get_steps_dict()

        return False, None, stats, self.tracer.get_steps_dict()

    def _backtrack(self, task_index: int, current_schedule: List[Dict[str, Any]]) -> bool:
        self.iteration_count += 1

        # Time or iteration cap
        if (time.time() - self.start_time) > self.time_limit_sec or self.iteration_count > self.search_limit:
            return self.best_schedule is not None

        # Base case: All tasks across all classes successfully placed!
        if task_index >= len(self.tasks):
            score, penalty, _ = calculate_timetable_quality(
                current_schedule, self.soft_weights, self.days, self.periods
            )
            if score > self.best_score:
                self.best_score = score
                self.best_schedule = copy.deepcopy(current_schedule)

            if not self.optimization_enabled or self.best_score >= 98.0:
                return True
            return False

        task = self.tasks[task_index]
        faculty_names = [self.faculty_map[fid].short_name for fid in task.faculty_ids if fid in self.faculty_map]
        c_obj = self.class_map.get(task.class_section_id, self.class_section)
        student_count = c_obj.student_count if c_obj else 60
        task_display_name = f"[{task.class_name}] {task.subject_code} ({task.subject_name})"

        candidates = self._generate_candidates_for_task(task, current_schedule)

        # Combine global fixed events with class-specific fixed events
        class_fixed = self.fixed_events_set.union(self.class_fixed_events_set.get(task.class_section_id, set()))

        for day, start_period, room in candidates:
            self.tracer.record_step(
                action="EVALUATE_CANDIDATE",
                task_name=task_display_name,
                duration=task.duration,
                day=day,
                period=start_period,
                room_name=room.name,
                faculty_names=faculty_names,
                current_assigned_count=len(current_schedule),
                class_name=task.class_name
            )

            is_valid, reason = HardConstraintEngine.check_assignment(
                task=task,
                day=day,
                start_period=start_period,
                room=room,
                class_student_count=student_count,
                class_occupancy=self.class_occupancy,
                faculty_occupancy=self.faculty_occupancy,
                room_occupancy=self.room_occupancy,
                fixed_events_set=class_fixed,
                faculty_unavailability=self.faculty_unavailability,
                faculty_map=self.faculty_map,
                faculty_assignment_owners=self.faculty_assignment_owners,
                room_assignment_owners=self.room_assignment_owners
            )

            if is_valid:
                # 1. Apply Global Assignment
                target_slots = [(day, start_period + i) for i in range(task.duration)]
                for slot in target_slots:
                    self.class_occupancy[task.class_section_id].add(slot)
                    self.room_occupancy[room.id].add(slot)
                    self.room_assignment_owners[(room.id, slot[0], slot[1])] = f"{task.class_name} • {task.subject_code}"
                    for fid in task.faculty_ids:
                        self.faculty_occupancy[fid].add(slot)
                        self.faculty_assignment_owners[(fid, slot[0], slot[1])] = f"{task.class_name} • {task.subject_code}"

                entry = {
                    "day": day,
                    "period": start_period,
                    "duration": task.duration,
                    "class_section_id": task.class_section_id,
                    "class_name": task.class_name,
                    "subject_id": task.subject_id,
                    "subject_code": task.subject_code,
                    "subject_name": task.subject_name,
                    "subject_type": task.subject_type,
                    "room_id": room.id,
                    "room_name": room.name,
                    "faculty_ids": task.faculty_ids,
                    "faculty_names": [self.faculty_map[fid].name for fid in task.faculty_ids if fid in self.faculty_map],
                    "faculty_short_names": faculty_names
                }
                current_schedule.append(entry)

                self.tracer.record_step(
                    action="ASSIGN",
                    task_name=task_display_name,
                    duration=task.duration,
                    day=day,
                    period=start_period,
                    room_name=room.name,
                    faculty_names=faculty_names,
                    is_valid=True,
                    current_assigned_count=len(current_schedule),
                    class_name=task.class_name
                )

                # 2. Recurse to next global task
                solved = self._backtrack(task_index + 1, current_schedule)
                if solved and (not self.optimization_enabled or self.best_score >= 98.0):
                    return True

                # 3. Backtrack (Undo Assignment)
                current_schedule.pop()
                for slot in target_slots:
                    self.class_occupancy[task.class_section_id].discard(slot)
                    self.room_occupancy[room.id].discard(slot)
                    self.room_assignment_owners.pop((room.id, slot[0], slot[1]), None)
                    for fid in task.faculty_ids:
                        self.faculty_occupancy[fid].discard(slot)
                        self.faculty_assignment_owners.pop((fid, slot[0], slot[1]), None)

                self.tracer.record_step(
                    action="BACKTRACK",
                    task_name=task_display_name,
                    duration=task.duration,
                    day=day,
                    period=start_period,
                    room_name=room.name,
                    faculty_names=faculty_names,
                    is_valid=False,
                    reason="Backtracking: exploring alternative branches",
                    current_assigned_count=len(current_schedule),
                    class_name=task.class_name
                )
            else:
                self.diagnostic_failures[reason] = self.diagnostic_failures.get(reason, 0) + 1
                self.tracer.record_step(
                    action="CONFLICT",
                    task_name=task_display_name,
                    duration=task.duration,
                    day=day,
                    period=start_period,
                    room_name=room.name,
                    faculty_names=faculty_names,
                    is_valid=False,
                    reason=reason,
                    current_assigned_count=len(current_schedule),
                    class_name=task.class_name
                )

        return False
