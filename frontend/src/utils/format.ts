/** Форматирование чисел и дат для показа (без вычислений — только вид). */

const moneyFormat = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const roundMoneyFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

export function money(value: number | null | undefined, round = false): string {
  if (value === null || value === undefined) return "—";
  // Копейки показываем, только если они есть: «1 500 000 ₽», но «54 213,15 ₽» и «115,60 ₽»
  const whole = Number.isInteger(value);
  return `${(round || whole ? roundMoneyFormat : moneyFormat).format(value)} ₽`;
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(value)}%`;
}

export function months(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value} мес.`;
}

export function dateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
}

export function date(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}
