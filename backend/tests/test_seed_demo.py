from pathlib import Path

from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.scripts import seed_demo


def test_seed_demo_builds_a_single_live_job_with_freshly_submitted_candidates(
    db_session: Session,
) -> None:
    seed_demo.main()

    jobs = db_session.query(JobPosting).all()
    candidates = db_session.query(Candidate).all()

    assert len(jobs) == 1
    assert jobs[0].status == "LIVE"
    assert jobs[0].job_title == "Backend Engineer"
    assert len(candidates) >= 1
    for candidate in candidates:
        assert candidate.job_id == jobs[0].job_id
        assert candidate.submission_status == "SUBMITTED"
        assert candidate.resume_storage_key is not None
        assert Path(candidate.resume_storage_key).is_file()
