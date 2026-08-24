import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./global-setup.ts",
  use: {
    baseURL: "http://localhost:5173",
  },
});
