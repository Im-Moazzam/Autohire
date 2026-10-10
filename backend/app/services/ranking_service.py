import csv
import io
import re
import uuid
from datetime import UTC, datetime

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_analysis_result import AiAnalysisResult
from app.models.candidate import Candidate
from app.models.job import JobPosting
from app.models.template import TemplateField
from app.schemas.common import PaginationParams
from app.services.candidate_service import resume_url_for


def list_ranked_candidates(
    db: Session,
    job_id: uuid.UUID,
    params: PaginationParams,
    min_score: float | None,
    skill: str | None,
) -> tuple[list[tuple[Candidate, AiAnalysisResult]], int]:
    """Mirrors candidate_service.list_candidates: a COUNT over the filtered
    subquery, then one bounded page (TC-13) — never N+1 over analysis rows."""
    base = (
        select(Candidate, AiAnalysisResult)
        .join(AiAnalysisResult, AiAnalysisResult.candidate_id == Candidate.candidate_id)
        .where(Candidate.job_id == job_id, Candidate.deleted_at.is_(None))
    )
    if min_score is not None:
        base = base.where(AiAnalysisResult.semantic_score >= min_score)
    if skill:
        base = base.where(AiAnalysisResult.matched_skills.contains([skill]))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(AiAnalysisResult.rank_position.asc())
        .offset((params.page - 1) * params.size)
        .limit(params.size)
    ).all()
    return [(row[0], row[1]) for row in rows], total


def processed_at_for_job(db: Session, job_id: uuid.UUID) -> datetime | None:
    """Null until BATCH_RANKING has completed once — a job never ranked is a
    200 with an empty shortlist (TC-10), not something to 404 or fake a
    timestamp for."""
    return db.scalar(
        select(func.max(AiAnalysisResult.processed_at)).where(AiAnalysisResult.job_id == job_id)
    )


# TS-16: ranked-candidate export (CSV/XLSX). An export is a file download, not
# a Page[T] list — ADR-004 P5's documented-exception mechanism — but it must
# still never be an unbounded query (CLAUDE.md), hence the hard cap rather
# than exporting every ranked candidate unconditionally.
# ponytail: in-memory row cap, stream if a job ever exports >5k rows — a
# single recruiter's job runs to tens of candidates today.
EXPORT_ROW_CAP = 5000

_EXPORT_BASE_COLUMNS = [
    "Rank",
    "Name",
    "Email",
    "Phone",
    "Match Score",
    "Status",
    "Matched Skills",
    "Missing Skills",
    "AI Feedback",
]
_EXPORT_TRAILING_COLUMNS = ["Submitted At", "Resume URL"]


def export_rows(db: Session, job_id: uuid.UUID) -> list[tuple[Candidate, AiAnalysisResult]]:
    """Ranked candidates only, bounded by EXPORT_ROW_CAP. Reuses
    list_ranked_candidates's single bounded query rather than looping pages."""
    rows, _ = list_ranked_candidates(
        db, job_id, PaginationParams(page=1, size=EXPORT_ROW_CAP), None, None
    )
    return rows


def export_filename(job: JobPosting, fmt: str) -> str:
    # job_title is recruiter-supplied text and must never reach a response
    # header raw (same discipline download_resume applies to the resume
    # filename). apply_slug is already a random token; the character filter
    # is defence in depth, not the only thing standing between this and an
    # injected header.
    safe_slug = re.sub(r"[^A-Za-z0-9_-]", "_", job.apply_slug)
    date = datetime.now(UTC).strftime("%Y%m%d")
    return f"{safe_slug}-candidates-{date}.{fmt}"


def _export_row_values(
    candidate: Candidate,
    analysis: AiAnalysisResult,
    template_fields: list[TemplateField],
    responses: dict[str, str],
) -> list[object]:
    base: list[object] = [
        analysis.rank_position,
        candidate.full_name,
        candidate.email,
        candidate.phone_number or "",
        round(analysis.semantic_score, 4),
        candidate.submission_status.value,
        ", ".join(analysis.matched_skills or []),
        ", ".join(analysis.missing_skills or []),
        analysis.ai_feedback_summary or "",
    ]
    template_values = [responses.get(field.field_label, "") for field in template_fields]
    trailing: list[object] = [candidate.submitted_at.isoformat(), resume_url_for(candidate) or ""]
    return base + template_values + trailing


def build_export_file(
    job: JobPosting,
    rows: list[tuple[Candidate, AiAnalysisResult]],
    responses_by_candidate: dict[uuid.UUID, dict[str, str]],
    fmt: str,
) -> tuple[bytes, str]:
    """Column order: stable identity + score columns, the AI block, then the
    variable-width template-field answers (differs per job's template, by
    design), then two trailing meta columns."""
    template_fields = job.template.fields
    headers = (
        _EXPORT_BASE_COLUMNS
        + [field.field_label for field in template_fields]
        + _EXPORT_TRAILING_COLUMNS
    )
    data_rows = [
        _export_row_values(
            candidate,
            analysis,
            template_fields,
            responses_by_candidate.get(candidate.candidate_id, {}),
        )
        for candidate, analysis in rows
    ]

    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        writer.writerows(data_rows)
        # utf-8-sig is the UTF-8 BOM the contract asks for — what makes Excel
        # open a non-ASCII candidate name without mangling it.
        return buffer.getvalue().encode("utf-8-sig"), "text/csv"

    # ponytail: build the workbook in memory, stream if a job ever exports
    # more than EXPORT_ROW_CAP rows.
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in data_rows:
        sheet.append(row)
    xlsx_buffer = io.BytesIO()
    workbook.save(xlsx_buffer)
    return (
        xlsx_buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
