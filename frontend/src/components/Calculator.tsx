/** Калькулятор на карточке продукта: сумма и срок → примерный платёж из GET /calculator (считает бэкенд). */
import { Box, Group, NumberInput, Stack, Text } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, call, errorText, type Schemas } from "../api/client";
import { COLORS, RADIUS } from "../theme";
import { money } from "../utils/format";
import { Term } from "./Term";

type Product = Schemas["ProductOut"];

export function defaultAmount(product: Product): number {
  return Math.min(Math.max(1_000_000, product.min_amount), product.max_amount);
}

export function defaultTerm(product: Product): number {
  return Math.min(Math.max(24, product.min_term_months), product.max_term_months);
}

export function Calculator({
  product,
  onChange,
  initialAmount,
  initialTerm,
}: {
  product: Product;
  onChange?: (amount: number, term: number) => void;
  initialAmount?: number;
  initialTerm?: number;
}) {
  const [amount, setAmount] = useState<number>(initialAmount ?? defaultAmount(product));
  const [term, setTerm] = useState<number>(initialTerm ?? defaultTerm(product));
  const [debounced] = useDebouncedValue({ amount, term }, 400);

  const result = useQuery({
    queryKey: ["calculator", product.code, debounced.amount, debounced.term],
    queryFn: () =>
      call(api.GET("/api/v1/calculator", { params: { query: { product: product.code, amount: debounced.amount, term: debounced.term } } })),
    enabled: debounced.amount > 0 && debounced.term > 0,
    retry: false,
    placeholderData: (previous) => previous,
  });

  function update(nextAmount: number, nextTerm: number) {
    setAmount(nextAmount);
    setTerm(nextTerm);
    onChange?.(nextAmount, nextTerm);
  }

  return (
    <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid={`calculator-${product.code}`}>
      <Stack gap="sm">
        <Text fw={600}>Калькулятор платежа</Text>
        <Group grow wrap="wrap" align="flex-start">
          <NumberInput
            label="Сумма, ₽"
            value={amount}
            onChange={(value) => update(Number(value) || 0, term)}
            min={0}
            step={50_000}
            thousandSeparator=" "
            description={`от ${money(product.min_amount, true)} до ${money(product.max_amount, true)}`}
            miw={180}
          />
          <NumberInput
            label={<Term id="term">Срок, мес.</Term>}
            value={term}
            onChange={(value) => update(amount, Number(value) || 0)}
            min={1}
            description={`от ${product.min_term_months} до ${product.max_term_months} мес.`}
            miw={140}
          />
        </Group>
        {result.isError && (
          <Text size="sm" c="brand">
            {errorText(result.error)}
          </Text>
        )}
        {result.data && !result.isError && (
          <Stack gap={4}>
            <Group align="baseline" gap="xs">
              <Text size="sm" c={COLORS.textSecondary}>
                <Term id="monthly_payment">Платёж в месяц</Term> примерно
              </Text>
              <Text fz={26} fw={700} c={COLORS.accent} className="num" data-testid="calc-payment">
                {money(result.data.monthly_payment)}
              </Text>
            </Group>
            <Text size="sm" c={COLORS.textSecondary} className="num">
              Всего вернуть {money(result.data.total_payment)}, <Term id="overpayment">переплата</Term> {money(result.data.overpayment)}
            </Text>
            <Text size="xs" c={COLORS.textSecondary}>
              {result.data.note}
            </Text>
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
