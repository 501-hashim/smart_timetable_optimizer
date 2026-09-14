# System Architecture & Design Specification
## Project: Smart Academic Timetable Optimizer

---

## 1. System Overview & Component Hierarchy

The Smart Academic Timetable Optimizer is built using a clean, decoupled full-stack architecture designed for performance, algorithmic transparency, and zero-setup deployment.

```
+-------------------------------------------------------------------------+
|                         PRESENTATION LAYER                              |
|   React 18 Single Page Application (SPA) • Tailwind CSS • HTML5 Canvas  |
|   - Interactive Timetable Grid (Intervals, Lunch Breaks, Multi-Period)  |
|   - Real-Time DAA Algorithm Visualizer (Step-by-Step & Auto Playback)   |
|   - Data Management & Constraint Configuration Portal                   |
+-------------------------------------------------------------------------+
                                    |
                           REST API (HTTP / JSON)
                                    v
+-------------------------------------------------------------------------+
|                        APPLICATION / API LAYER                          |
|                       FastAPI Asynchronous Gateway                      |
|   /api/classes       /api/subjects       /api/faculty    /api/rooms     |
|   /api/timetable/generate                /api/timetable/validate        |
|   /api/timetable/visualize               /api/timetable/export          |
|   /api/demo/load                         /api/demo/reset                |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                            DOMAIN SERVICE LAYER                         |
|   TimetableService (Orchestrator) & ExportService (openpyxl / reportlab)|
+-------------------------------------------------------------------------+
            |                                           |
            v                                           v
+-----------------------+                   +-----------------------------+
|    DAA ENGINE LAYER   |                   |     VALIDATION LAYER        |
| BacktrackingEngine    |                   | IndependentValidator        |
| - MRV Heuristics      |                   | - 5 Mandatory Hard Audits   |
| - O(1) Occupancy Sets |                   | - Quality Score Evaluation  |
| - AlgorithmTracer     |                   +-----------------------------+
| - Scoring Optimizer   |
+-----------------------+
            |
            v
+-------------------------------------------------------------------------+
|                            PERSISTENCE LAYER                            |
|       SQLite Relational Database with SQLAlchemy 2.0 ORM Engine         |
+-------------------------------------------------------------------------+
```

---

## 2. Entity-Relationship & Relational Data Model

### Core Database Entities:
1. **`Department`**: Unique department code (`AIML`), full name.
2. **`ClassSection`**: Section title (`S5 AIML`), student cohort size (60), academic year (`2026-27`), semester (`Odd Semester`).
3. **`Faculty`**: Faculty name, short initials (`AKP`, `RR`, `NP`, `AER`), department, JSON arrays of unavailable and preferred time slots.
4. **`Room`**: Room name, room type (`THEORY` or `LAB`), lab cluster specification (`IOT`, `AI_DL`, `PROJECT`), seating capacity, building location.
5. **`Subject`**: Course code (`CST 301`), title, weekly period requirement (e.g. 4 periods), block duration (1 for theory, 3 for lab), lab requirement flags, assigned faculty ID list.
6. **`FixedEvent`**: Non-overwritable college events (e.g., Morning Interval, Lunch Break, Friday Common Activity).
7. **`GeneratedTimetable`**: Master record of generated schedule, status, evaluated score, execution statistics.
8. **`TimetableEntry`**: Individual assigned session storing `day`, `period`, `duration`, `class_id`, `subject_id`, `room_id`, and `faculty_ids`.

---

## 3. Data Flow

1. **User Initiation**: Administrator selects class (e.g., S5 AIML) and clicks "Generate Timetable".
2. **Task Decomposition**: `TimetableService` transforms subject requirements into discrete scheduling tasks.
3. **MRV Ordering**: Tasks are prioritized by difficulty (duration $\times$ 120 + lab requirement + faculty count).
4. **Backtracking Search**: Recursive engine assigns slots, checking collision in $O(1)$ via hash occupancy maps.
5. **Quality Optimization**: Branch-and-bound optimization searches for minimal idle gaps and maximum pedagogical balance.
6. **Persistence & Verification**: Schedule is committed to SQLite and independently validated by `IndependentValidator`.
7. **Presentation & Export**: Visualized on web grid with 1-click download to Excel (`.xlsx`) or PDF.
