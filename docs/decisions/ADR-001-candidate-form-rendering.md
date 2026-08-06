# ADR-001: Render the candidate application form in-app, not via Google Forms

- **Status:** Accepted
- **Date:** 2026-08-06
- **Affects:** EP-02, EP-03, US-06, US-11, US-12, `job_postings`, `template_fields`

## Context

The original design (SDS §1.3, Flow 2) had the recruiter define template fields in our
UI, which we would POST to the Google Forms API to generate a real Google Form. The
candidate would apply through that Form, uploading a resume into the recruiter's Drive.

Two independent blockers were found during architecture validation (TS-02):

1. **The Forms API cannot create file upload questions.** Google's own REST reference
   states the API does not support creating file upload questions. The Apps Script
   Forms service has no equivalent constructor either — its item types cover checkbox,
   multiple choice, date, grid, page break and so on, but not file upload. There is no
   supported programmatic path to a Form with a resume upload field.

2. **File upload questions require the responder to sign in to a Google Account.**
   Even a hand-built Form would force every candidate through a Google login. A paid
   third-party add-on ecosystem exists purely to work around this, which is itself
   evidence the limitation is real and permanent. This conflicts directly with US-11
   (open application link) and with the product goal of a low-friction candidate experience.

## Options considered

**A. Forms API + separate upload step.** Create the Form for text fields, then redirect
the candidate to our own upload page. Rejected: we still have to build the upload page,
so we pay the full cost of option C *plus* a Forms dependency, split state across two
systems, and a worse candidate experience.

**B. Manual Form creation by the recruiter.** Rejected: destroys US-06 (automated job
launch), which is a core product claim.

**C. Render the form ourselves.** Accepted.

## Decision

Serve the application form from our own React app at `/apply/{apply_slug}`, rendered
dynamically from `template_fields` rows. Resume uploads POST to our API, which streams
them to the job's Google Drive folder using the recruiter's OAuth token.

The recruiter-facing template builder is **unchanged** — same UI, same payload, same
tables. Only the consumer of that payload changes.

Google Forms is removed from the runtime path entirely. `google_form_id` and
`google_form_url` are kept on `job_postings` as nullable columns so the submitted ERD
remains accurate. `GOOGLE_FORMS` stays in `api_name_enum` for the same reason.

## Consequences

**Gained**
- Candidates apply without a Google account
- Submissions arrive as real-time webhooks to our own API instead of requiring a
  polling job to diff the Forms responses list
- Server-side validation of file type and size (TC-11, defect #5)
- `template_fields` / `candidate_form_responses` become load-bearing rather than
  redundant — the ERD as submitted already assumed this design

**Cost**
- We build a dynamic form renderer for 7 field types (~2-3 days)
- We own file upload security: magic-byte type checking, 5MB cap, IP rate limiting

**Report note:** record this in the SDS revision history and be ready to explain it in
the viva. Discovering a documented platform limitation during architecture validation
and adapting is exactly what TS-02 exists to catch.
