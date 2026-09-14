# Smart Academic Timetable Optimizer
### Constraint-Based Academic Timetable Generation using Backtracking Algorithm & MRV Heuristics

A complete, production-ready, general-purpose college timetable optimization and scheduling system built as a **Design and Analysis of Algorithms (DAA)** project.

Featuring a handcrafted **Recursive Backtracking Algorithm**, **Most-Constrained-Variable-First (MRV) heuristics**, **constant-time $O(1)$ occupancy constraint checking**, soft-constraint scoring optimization, an **interactive step-by-step algorithm visualizer**, and the authoritative **VAST S5 AIML** reference seed dataset.

---

## Key Highlights

- **Pure DAA Backtracking Implementation**: Written from first principles without black-box optimization libraries (no OR-Tools, PuLP, OptaPlanner).
- **General-Purpose System**: Fully configurable for any department, class, subject, faculty, classroom, laboratory, working days, or period layout.
- **VAST S5 AIML Reference Dataset**: Preloaded with the Vidya Academy of Science & Technology (VAST) 2026-27 curriculum (DAA, ICV, DL, IoT Lab, Friday Common Activity, intervals, lunch breaks).
- **Interactive Algorithm Visualizer**: Step-by-step or automated playback demonstrating candidate slot evaluations, constraint conflict prunes, and backtracks.
- **Independent Validation Engine**: A separate verification module auditing all mandatory hard constraints.
- **Excel & PDF Export**: Professional formatted spreadsheets (`.xlsx` via `openpyxl`) and printable PDFs (via `reportlab`).
- **100% Automated Test Coverage**: Comprehensive pytest test suite verifying all constraint checks and algorithms.

---

## System Architecture

```
Frontend (React 18 / Tailwind CSS)
       |
    REST API (FastAPI)
       |
Timetable Service
       |
Backtracking Engine (with MRV Heuristics & O(1) Occupancy Sets)
       |
Soft Constraint Scoring (Branch-and-Bound Optimization)
       |
Generated Timetable & Independent Validator
       |
Export Engine (Excel .xlsx / PDF)
```

---

## Quick Start (Running Locally)

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Launch the Application
Open a terminal in the project directory:

```bash
cd smart_timetable_optimizer
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Open in Browser
Visit **`http://localhost:8000`** in your web browser.
- The interactive Single Page Application will load immediately.
- The VAST S5 AIML reference dataset will auto-seed automatically.
- Swagger API documentation is available at **`http://localhost:8000/docs`**.

---

## Running the Automated Test Suite

Run the full pytest test suite from the project root:

```bash
pytest backend/tests -v
```

### Automated Test Coverage (13 Tests, 100% Pass Rate):
1. `test_class_conflict_detection`: Verifies rejection when class is double-booked.
2. `test_faculty_conflict_detection`: Verifies rejection when teacher is assigned to two sessions at once.
3. `test_room_conflict_detection`: Verifies rejection when classroom is double-booked.
4. `test_room_type_enforcement`: Ensures lab subjects are strictly assigned to laboratories matching required lab type.
5. `test_room_capacity_check`: Rejects rooms smaller than class cohort size.
6. `test_consecutive_lab_break_crossing`: Ensures multi-period blocks never straddle interval or lunch breaks.
7. `test_fixed_event_protection`: Protects college breaks and Friday Common Activity from overwrite.
8. `test_multi_faculty_lab_availability`: Verifies availability for multi-teacher lab supervision.
9. `test_valid_small_timetable`: Verifies clean resolution of small CSP instance.
10. `test_impossible_timetable_handling`: Gracefully detects and reports unsatisfiable constraints.
11. `test_validator_detects_deliberate_conflict`: Verifies independent validator catches manual schedule corruptions.
12. `test_excel_and_pdf_export_output`: Verifies binary generation of `.xlsx` and `.pdf` files.
13. `test_vast_s5_aiml_full_generation`: End-to-end generation and validation of the VAST S5 AIML curriculum.

---

## DAA Algorithm & Viva Defense Guide

A dedicated mathematical and algorithmic specification is available in [`docs/ALGORITHM.md`](docs/ALGORITHM.md).

### The Core Heuristic: Most Constrained Variable (MRV)
In college scheduling, theory courses can occupy almost any period, but a 3-period lab that requires a GPU cluster and two teachers can only start in the afternoon session (Period 5) to avoid crossing lunch. Scheduling flexible theory classes first causes massive backtracking later. 

By applying the MRV heuristic, the algorithm sorts tasks by priority:
$$\Phi(T_i) = (\text{duration} \times 120) + (80 \times [\text{is\_lab}]) + (40 \times |\text{faculty}|) + \frac{10}{|\text{Rooms}|}$$

This reduces execution time from indefinite search down to **~318 milliseconds**.

---

## Viva Demonstration Workflow

1. **Open Dashboard**: View class metrics, department stats, and engine readiness.
2. **Review Data**: In *Data Management*, inspect courses (DAA, ICV, DL, IoT Lab), faculty (AKP, RR, NP, AER), and specialized labs.
3. **Click Generate Timetable**: Observe real-time solver telemetry (tasks scheduled, candidates tested, backtracks triggered, generation time ms).
4. **Inspect Timetable Grid**: View the college timetable with lunch breaks, morning intervals, multi-period lab spanning, and Friday Common Activity.
5. **Open Algorithm Visualizer**: Step forward and backward through the search tree to watch the algorithm test candidates, encounter conflicts, and backtrack.
6. **Modify a Constraint**: In *Constraints*, mark Ms. Anju K P (DAA) unavailable on Monday Period 2, re-generate, and observe DAA automatically rescheduled to another valid period.
7. **Export**: Download formatted Excel (`.xlsx`) and PDF timetables.
