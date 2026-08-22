"""ResumeAnalyzer adapter (US-18). LocalAnalyzer is canned and deterministic
(ADR-003) — same input always yields the same matched/missing skills and
feedback text, never a score. A real LLM adapter is out of scope for this
story (cloud embedder is likewise not built); this is the local implementation
the Protocol requires.
"""

import re

from app.adapters.base import ResumeAnalysis, ResumeAnalyzer

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "in", "is", "it", "of", "on", "or", "our", "that", "the", "to",
    "was", "we", "will", "with", "you", "your",
}  # fmt: skip
_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+.#]{1,}")
_MAX_SKILLS = 10


def _keywords(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in _TOKEN_RE.finditer(text):
        token = match.group().lower()
        if token in _STOPWORDS or len(token) < 3:
            continue
        seen.setdefault(token, None)
    return list(seen)


class LocalAnalyzer:
    def analyze(self, jd_text: str, resume_text: str) -> ResumeAnalysis:
        jd_keywords = _keywords(jd_text)
        resume_keywords = set(_keywords(resume_text))

        matched = [kw for kw in jd_keywords if kw in resume_keywords][:_MAX_SKILLS]
        missing = [kw for kw in jd_keywords if kw not in resume_keywords][:_MAX_SKILLS]

        evidence = None
        if matched:
            lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
            matched_set = set(matched)
            evidence = [line for line in lines if any(kw in line.lower() for kw in matched_set)][
                :5
            ] or None

        if matched:
            feedback = (
                f"Matches {len(matched)} of {len(jd_keywords) or 1} job-description "
                f"terms, including {', '.join(matched[:3])}."
            )
        else:
            feedback = "No overlapping terms found between the resume and the job description."

        return ResumeAnalysis(
            matched_skills=matched,
            missing_skills=missing,
            feedback=feedback,
            evidence_snippets=evidence,
        )


def get_analyzer() -> ResumeAnalyzer:
    return LocalAnalyzer()
