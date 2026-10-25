/**
 * Предложение банка. Главная цифра — платёж в месяц. Ниже сравнение «Вы просили / Банк предлагает»:
 * изменённое значение выделено, старое зачёркнуто, а объяснение банка стоит прямо под строками, которые изменились.
 * Все числа и тексты — из API; здесь только сравнение «совпадает / не совпадает» для выделения.
 */
import { Badge, Box, Card, Group, Stack, Text, Title } from "@mantine/core";
import { IconArrowRight } from "@tabler/icons-react";
import { Fragment, type ReactNode } from "react";

import type { Application } from "../../api/client";
import { COLORS, RADIUS } from "../../theme";
import { dateTime, money, months, percent } from "../../utils/format";
import { MoneyFigure } from "../MoneyFigure";
import { Term } from "../Term";

type CompareRow = { key: string; label: ReactNode; asked: string; offered: string; changed: boolean };

function Figure({ label, value }: { label: ReactNode; value: number | null | undefined }) {
  return (
    <Stack gap={2}>
      <Text size="sm" c={COLORS.textSecondary}>
        {label}
      </Text>
      <MoneyFigure value={value} fontSize={22} />
    </Stack>
  );
}

/** actions — кнопки «Принять / Отказаться»: стоят прямо под условиями, чтобы решение принималось рядом с цифрами */
export function OfferCard({ application, actions }: { application: Application; actions?: ReactNode }) {
  const offer = application.offer;
  if (!offer) return null;

  const isCounter = offer.offer_type === "counter_offer";
  // Пояснение банка к предложению — комментарий последнего события, после которого появилось предложение
  const explanation = [...application.timeline].reverse().find((item) => item.status === "OFFER_SENT")?.comment;

  const rows: CompareRow[] = [
    { key: "amount", label: "Сумма", asked: money(application.amount), offered: money(offer.amount), changed: Number(offer.amount) !== Number(application.amount) },
    { key: "term", label: <Term id="term">Срок</Term>, asked: months(application.term_months), offered: months(offer.term_months), changed: offer.term_months !== application.term_months },
    { key: "rate", label: <Term id="rate">Ставка</Term>, asked: "—", offered: `${percent(offer.rate)} годовых`, changed: false },
  ];

  return (
    <Card data-testid="offer">
      <Stack gap="lg">
        <Group justify="space-between" wrap="wrap" gap="xs">
          <Title order={3}>Предложение банка</Title>
          <Badge color={isCounter ? "violet" : "lime"} variant="light" c={isCounter ? COLORS.attentionText : COLORS.positiveText}>
            {isCounter ? <Term id="counter_offer">{offer.offer_type_label}</Term> : offer.offer_type_label}
          </Badge>
        </Group>

        {/* Главная цифра: сколько платить каждый месяц */}
        <Group align="flex-end" justify="space-between" wrap="wrap" gap="lg">
          <Stack gap={4}>
            <Text c={COLORS.textSecondary}>
              <Term id="monthly_payment">Платёж в месяц</Term>
            </Text>
            <MoneyFigure value={offer.monthly_payment} fontSize={44} data-testid="offer-payment" />
            <Text size="sm" c={COLORS.textSecondary}>
              <Term id="annuity">Аннуитетный</Term>: одинаковый каждый месяц, {months(offer.term_months)}
            </Text>
          </Stack>
          <Group gap="xl" wrap="nowrap">
            <Figure label={<Term id="total_cost">Всего вы вернёте</Term>} value={offer.total_payment} />
            <Figure label={<Term id="overpayment">Переплата</Term>} value={offer.overpayment} />
          </Group>
        </Group>

        {/* Сравнение условий */}
        <Box
          p="md"
          bg={COLORS.page}
          style={{ borderRadius: RADIUS.block, display: "grid", gridTemplateColumns: "minmax(80px, 1fr) auto 20px auto", columnGap: 16, rowGap: 10, alignItems: "baseline" }}
        >
          <span />
          <Text size="sm" c={COLORS.textSecondary} ta="right">
            Вы просили
          </Text>
          <span />
          <Text size="sm" fw={600} ta="right">
            Банк предлагает
          </Text>
          {rows.map((row) => (
            <Fragment key={row.key}>
              <Text c={COLORS.textSecondary}>{row.label}</Text>
              <Text
                className="num"
                ta="right"
                c={COLORS.textSecondary}
                td={row.changed ? "line-through" : undefined}
                style={{ textDecorationThickness: 1 }}
              >
                {row.asked}
              </Text>
              <Box c={row.changed ? COLORS.accentText : "transparent"} style={{ alignSelf: "center", display: "grid" }} aria-hidden>
                <IconArrowRight size={16} />
              </Box>
              <Text className="num" ta="right" fw={600} c={row.changed ? COLORS.accentText : COLORS.text} data-changed={row.changed || undefined}>
                {row.offered}
              </Text>
            </Fragment>
          ))}
        </Box>

        {/* Объяснение сразу под сравнением: изменённые строки выделены выше, здесь — почему */}
        {explanation && isCounter && (
          <Box style={{ borderLeft: `3px solid ${COLORS.attention}`, borderRadius: 4 }} px="md" py={4}>
            <Text size="sm" fw={600} c={COLORS.attentionText}>
              Почему условия изменены
            </Text>
            <Text size="sm" mt={2}>
              {explanation}
            </Text>
          </Box>
        )}

        {actions}

        <Text size="sm" c={COLORS.textSecondary}>
          {offer.status === "active" ? `Предложение действует до ${dateTime(offer.valid_until)}.` : `Предложение: ${offer.status_label.toLowerCase()}.`}
        </Text>
      </Stack>
    </Card>
  );
}
