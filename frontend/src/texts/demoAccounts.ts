/**
 * Демо-учётки для быстрого входа на экране логина (те же, что в README и backend/seed/users.json).
 * Пароль каждой — <логин>123.
 */
export const DEMO_ACCOUNTS = [
  { login: "client_good", title: "Сильный заёмщик", scenario: "Одобрение на запрошенных условиях → подписание → выдача" },
  { login: "client_medium", title: "Высокая нагрузка", scenario: "Банк предлагает изменённые условия (встречное предложение)" },
  { login: "client_border", title: "Пограничный случай", scenario: "Заявку рассматривает кредитный специалист" },
  { login: "client_bad", title: "Проблемная компания", scenario: "Отказ с понятной причиной" },
  { login: "client_info", title: "Нет отчётности", scenario: "Банк просит выписку → загрузка → предложение" },
  { login: "client_timeout", title: "Сбой бюро", scenario: "Бюро кредитных историй не отвечает → специалист" },
  { login: "employee", title: "Сотрудник банка", scenario: "Очередь заявок, скоринг, решения, статистика" },
] as const;
