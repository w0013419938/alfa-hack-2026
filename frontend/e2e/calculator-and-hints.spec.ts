/** Калькулятор с двумя видами платежа и графиком, чек-лист «Что понадобится», подсказки в анкете. */
import { expect, test } from "@playwright/test";

import { loginAs } from "./helpers";

test("калькулятор: платёж, который уменьшается, и график платежей", async ({ page }) => {
  await loginAs(page, "client_good");
  await page.goto("/client/products");
  await page.getByRole("tab", { name: "Все продукты" }).click();
  const calculator = page.getByTestId("calculator-working_capital");
  await expect(calculator).toBeVisible();
  await expect(calculator.getByTestId("calc-payment")).toBeVisible();
  await expect(calculator.getByText("Платёж в месяц (примерно)")).toBeVisible();
  const annuityPayment = await calculator.getByTestId("calc-payment").textContent();

  await calculator.getByTestId("calc-payment-type").getByText("Уменьшается со временем").click();
  await expect(calculator.getByText("Первый платёж (примерно)")).toBeVisible();
  await expect(calculator.getByText(/Дальше платёж уменьшается, последний будет/)).toBeVisible();
  await expect(calculator.getByTestId("calc-payment")).not.toHaveText(annuityPayment ?? "");

  await calculator.getByTestId("calc-schedule-open").click();
  const table = page.getByTestId("calc-schedule");
  await expect(table).toBeVisible();
  // В графике по одной строке на каждый месяц срока и остаток долга в конце равен нулю
  const rows = table.locator("tbody tr");
  const count = await rows.count();
  expect(count).toBeGreaterThanOrEqual(3);
  await expect(rows.last().locator("td").last()).toContainText("0 ₽");
});

test("анкета: «Что понадобится» и подсказки под полями", async ({ page }) => {
  await loginAs(page, "client_good");
  await page.goto("/client/apply?product=working_capital");
  await expect(page.getByTestId("checklist")).toContainText("Что понадобится");
  await expect(page.getByTestId("checklist")).toContainText("Выписка по расчётному счёту за последние 6 месяцев");
  await expect(page.getByTestId("checklist")).toContainText("Можно без этого");
  await expect(page.getByText("Выберите продукт, сумму и срок. Платёж посчитаем сразу.")).toBeVisible();
  await expect(page.getByText(/для выбранного продукта/)).toBeVisible();
});
