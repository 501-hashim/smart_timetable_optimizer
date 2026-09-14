import pytest
from backend.app.database.session import SessionLocal
from backend.app.seed.vast_s5_aiml import seed_vast_s5_aiml_data
from backend.app.schemas.timetable_schemas import GenerateRequest
from backend.app.services.timetable_service import TimetableService

def test_vast_s5_aiml_full_generation():
    db = SessionLocal()
    try:
        # Seed demo dataset
        seed_res = seed_vast_s5_aiml_data(db)
        assert seed_res["status"] == "success"

        # Run generator
        req = GenerateRequest(class_section_id="class-s5-aiml", optimization_enabled=True)
        res = TimetableService.generate(db, req)

        assert res.success is True
        assert res.timetable_id is not None
        assert len(res.entries) > 0
        assert res.statistics.hard_constraint_violations == 0
        assert res.score >= 70.0

        # Validate with independent validator
        val_res = TimetableService.validate(db, res.timetable_id)
        assert val_res.is_valid is True
        assert len(val_res.violations) == 0
        assert len(val_res.passed_checks) >= 5
    finally:
        db.close()
