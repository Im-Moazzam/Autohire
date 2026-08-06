import { expect, test } from "@playwright/test";

test("app loads and the API health endpoint is reachable", async ({ page, request }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/.+/);

  const health = await request.get("http://localhost:8000/api/v1/health");
  expect(health.ok()).toBeTruthy();
});
