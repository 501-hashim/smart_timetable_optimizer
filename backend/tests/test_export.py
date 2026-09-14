import pytest
from backend.app.services.export_service import generate_excel_timetable, generate_pdf_timetable

def test_excel_and_pdf_export_output():
    entries = [
        {
            "day": "Monday", "period": 1, "duration": 1, "class_section_id": "c1",
            "subject_id": "s1", "subject_code": "DAA", "subject_name": "Design & Analysis of Algorithms",
            "room_id": "r1", "room_name": "Room 301", "faculty_short_names": ["AKP"]
        },
        {
            "day": "Tuesday", "period": 5, "duration": 3, "class_section_id": "c1",
            "subject_id": "s2", "subject_code": "IOT_LAB", "subject_name": "IoT Lab",
            "room_id": "r2", "room_name": "IoT Lab", "faculty_short_names": ["AER", "MK"]
        }
    ]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = [1, 2, 3, 4, 5, 6, 7]
    fixed_events = [{"day": "Friday", "period": 7, "name": "Common Activity"}]

    excel_data = generate_excel_timetable("S5 AIML", "2026-27", entries, days, periods, fixed_events)
    assert isinstance(excel_data, bytes)
    assert len(excel_data) > 1000

    pdf_data = generate_pdf_timetable("S5 AIML", "2026-27", entries, days, periods, fixed_events)
    assert isinstance(pdf_data, bytes)
    assert len(pdf_data) > 1000
