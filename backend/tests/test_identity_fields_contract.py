import json
from pathlib import Path

from app.services.identity_fields import resolve_identity_fields

_CASES_PATH = Path(__file__).resolve().parents[2] / "docs" / "identity-fields-cases.json"


def test_matches_shared_contract_cases():
    """Golden file shared with frontend/src/lib/identityFields.test.ts (issue
    #23) — a case that passes here but fails there (or vice versa) means the two
    implementations have drifted and both need updating together."""
    cases = json.loads(_CASES_PATH.read_text())["cases"]
    for case in cases:
        email_index, name_index = resolve_identity_fields(case["labels"])
        assert (email_index is not None) == case["email"], case
        assert (name_index is not None) == case["name"], case
