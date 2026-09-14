export interface Department {
  id: string;
  name: string;
  code: string;
}

export interface ClassSection {
  id: string;
  name: string;
  department_id?: string;
  student_count: number;
  academic_year: string;
  semester: string;
}

export interface Faculty {
  id: string;
  name: string;
  short_name: string;
  email?: string;
  department_id?: string;
  unavailable_slots: { day: string; period: number }[];
  preferred_slots: { day: string; period: number }[];
}

export interface Room {
  id: string;
  name: string;
  type: string;
  lab_type?: string;
  capacity: number;
  building: string;
}

export interface Subject {
  id: string;
  course_code: string;
  name: string;
  type: string;
  periods_per_week: number;
  duration: number;
  requires_lab: boolean;
  required_lab_type?: string;
  class_section_id?: string;
  faculty_ids: string[];
}

export interface TimetableEntry {
  day: string;
  period: number;
  duration: number;
  class_section_id: string;
  subject_id: string;
  subject_name?: string;
  subject_code?: string;
  subject_type?: string;
  room_id: string;
  room_name?: string;
  faculty_ids: string[];
  faculty_names: string[];
  faculty_short_names: string[];
}

export interface Statistics {
  tasks: number;
  candidates_tested: number;
  backtracking_steps: number;
  valid_assignments: number;
  hard_constraint_violations: number;
  soft_constraint_penalty: number;
  quality_score: number;
  generation_time_ms: number;
}

export interface Timetable {
  id: string;
  class_section_id: string;
  class_name: string;
  academic_year: string;
  name: string;
  status: string;
  score: number;
  statistics: Statistics;
  entries: TimetableEntry[];
}
