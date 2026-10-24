/** Сквозные сценарии каждой демо-учётки клиента — от создания заявки до ожидаемого исхода, в браузере. */
import { expect, test } from "@playwright/test";

import { createAndSubmitStandardApplication, expectStatus, loginAs, PDF_FILE } from "./helpers";

test("client_good: подбор продукта → одобрение → подписание → выдача", async ({ page }) => {
  await loginAs(page, "client_good");
  await page.getByTestId("get-financing").click();

  // Подбор продукта по вопросам
  await page.getByTestId("purpose-select").click();
  await page.getByRole("option", { name: "Пополнение оборотных средств" }).click();
  await page.getByTestId("recommend").click();
  await page.getByTestId("apply-recommended-working_capital").click();

  // Анкета: сумма и срок подставлены из подбора
  await expect(page.getByTestId("form-amount")).toHaveValue("1 500 000");
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-revenue").fill("800000");
  await page.getByTestId("form-expenses").fill("550000");
  await page.getByTestId("form-payments").fill("0");
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-submit").click();

  // Статус меняется на глазах, без перезагрузки
  await expectStatus(page, "OFFER_SENT");
  await expect(page.getByTestId("offer")).toBeVisible();
  await expect(page.locator('[data-step="decision"]')).toHaveAttribute("data-state", "action");

  await page.locator('[data-action="accept_offer"]').click();
  await expectStatus(page, "OFFER_ACCEPTED");

  await page.locator('[data-action="sign"]').click();
  await expect(page.frameLocator('iframe[title="Кредитный договор"]').getByText("Кредитный договор")).toBeVisible();
  await expect(page.getByTestId("sign-confirm")).toBeDisabled();
  await page.getByTestId("sign-agree").check();
  await page.getByTestId("sign-confirm").click();

  await expectStatus(page, "ISSUED");
  await expect(page.locator('[data-step="issued"]')).toHaveAttribute("data-state", "done");
  await expect(page.locator("#documents").getByText("Кредитный договор")).toBeVisible();
});

test("client_medium: встречное предложение и отказ клиента", async ({ page }) => {
  await loginAs(page, "client_medium");
  await createAndSubmitStandardApplication(page);
  await expectStatus(page, "OFFER_SENT");
  const offer = page.getByTestId("offer");
  await expect(offer).toBeVisible();
  await expect(offer.getByText("Почему условия изменены")).toBeVisible();

  await page.locator('[data-action="decline_offer"]').click();
  await page.getByTestId("confirm-action").click();
  await expectStatus(page, "CLIENT_DECLINED");
});

test("client_bad: отказ с понятной причиной", async ({ page }) => {
  await loginAs(page, "client_bad");
  await createAndSubmitStandardApplication(page);
  await expectStatus(page, "REJECTED");
  await expect(page.getByTestId("timeline")).toContainText("ликвидации");
  await expect(page.getByTestId("actions")).toHaveCount(0);
});

test("client_info: запрос выписки → загрузка → уточнения → предложение", async ({ page }) => {
  await loginAs(page, "client_info");
  await createAndSubmitStandardApplication(page);
  await expectStatus(page, "NEEDS_INFO");
  const request = page.getByTestId("info-request");
  await expect(request).toBeVisible();
  // Пока выписки нет, «Отправить уточнения» неактивна
  await expect(page.locator('[data-action="provide_info"]')).toBeDisabled();

  await page.getByTestId("requested-bank_statement").locator('input[type="file"]').setInputFiles(PDF_FILE);
  await page.getByTestId("upload-bank_statement").click();
  await expect(page.locator('[data-action="provide_info"]')).toBeEnabled();

  await page.locator('[data-action="provide_info"]').click();
  await page.getByTestId("confirm-action").click();
  await expectStatus(page, "OFFER_SENT");
});

test("client_timeout: бюро не отвечает → рассмотрение специалистом", async ({ page }) => {
  await loginAs(page, "client_timeout");
  await createAndSubmitStandardApplication(page);
  await expectStatus(page, "MANUAL_REVIEW", 90_000);
  await expect(page.getByTestId("timeline")).toContainText("Бюро кредитных историй");
});

test("client_border: пограничный грейд → рассмотрение специалистом", async ({ page }) => {
  await loginAs(page, "client_border");
  await createAndSubmitStandardApplication(page);
  await expectStatus(page, "MANUAL_REVIEW");
  await expect(page.locator('[data-step="decision"]')).toHaveAttribute("data-state", "current");
});

test("анкета: понятные ошибки при незаполненных полях", async ({ page }) => {
  await loginAs(page, "client_good");
  await page.goto("/client/apply?product=working_capital");
  await page.getByTestId("form-next").click();
  await expect(page.getByText("Укажите сумму")).toBeVisible();
  await expect(page.getByText("Выберите цель кредита")).toBeVisible();
});
