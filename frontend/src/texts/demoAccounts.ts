/**
 * Демо-учётки для быстрого входа на экране логина (те же, что в README и backend/seed/users.json).
 * Пароль каждой — <логин>123.
 */
export const DEMO_ACCOUNTS = [
  { login: "client_good", title: "Сильный заёмщик", scenario: "Банк одобрит кредит как просили, дальше подписание и выдача" },
  { login: "client_medium", title: "Высокая нагрузка", scenario: "Банк предложит меньшую сумму и объяснит почему" },
  { login: "client_border", title: "Пограничный случай", scenario: "Решение примет кредитный специалист" },
  { login: "client_bad", title: "Проблемная компания", scenario: "Отказ, причина видна сразу" },
  { login: "client_info", title: "Нет отчётности", scenario: "Банк попросит выписку по счёту, после неё даст предложение" },
  { login: "client_timeout", title: "Сбой бюро", scenario: "Бюро кредитных историй не отвечает, заявку решает специалист" },
  { login: "employee", title: "Сотрудник банка", scenario: "Очередь заявок, оценка заявки, решения и статистика" },
] as const;
