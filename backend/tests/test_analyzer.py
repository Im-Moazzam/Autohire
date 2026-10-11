"""TS-15: the ANALYZER switch, and the validation boundary between a free-tier
model's reply and anything that reaches the database.

No test here makes a network call. LlmAnalyzer's HTTP client is faked, because
the behaviour worth pinning down is what happens to a *malformed* reply — which
is exactly what you cannot provoke on demand from a real provider.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from app.adapters.analyzer import LlmAnalyzer, LocalAnalyzer, _LlmPayload, get_analyzer
from app.core.config import settings


@pytest.fixture
def llm_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "analyzer", "llm")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(settings, "llm_model", "fake-model")
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")


def _fake_client(content: str) -> Mock:
    """Stands in for openai.OpenAI — only the one call path is exercised."""
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(total_tokens=123),
    )
    client = Mock()
    client.chat.completions.create.return_value = completion
    return client


def _analyzer_with(content: str) -> LlmAnalyzer:
    with patch("openai.OpenAI", return_value=_fake_client(content)):
        analyzer = LlmAnalyzer()
    # Usage logging opens its own session; irrelevant here and would need a DB.
    analyzer._log_usage = lambda response: None  # type: ignore[method-assign]
    return analyzer


_VALID_REPLY = (
    '{"relevance_score": 72, "matched_skills": ["python"], "missing_skills": ["kubernetes"], '
    '"feedback": "Strong backend fit.", "evidence_snippets": ["5 years of Python"]}'
)


# --- the ANALYZER switch ------------------------------------------------------


def test_analyzer_defaults_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "analyzer", "local")
    assert isinstance(get_analyzer(), LocalAnalyzer)


def test_analyzer_switches_to_llm(llm_settings: None) -> None:
    with patch("openai.OpenAI", return_value=Mock()):
        assert isinstance(get_analyzer(), LlmAnalyzer)


def test_unknown_analyzer_raises_naming_the_valid_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "analyzer", "gemini")
    with pytest.raises(NotImplementedError, match="ANALYZER=local"):
        get_analyzer()


def test_llm_analyzer_requires_its_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail at construction with the missing variable named, rather than on the
    first HTTP call with an opaque auth error from the provider."""
    monkeypatch.setattr(settings, "analyzer", "llm")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "fake-model")
    monkeypatch.setattr(settings, "llm_api_key", "fake-key")
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        get_analyzer()


# --- local mode contributes no score -----------------------------------------


def test_local_analyzer_returns_no_relevance_score() -> None:
    """Keyword overlap is not a relevance judgement. Feeding it into the blend
    would mix cosine with a worse proxy for cosine, so local mode ranks on
    embeddings alone — US-18's behaviour, preserved by ADR-006."""
    analysis = LocalAnalyzer().analyze("python and sql", "python developer")
    assert analysis.relevance_score is None
    assert analysis.matched_skills  # still produces skills and feedback


# --- what a free-tier model is allowed to return ------------------------------


def test_valid_reply_is_parsed(llm_settings: None) -> None:
    analysis = _analyzer_with(_VALID_REPLY).analyze("python role", "python developer")
    assert analysis.relevance_score == 72
    assert analysis.matched_skills == ["python"]
    assert analysis.missing_skills == ["kubernetes"]
    assert analysis.feedback == "Strong backend fit."
    assert analysis.evidence_snippets == ["5 years of Python"]


@pytest.mark.parametrize(
    "relevance",
    [101, -1, 1000],
    ids=["above-range", "below-range", "wildly-out-of-range"],
)
def test_out_of_range_relevance_score_is_rejected(llm_settings: None, relevance: int) -> None:
    """Bounded, not clamped. A model answering 120 has misunderstood the scale;
    silently rewriting that to 100 would skew a ranking with no trace. The raise
    propagates to batch_ranking, which degrades the candidate to cosine-only."""
    reply = _VALID_REPLY.replace('"relevance_score": 72', f'"relevance_score": {relevance}')
    with pytest.raises(ValidationError):
        _analyzer_with(reply).analyze("python role", "python developer")


@pytest.mark.parametrize(
    "reply",
    [
        "not json at all",
        '{"relevance_score": "high"}',
        '{"matched_skills": []}',
        "",
    ],
    ids=["prose", "wrong-type", "missing-score", "empty"],
)
def test_malformed_reply_raises_rather_than_writing_junk(llm_settings: None, reply: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        _analyzer_with(reply).analyze("python role", "python developer")


def test_resume_is_truncated_before_it_reaches_the_prompt(
    llm_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Free tiers are token-limited and resume_parser imposes no ceiling, so a
    pathologically long resume must not be sent whole."""
    monkeypatch.setattr(settings, "llm_max_resume_chars", 50)
    analyzer = _analyzer_with(_VALID_REPLY)
    analyzer.analyze("python role", "x" * 5000)

    sent = analyzer._client.chat.completions.create.call_args.kwargs["messages"]
    user_prompt = sent[-1]["content"]
    assert user_prompt.count("x") == 50


def test_rate_limit_is_retried_once(llm_settings: None) -> None:
    """One retry, because a free-tier per-minute cap tripped mid-demo would
    otherwise lose that candidate's analysis entirely."""
    analyzer = _analyzer_with(_VALID_REPLY)
    completion = analyzer._client.chat.completions.create.return_value
    analyzer._client.chat.completions.create.side_effect = [
        Exception("429 rate limit exceeded"),
        completion,
    ]
    with patch("app.adapters.analyzer.time.sleep") as sleep:
        analysis = analyzer.analyze("python role", "python developer")

    assert analysis.relevance_score == 72
    assert analyzer._client.chat.completions.create.call_count == 2
    sleep.assert_called_once()


def test_non_rate_limit_error_is_not_retried(llm_settings: None) -> None:
    analyzer = _analyzer_with(_VALID_REPLY)
    analyzer._client.chat.completions.create.side_effect = Exception("invalid api key")
    with pytest.raises(Exception, match="invalid api key"):
        analyzer.analyze("python role", "python developer")
    assert analyzer._client.chat.completions.create.call_count == 1


def test_payload_defaults_tolerate_omitted_lists() -> None:
    """A model that answers the score but skips an empty list shouldn't fail the
    candidate — only relevance_score is genuinely required."""
    payload = _LlmPayload.model_validate_json('{"relevance_score": 40}')
    assert payload.matched_skills == []
    assert payload.missing_skills == []
    assert payload.evidence_snippets == []
    assert payload.feedback is None
