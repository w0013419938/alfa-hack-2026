import { expect, type Browser, type Page } from "@playwright/test";

/** Вход через кнопку «Демо-доступ», так же, как это сделает жюри */
export async function loginAs(page: Page, login: string) {
  await page.goto("/login");
  await page.getByTestId(`demo-${login}`).click();
  await expect(page.getByTestId("current-user")).toBeVisible();
}

export async function newClientPage(browser: Browser, login: string): Promise<Page> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await loginAs(page, login);
  return page;
}

/** Стандартная анкета из docs/test-scenarios.md, через пошаговую форму */
export async function createAndSubmitStandardApplication(page: Page) {
  await page.goto("/client/apply?product=working_capital&amount=1500000&term=24&purpose=working_capital");
  await page.getByTestId("form-next").click(); // 1. параметры → черновик сохранён
  await expect(page.getByTestId("company-data")).toBeVisible(); // 2. данные компании подставлены
  await page.getByTestId("form-next").click();
  await page.getByTestId("form-revenue").fill("800000");
  await page.getByTestId("form-expenses").fill("550000");
  await page.getByTestId("form-payments").fill("0");
  await page.getByTestId("form-next").click(); // 3. финансы → сохранены
  await page.getByTestId("form-submit").click(); // 4. отправка
  await expect(page).toHaveURL(/\/client\/applications\/[0-9a-f-]+$/);
}

/** Ждём статус заявки на открытой странице, без перезагрузки: страница опрашивает API сама */
export async function expectStatus(page: Page, status: string, timeout = 60_000) {
  await expect(page.getByTestId("status-label")).toHaveAttribute("data-status", status, { timeout });
}

export async function applicationNumber(page: Page): Promise<string> {
  const text = await page.getByText(/Заявка № \d+/).first().textContent();
  return text!.match(/№ (\d+)/)![1];
}

/** Минимальный PDF для загрузки документа */
export const PDF_FILE = { name: "выписка.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4\n% e2e test\n%%EOF\n") };
