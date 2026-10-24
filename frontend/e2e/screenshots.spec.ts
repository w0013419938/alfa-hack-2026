/**
 * Скриншоты ключевых экранов для docs/screenshots/.
 * Запуск: docker compose --profile e2e run --rm -e SCREENSHOTS=1 e2e npx playwright test --grep @screenshots
 */
import { expect, test } from "@playwright/test";

import { applicationNumber, createAndSubmitStandardApplication, expectStatus, loginAs, newClientPage } from "./helpers";

// Папку и ширину можно поменять для дизайн-ревью: SHOT_DIR=shots SHOT_WIDTH=768
const DIR = process.env.SHOT_DIR ?? "screenshots";
const WIDTH = Number(process.env.SHOT_WIDTH ?? 1360);

test.use({ viewport: { width: WIDTH, height: 900 } });

test("@screenshots ключевые экраны", async ({ page, browser }) => {
  test.setTimeout(240_000);
  await page.goto("/login");
  await page.screenshot({ path: `${DIR}/01-login.png`, fullPage: true });

  await loginAs(page, "client_info");
  await expect(page.getByTestId("feed-item").first()).toBeVisible();
  await page.screenshot({ path: `${DIR}/02-client-home.png`, fullPage: true });

  await page.getByTestId("get-financing").click();
  await page.getByTestId("purpose-select").click();
  await page.getByRole("option", { name: "Покупка оборудования" }).click();
  await page.getByTestId("recommend").click();
  await expect(page.getByText("Что вам подойдёт")).toBeVisible();
  await page.screenshot({ path: `${DIR}/03-product-picker.png`, fullPage: true });

  await page.goto("/client/apply?product=working_capital&amount=1500000&term=24&purpose=working_capital");
  await page.getByTestId("form-next").click();
  await expect(page.getByTestId("company-data")).toBeVisible();
  await page.screenshot({ path: `${DIR}/04-application-form.png`, fullPage: true });

  // Статус меняется на глазах: снимок во время проверки и после решения
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-revenue").fill("800000");
  await page.getByTestId("form-expenses").fill("550000");
  await page.getByTestId("form-payments").fill("0");
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-submit").click();
  await expectStatus(page, "VALIDATION", 10_000).catch(() => undefined);
  await page.screenshot({ path: `${DIR}/05-application-in-progress.png`, fullPage: true });
  await expectStatus(page, "NEEDS_INFO");
  await page.waitForTimeout(4000);
  await page.screenshot({ path: `${DIR}/06-application-needs-info.png`, fullPage: true });

  const medium = await newClientPage(browser, "client_medium");
  await createAndSubmitStandardApplication(medium);
  await expectStatus(medium, "OFFER_SENT");
  await medium.waitForTimeout(4000);
  await medium.screenshot({ path: `${DIR}/07-application-counter-offer.png`, fullPage: true });

  const border = await newClientPage(browser, "client_border");
  await createAndSubmitStandardApplication(border);
  await expectStatus(border, "MANUAL_REVIEW");
  const number = await applicationNumber(border);

  const employee = await newClientPage(browser, "employee");
  await expect(employee.getByTestId("queue-row").first()).toBeVisible();
  await employee.screenshot({ path: `${DIR}/08-bank-queue.png`, fullPage: true });
  await employee.locator(`[data-testid="queue-row"][data-number="${number}"]`).click();
  await expect(employee.getByTestId("scoring")).toBeVisible();
  await employee.screenshot({ path: `${DIR}/09-bank-application-card.png`, fullPage: true });
  await employee.goto("/bank/stats");
  await expect(employee.getByText("Доля автоодобрений")).toBeVisible();
  await employee.screenshot({ path: `${DIR}/10-bank-stats.png`, fullPage: true });
});
