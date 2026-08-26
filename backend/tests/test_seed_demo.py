from pathlib import Path

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.scripts import seed_demo


def test_seed_demo_builds_a_full_demo_world_with_real_resume_files(db_session: Session) -> None:
    seed_demo.main()

    jobs = db_session.query(JobPosting).all()
    candidates = db_session.query(Candidate).all()

    assert len(jobs) == 4
    assert {j.status for j in jobs} == {"DRAFT", "LIVE", "CLOSED"}
    assert len(candidates) >= 1
    for candidate in candidates:
        assert candidate.resume_storage_key is not None
        assert Path(candidate.resume_storage_key).is_file()
