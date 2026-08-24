import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

/** TS-06/R-13: the public apply flow is the only fully-built vertical slice
 * with no auth to fake — create a template and a job via the API using the
 * seeded session cookie, then drive /apply/{slug} in the browser. */

const API = "http://localhost:8000/api/v1";
const SESSION_COOKIE_NAME = "autohire_session";
const RESUME_FIXTURE = path.resolve(
  __dirname,
  "../../backend/tests/fixtures/resumes/Moazzam_Resume.pdf",
);

function seededSessionCookie(): string {
  const authFile = path.resolve(__dirname, "../.auth/session.json");
  const { sessionCookie } = JSON.parse(readFileSync(authFile, "utf-8")) as {
    sessionCookie: string;
  };
  return sessionCookie;
}

async function createJobWithApplySlug(request: import("@playwright/test").APIRequestContext) {
  const cookie = `${SESSION_COOKIE_NAME}=${seededSessionCookie()}`;

  const template = await request.post(`${API}/templates`, {
    headers: { Cookie: cookie },
    data: {
      template_name: `E2E Apply Flow ${Date.now()}`,
      fields: [
        { field_label: "Email", field_type: "SHORT_TEXT", is_required: true, field_order: 0 },
        {
          field_label: "Full Name",
          field_type: "SHORT_TEXT",
          is_required: true,
          field_order: 1,
        },
      ],
    },
  });
  expect(template.ok(), await template.text()).toBeTruthy();
  const templateBody = await template.json();

  const job = await request.post(`${API}/jobs`, {
    headers: { Cookie: cookie },
    data: {
      job_title: "E2E Backend Engineer",
      job_description: "Own the API layer for a recruitment platform.",
      template_id: templateBody.template_id,
      expires_at: new Date(Date.now() + 7 * 86_400_000).toISOString(),
    },
  });
  expect(job.ok(), await job.text()).toBeTruthy();
  const jobBody = await job.json();
  return jobBody.apply_slug as string;
}

test("apply form renders, submits, and rejects a duplicate email", async ({ page, request }) => {
  const slug = await createJobWithApplySlug(request);
  const email = `e2e-${Date.now()}@example.com`;

  await page.goto(`/apply/${slug}`);
  await expect(page.getByRole("heading", { name: "E2E Backend Engineer" })).toBeVisible();

  await page.getByLabel("Email *").fill(email);
  await page.getByLabel("Full Name *").fill("E2E Candidate");
  await page.locator('input[type="file"]').setInputFiles(RESUME_FIXTURE);
  await page.getByRole("button", { name: "Submit application" }).click();

  await expect(page.getByRole("heading", { name: "Application received" })).toBeVisible();

  // Duplicate: same job, same email.
  await page.goto(`/apply/${slug}`);
  await page.getByLabel("Email *").fill(email);
  await page.getByLabel("Full Name *").fill("E2E Candidate Again");
  await page.locator('input[type="file"]').setInputFiles(RESUME_FIXTURE);
  await page.getByRole("button", { name: "Submit application" }).click();

  await expect(page.getByText(/already exists|duplicate/i)).toBeVisible();
});
