"""Resolves which template field answers a candidate's email and full name.

`candidates.email` / `candidates.full_name` are real columns, but the form is
template-driven — there is no reserved field for either. This module is the
single place that maps a field's label to one of those two columns, by a
normalised alias match, so template_service (reject at template save time)
and candidate_service (read the answer at submission time) can never drift
apart on what counts as "the email field".

Validating at template save time is the point: a template missing an email
field would otherwise only surface as a 500 on some future candidate's
submission, for a mistake the recruiter made and the candidate can't fix.
"""

import re
from collections.abc import Sequence


def _normalize(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", label.lower())


def resolve_identity_fields(labels: Sequence[str]) -> tuple[int | None, int | None]:
    """Returns (email_index, name_index) into `labels` — either may be None.

    Operates on plain labels, not field objects, so the caller (a list of
    ORM `TemplateField` rows here, `TemplateFieldIn` schemas there — two
    different types) does the trivial index-to-object lookup itself instead
    of this module needing to be generic over both.

    Substring match on the normalised label, not an exact alias table: "Email",
    "Your Email Address", and "Work Email" all resolve; only "email" itself is
    reserved so a name field never doubles as the email match. First field in
    template order wins on a repeat hit. Deliberately permissive — a false
    positive here just means the recruiter's 422 fires one field later, a
    false negative is the failure mode this check exists to prevent."""
    email_index: int | None = None
    name_index: int | None = None
    for index, label in enumerate(labels):
        norm = _normalize(label)
        if email_index is None and "email" in norm:
            email_index = index
        if name_index is None and "email" not in norm and "name" in norm:
            name_index = index
    return email_index, name_index
