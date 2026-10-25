/** Калькулятор на карточке продукта: сумма, срок и вид платежа → примерный платёж и график из GET /calculator (считает бэкенд). */
import { Box, Button, Group, Modal, NumberInput, SegmentedControl, SimpleGrid, Slider, Stack, Table, Text } from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, call, errorText, type Schemas } from "../api/client";
import { COLORS, RADIUS } from "../theme";
import { money, months } from "../utils/format";
import { MoneyFigure } from "./MoneyFigure";
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
  const [paymentType, setPaymentType] = useState<"annuity" | "differentiated">("annuity");
  const [scheduleOpen, schedule] = useDisclosure(false);
  const [debounced] = useDebouncedValue({ amount, term }, 300);

  const result = useQuery({
    queryKey: ["calculator", product.code, debounced.amount, debounced.term, paymentType],
    queryFn: () =>
      call(
        api.GET("/api/v1/calculator", {
          params: { query: { product: product.code, amount: debounced.amount, term: debounced.term, payment_type: paymentType } },
        }),
      ),
    enabled: debounced.amount > 0 && debounced.term > 0,
    retry: false,
    placeholderData: (previous) => previous,
  });

  function update(nextAmount: number, nextTerm: number) {
    setAmount(nextAmount);
    setTerm(nextTerm);
    onChange?.(nextAmount, nextTerm);
  }

  // Шаг слайдера суммы: 50 000 ₽ для небольших продуктов, 100 000 ₽ для крупных
  const amountStep = product.max_amount > 10_000_000 ? 100_000 : 50_000;

  return (
    <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid={`calculator-${product.code}`}>
      <Stack gap="md">
        <Group justify="space-between" align="center" gap="sm">
          <Text fw={600}>Калькулятор платежа</Text>
          {result.data && (
            // Подписи и список видов платежа приходят из API: фронт ничего не придумывает сам
            <SegmentedControl
              size="sm"
              value={paymentType}
              onChange={(value) => setPaymentType(value as "annuity" | "differentiated")}
              data={result.data.payment_type_options.map((item) => ({ value: item.code, label: item.label }))}
              aria-label="Вид платежа"
              data-testid="calc-payment-type"
            />
          )}
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
          <Stack gap={6}>
            <NumberInput
              label="Сумма, ₽"
              value={amount}
              onChange={(value) => update(Number(value) || 0, term)}
              min={0}
              step={amountStep}
              thousandSeparator=" "
              className="num"
            />
            <Slider
              value={Math.min(Math.max(amount, product.min_amount), product.max_amount)}
              onChange={(value) => update(value, term)}
              min={product.min_amount}
              max={product.max_amount}
              step={amountStep}
              label={(value) => money(value, true)}
              aria-label="Сумма кредита"
              size="md"
            />
            <Group justify="space-between">
              <Text size="xs" c={COLORS.textSecondary} className="num">
                {money(product.min_amount, true)}
              </Text>
              <Text size="xs" c={COLORS.textSecondary} className="num">
                {money(product.max_amount, true)}
              </Text>
            </Group>
          </Stack>
          <Stack gap={6}>
            <NumberInput
              label={<Term id="term">Срок, месяцев</Term>}
              value={term}
              onChange={(value) => update(amount, Number(value) || 0)}
              min={1}
              className="num"
            />
            <Slider
              value={Math.min(Math.max(term, product.min_term_months), product.max_term_months)}
              onChange={(value) => update(amount, value)}
              min={product.min_term_months}
              max={product.max_term_months}
              step={1}
              label={(value) => months(value)}
              aria-label="Срок кредита в месяцах"
              size="md"
            />
            <Group justify="space-between">
              <Text size="xs" c={COLORS.textSecondary} className="num">
                {months(product.min_term_months)}
              </Text>
              <Text size="xs" c={COLORS.textSecondary} className="num">
                {months(product.max_term_months)}
              </Text>
            </Group>
          </Stack>
        </SimpleGrid>
        {result.isError && (
          <Text size="sm" c={COLORS.accentText} role="alert">
            {errorText(result.error)}
          </Text>
        )}
        {result.data && !result.isError && (
          // Пока пересчёт в пути, старое значение остаётся на месте и слегка бледнеет, без мигания
          <Group
            justify="space-between"
            align="flex-end"
            wrap="wrap"
            gap="md"
            style={{ opacity: result.isFetching ? 0.55 : 1, transition: "opacity 150ms ease" }}
            aria-busy={result.isFetching}
          >
            <Stack gap={2}>
              <Text size="sm" c={COLORS.textSecondary}>
                <Term id="monthly_payment">{result.data.payment_label}</Term>
              </Text>
              <MoneyFigure value={result.data.monthly_payment} fontSize={34} data-testid="calc-payment" />
              <Text size="xs" c={COLORS.textSecondary}>
                {result.data.payment_caption}
              </Text>
            </Stack>
            <Stack gap={2} align="flex-end">
              <Text size="sm" c={COLORS.textSecondary} className="num" ta="right">
                <Term id="total_cost">Всего вы вернёте</Term> {money(result.data.total_payment)}
              </Text>
              <Text size="sm" c={COLORS.textSecondary} className="num" ta="right">
                <Term id="overpayment">Переплата</Term> {money(result.data.overpayment)}
              </Text>
            </Stack>
            <Text size="xs" c={COLORS.textSecondary} w="100%">
              {result.data.note}
            </Text>
            <Button variant="default" onClick={schedule.open} data-testid="calc-schedule-open">
              График платежей
            </Button>
          </Group>
        )}
      </Stack>
      <Modal opened={scheduleOpen} onClose={schedule.close} title={`График платежей: ${product.name}`} size="xl" fullScreen={false} centered>
        {result.data && (
          <Stack gap="sm">
            <Text size="sm" c={COLORS.textSecondary}>
              {money(result.data.amount)} на {months(result.data.term_months)}. {result.data.note}
            </Text>
            <Table.ScrollContainer minWidth={520} mah={420} type="native">
              <Table stickyHeader highlightOnHover data-testid="calc-schedule">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Месяц</Table.Th>
                    <Table.Th ta="right">Платёж</Table.Th>
                    <Table.Th ta="right">Основной долг</Table.Th>
                    <Table.Th ta="right">Проценты</Table.Th>
                    <Table.Th ta="right">Остаток долга</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {result.data.schedule.map((row) => (
                    <Table.Tr key={row.month}>
                      <Table.Td className="num">{row.month}</Table.Td>
                      <Table.Td ta="right" className="num">
                        {money(row.payment)}
                      </Table.Td>
                      <Table.Td ta="right" className="num">
                        {money(row.principal)}
                      </Table.Td>
                      <Table.Td ta="right" className="num">
                        {money(row.interest)}
                      </Table.Td>
                      <Table.Td ta="right" className="num">
                        {money(row.balance)}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          </Stack>
        )}
      </Modal>
    </Box>
  );
}
