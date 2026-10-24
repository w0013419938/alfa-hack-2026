/** Предложение банка: «Вы просили / Банк предлагает» и объяснение, если условия изменены. */
import { Alert, Badge, Box, Card, Divider, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

import type { Application } from "../../api/client";
import { COLORS, RADIUS } from "../../theme";
import { dateTime, money, months, percent } from "../../utils/format";
import { Term } from "../Term";

function Row({ label, asked, offered, highlight }: { label: ReactNode; asked: string; offered: string; highlight?: boolean }) {
  return (
    <>
      <Text c={COLORS.textSecondary}>{label}</Text>
      <Text className="num" ta="right">
        {asked}
      </Text>
      <Text className="num" ta="right" fw={600} c={highlight ? COLORS.accent : COLORS.text}>
        {offered}
      </Text>
    </>
  );
}

export function OfferCard({ application }: { application: Application }) {
  const offer = application.offer;
  if (!offer) return null;

  const changedAmount = offer.amount !== application.amount;
  const changedTerm = offer.term_months !== application.term_months;
  // Пояснение банка к предложению — комментарий последнего события, после которого появилось предложение
  const explanation = [...application.timeline].reverse().find((item) => item.status === "OFFER_SENT")?.comment;

  return (
    <Card data-testid="offer">
      <Stack gap="md">
        <Group justify="space-between" wrap="wrap">
          <Title order={3}>Предложение банка</Title>
          <Group gap="xs">
            <Badge color={offer.offer_type === "counter_offer" ? "violet" : "lime"} variant="light" c={offer.offer_type === "counter_offer" ? undefined : COLORS.positiveText}>
              {offer.offer_type === "counter_offer" ? <Term id="counter_offer">{offer.offer_type_label}</Term> : offer.offer_type_label}
            </Badge>
            <Badge color="gray" variant="light">
              {offer.status_label}
            </Badge>
          </Group>
        </Group>

        <Box style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr 1fr", columnGap: 16, rowGap: 12, alignItems: "baseline" }}>
          <span />
          <Text size="sm" c={COLORS.textSecondary} ta="right">
            Вы просили
          </Text>
          <Text size="sm" fw={600} ta="right">
            Банк предлагает
          </Text>
          <Row label="Сумма" asked={money(application.amount)} offered={money(offer.amount)} highlight={changedAmount} />
          <Row label={<Term id="term">Срок</Term>} asked={months(application.term_months)} offered={months(offer.term_months)} highlight={changedTerm} />
          <Row label={<Term id="rate">Ставка</Term>} asked="—" offered={`${percent(offer.rate)} годовых`} />
        </Box>

        <Divider />

        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          <Box p="md" bg={COLORS.accentSoft} style={{ borderRadius: RADIUS.block }}>
            <Text size="sm" c={COLORS.textSecondary}>
              <Term id="monthly_payment">Платёж в месяц</Term>
            </Text>
            <Text fz={28} fw={700} c={COLORS.accent} className="num">
              {money(offer.monthly_payment)}
            </Text>
            <Text size="xs" c={COLORS.textSecondary}>
              <Term id="annuity">аннуитетный</Term>, одинаковый каждый месяц
            </Text>
          </Box>
          <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }}>
            <Text size="sm" c={COLORS.textSecondary}>
              Всего вернуть
            </Text>
            <Text fz={22} fw={600} className="num">
              {money(offer.total_payment)}
            </Text>
          </Box>
          <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }}>
            <Text size="sm" c={COLORS.textSecondary}>
              <Term id="overpayment">Переплата</Term>
            </Text>
            <Text fz={22} fw={600} className="num">
              {money(offer.overpayment)}
            </Text>
          </Box>
        </SimpleGrid>

        {/* Объяснение показываем, только если условия изменены — иначе оно повторяет условия выше */}
        {explanation && offer.offer_type === "counter_offer" && (
          <Alert color="violet" radius="lg" title="Почему условия изменены">
            {explanation}
          </Alert>
        )}
        <Text size="sm" c={COLORS.textSecondary}>
          Предложение действует до {dateTime(offer.valid_until)}.
        </Text>
      </Stack>
    </Card>
  );
}
