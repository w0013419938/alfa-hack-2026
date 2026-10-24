import { defineConfig, devices } from "@playwright/test";

/**
 * E2E-тесты интерфейса. Запуск (поднимет весь стек и прогонит тесты в браузере Chromium):
 *   docker compose --profile e2e run --rm e2e
 * Тесты ходят в настоящий фронт → nginx → backend → mock-external, без подмен.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: true,
  workers: 3,
  retries: 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "test-results/report" }]],
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    locale: "ru-RU",
    viewport: { width: 1360, height: 900 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1360, height: 900 } } }],
});
