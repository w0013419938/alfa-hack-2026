/**
 * Крупная сумма: рубли в полный размер, копейки и знак рубля мельче и серым.
 * Только вид — число приходит из API, форматирует utils/format.
 */
import { Text, type TextProps } from "@mantine/core";

import { COLORS } from "../theme";
import { money } from "../utils/format";

export function MoneyFigure({ value, fontSize = 40, color = COLORS.text, ...props }: { value: number | null | undefined; fontSize?: number; color?: string } & Omit<TextProps, "size">) {
  const text = money(value); // «54 213,15 ₽» или «1 500 000 ₽»
  if (value === null || value === undefined) {
    return (
      <Text component="span" fz={fontSize} c={COLORS.textSecondary} {...props}>
        {text}
      </Text>
    );
  }
  const comma = text.indexOf(",");
  const whole = comma === -1 ? text.replace(" ₽", "") : text.slice(0, comma);
  const tail = comma === -1 ? " ₽" : text.slice(comma);
  return (
    <Text component="span" fz={fontSize} fw={600} c={color} lh={1.05} className="num" style={{ letterSpacing: "-0.02em" }} {...props}>
      {whole}
      <Text component="span" fz={Math.round(fontSize * 0.55)} fw={500} c={COLORS.textSecondary} style={{ letterSpacing: 0 }}>
        {tail}
      </Text>
    </Text>
  );
}
