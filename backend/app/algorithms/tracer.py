from typing import List, Optional, Dict, Any

class VisualizerStep:
    def __init__(
        self,
        step_index: int,
        action: str,  # SELECT_TASK, EVALUATE_CANDIDATE, ASSIGN, CONFLICT, BACKTRACK, COMPLETE
        task_name: str,
        duration: int,
        day: Optional[str] = None,
        period: Optional[int] = None,
        room_name: Optional[str] = None,
        faculty_names: Optional[List[str]] = None,
        is_valid: bool = False,
        reason: Optional[str] = None,
        current_assigned_count: int = 0,
        backtrack_count: int = 0,
        tested_count: int = 0,
        class_name: Optional[str] = None
    ):
        self.step_index = step_index
        self.action = action
        self.task_name = task_name
        self.duration = duration
        self.day = day
        self.period = period
        self.room_name = room_name
        self.faculty_names = faculty_names or []
        self.is_valid = is_valid
        self.reason = reason
        self.current_assigned_count = current_assigned_count
        self.backtrack_count = backtrack_count
        self.tested_count = tested_count
        self.class_name = class_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "action": self.action,
            "task_name": self.task_name,
            "class_name": self.class_name,
            "duration": self.duration,
            "day": self.day,
            "period": self.period,
            "room_name": self.room_name,
            "faculty_names": self.faculty_names,
            "is_valid": self.is_valid,
            "reason": self.reason,
            "current_assigned_count": self.current_assigned_count,
            "backtrack_count": self.backtrack_count,
            "tested_count": self.tested_count
        }

class AlgorithmTracer:
    def __init__(self, max_steps: int = 600):
        self.steps: List[VisualizerStep] = []
        self.max_steps = max_steps
        self.total_candidates_tested = 0
        self.total_backtracks = 0
        self.total_assignments = 0

    def record_step(
        self,
        action: str,
        task_name: str,
        duration: int,
        day: Optional[str] = None,
        period: Optional[int] = None,
        room_name: Optional[str] = None,
        faculty_names: Optional[List[str]] = None,
        is_valid: bool = False,
        reason: Optional[str] = None,
        current_assigned_count: int = 0,
        class_name: Optional[str] = None
    ):
        if action == "EVALUATE_CANDIDATE":
            self.total_candidates_tested += 1
        elif action == "BACKTRACK":
            self.total_backtracks += 1
        elif action == "ASSIGN":
            self.total_assignments += 1

        if len(self.steps) < self.max_steps:
            step = VisualizerStep(
                step_index=len(self.steps) + 1,
                action=action,
                task_name=task_name,
                duration=duration,
                day=day,
                period=period,
                room_name=room_name,
                faculty_names=faculty_names or [],
                is_valid=is_valid,
                reason=reason,
                current_assigned_count=current_assigned_count,
                backtrack_count=self.total_backtracks,
                tested_count=self.total_candidates_tested,
                class_name=class_name
            )
            self.steps.append(step)

    def get_steps_dict(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.steps]
