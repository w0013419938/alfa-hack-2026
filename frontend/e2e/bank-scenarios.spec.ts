/** Сотрудник и клиент вместе: решение сотрудника появляется у клиента без перезагрузки. */
import { expect, test } from "@playwright/test";

import { applicationNumber, createAndSubmitStandardApplication, expectStatus, loginAs, newClientPage, PDF_FILE } from "./helpers";

test("ручное рассмотрение: сотрудник одобряет — клиент сразу видит предложение", async ({ browser }) => {
  const client = await newClientPage(browser, "client_border");
  await createAndSubmitStandardApplication(client);
  await expectStatus(client, "MANUAL_REVIEW");
  const number = await applicationNumber(client);

  const employee = await newClientPage(browser, "employee");
  await employee.getByTestId("filter-manual").click();
  await employee.getByTestId("queue-row").filter({ hasText: number }).click();
  await expect(employee.getByTestId("scoring")).toBeVisible();
  await expect(employee.getByTestId("check-bki")).toBeVisible();

  // Без комментария решение не отправить
  await expect(employee.getByTestId("decision-submit")).toBeDisabled();
  await employee.getByTestId("decision-comment").fill("Одобряем: история в порядке, нагрузка допустимая");
  await employee.getByTestId("decision-submit").click();
  await expectStatus(employee, "OFFER_SENT");

  // Страница клиента открыта всё это время и обновилась сама
  await expectStatus(client, "OFFER_SENT");
  await expect(client.getByTestId("timeline")).toContainText("Одобряем: история в порядке");

  await client.locator('[data-action="accept_offer"]').click();
  await client.locator('[data-action="sign"]').click();
  await client.getByTestId("sign-agree").check();
  await client.getByTestId("sign-confirm").click();
  await expectStatus(client, "ISSUED");
});

test("запрос уточнений сотрудником → клиент загружает документ → заявка возвращается к специалисту", async ({ browser }) => {
  const client = await newClientPage(browser, "client_border");
  await createAndSubmitStandardApplication(client);
  await expectStatus(client, "MANUAL_REVIEW");
  const number = await applicationNumber(client);

  const employee = await newClientPage(browser, "employee");
  await employee.getByTestId("filter-manual").click();
  await employee.getByTestId("queue-row").filter({ hasText: number }).click();
  await employee.getByTestId("decision-actions").getByText("Запросить уточнения").click();
  await employee.getByTestId("request-documents").click();
  await employee.getByRole("option", { name: "Бухгалтерская или налоговая отчётность" }).click();
  await employee.keyboard.press("Escape");
  await employee.getByTestId("decision-comment").fill("Пришлите отчётность за последний год");
  await employee.getByTestId("decision-submit").click();
  await expectStatus(employee, "NEEDS_INFO");

  await expectStatus(client, "NEEDS_INFO");
  await expect(client.getByTestId("info-request")).toContainText("Пришлите отчётность за последний год");
  await client.getByTestId("requested-financial_report").locator('input[type="file"]').setInputFiles(PDF_FILE);
  await client.getByTestId("upload-financial_report").click();
  await client.locator('[data-action="provide_info"]').click();
  await client.getByTestId("confirm-action").click();

  // Ответ клиента снова проверяется, но решение остаётся за специалистом
  await expectStatus(client, "MANUAL_REVIEW");
  await expectStatus(employee, "MANUAL_REVIEW");
});

test("роли разведены: клиент не видит бэкофис, сотрудник — клиентский кабинет", async ({ page, browser }) => {
  await loginAs(page, "client_good");
  await page.goto("/bank");
  await expect(page).toHaveURL(/\/client$/);

  const employee = await newClientPage(browser, "employee");
  await employee.goto("/client");
  await expect(employee).toHaveURL(/\/bank$/);
  await employee.goto("/bank/stats");
  await expect(employee.getByText("Доля автоодобрений")).toBeVisible();
});

test("лента подсказок отличается у разных клиентов", async ({ browser }) => {
  const info = await newClientPage(browser, "client_info");
  const bad = await newClientPage(browser, "client_bad");
  await expect(info.getByTestId("feed-item").first()).toBeVisible();
  await expect(bad.getByTestId("feed-item").first()).toBeVisible();
  const infoTitles = await info.getByTestId("feed-item").allTextContents();
  const badTitles = await bad.getByTestId("feed-item").allTextContents();
  expect(infoTitles.join()).not.toEqual(badTitles.join());
  // У ИП есть подсказка «для ИП» с объяснением, почему она показана
  await expect(info.getByTestId("feed-reason").filter({ hasText: "ИП" })).toBeVisible();
});

test("неверный пароль — понятное сообщение", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Логин").fill("client_good");
  await page.getByLabel("Пароль").fill("wrong-password");
  await page.getByRole("button", { name: "Войти" }).click();
  await expect(page.getByTestId("login-error")).toHaveText("Неверный логин или пароль");
});
