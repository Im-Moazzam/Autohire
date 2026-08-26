# Seed resumes

Drop real `.pdf` / `.docx` resumes here before running `mise run db:seed-demo`. Gitignored
(only this README is tracked) — real resumes are other people's PII and don't belong in
git history. Share the files with your teammate directly (Drive, Slack, etc.), not
through a commit.

The filename becomes the candidate: `Sara_Khan.pdf` → full name "Sara Khan", email
`sara.khan@example.com`. Name files after the person. Any number of files — the seed
script cycles them through 6 submission-status archetypes (submitted, parsed, ranked x2,
parse-error, rejected), repeating the cycle if you drop more than 6.

If this folder is empty, the seed script falls back to the bundled
`backend/tests/fixtures/resumes/Moazzam_Resume.pdf` for every candidate, so a fresh clone
still seeds successfully.
