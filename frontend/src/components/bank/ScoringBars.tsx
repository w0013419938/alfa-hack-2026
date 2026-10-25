/**
 * Скоринг для сотрудника.
 * ScoringSummary это сводка сверху карточки: балл и грейд, решение системы, главные риски, долговая нагрузка.
 * ScoringBars показывает вклад факторов: у каждого фактора дорожка длиной в его максимум баллов,
 * набранное залито зелёным, недобранное бледно-красным. Цвет значит «набрано / потеряно».
 * Все числа и тексты приходят из API; здесь только рисунок и сортировка для списка рисков.
 */
import { Box, Group, List, SimpleGrid, Stack, Text } from "@mantine/core";

import type { Schemas } from "../../api/client";
import { COLORS } from "../../theme";
import { money, months, percent } from "../../utils/format";
import { Term } from "../Term";
import { gradeColor } from "./grade";

type Scoring = Schemas["ScoringOut"];
type BankApplication = Schemas["BackofficeApplicationOut"];

const LOST_COLOR = "#FFC9C3";

function SummaryLabel({ children }: { children: React.ReactNode }) {
  return (
    <Text size="sm" c={COLORS.textSecondary} mb={6}>
      {children}
    </Text>
  );
}

/** Долговая нагрузка: какая часть месячной выручки уйдёт на платежи по всем кредитам вместе с новым.
 *  Округляем до целого процента, как в факторе скоринга, чтобы на экране было одно число */
function DebtLoad({ value }: { value: number }) {
  const share = Math.min(Math.max(value, 0), 1);
  return (
    <Stack gap={6} data-testid="debt-load">
      <Group justify="space-between" align="baseline" wrap="nowrap">
        <Text size="sm" c={COLORS.textSecondary}>
          <Term id="debt_load">Долговая нагрузка</Term>
        </Text>
        <Text fw={600} className="num">
          {percent(Math.round(value * 100))} выручки
        </Text>
      </Group>
      <Box h={10} bg="#E6E7EB" style={{ borderRadius: 5, overflow: "hidden" }} aria-hidden>
        <Box h="100%" w={`${share * 100}%`} bg={COLORS.text} style={{ borderRadius: 5 }} />
      </Box>
      <Text size="xs" c={COLORS.textSecondary}>
        Платежи по всем кредитам вместе с новым к месячной выручке
      </Text>
    </Stack>
  );
}

export function ScoringSummary({ application }: { application: BankApplication }) {
  const scoring = application.scoring;
  const decision = application.decision;
  // Главные риски это факторы, где потеряно больше всего баллов (по данным API)
  const risks = scoring
    ? [...scoring.factors].filter((factor) => factor.max_points > factor.points).sort((a, b) => b.max_points - b.points - (a.max_points - a.points)).slice(0, 3)
    : [];

  return (
    <SimpleGrid cols={{ base: 1, md: 3 }} spacing="xl" data-testid="scoring-summary">
      <Stack gap={4}>
        <SummaryLabel>
          <Term id="scoring">Оценка</Term>
        </SummaryLabel>
        {scoring ? (
          <>
            <Text fz={40} fw={600} lh={1} className="num" style={{ letterSpacing: "-0.02em" }}>
              {scoring.total_score}
              <Text span fz={20} fw={500} c={COLORS.textSecondary}>
                {" "}
                из {scoring.max_score}
              </Text>
            </Text>
            <Text fw={600} c={gradeColor(scoring.grade)}>
              <Term id="grade">Грейд</Term> {scoring.grade}: {scoring.grade_label.toLowerCase()}
            </Text>
            {scoring.debt_to_income !== null && (
              <Box mt="md">
                <DebtLoad value={scoring.debt_to_income} />
              </Box>
            )}
          </>
        ) : (
          <Text c={COLORS.textSecondary}>Скоринг ещё не проводился.</Text>
        )}
      </Stack>

      <Stack gap={4}>
        <SummaryLabel>Решение системы</SummaryLabel>
        {decision ? (
          <>
            <Text fw={600} size="lg">
              {decision.outcome_label}
            </Text>
            <List size="sm" spacing={2}>
              {decision.reasons.map((reason) => (
                <List.Item key={reason.code}>{reason.text}</List.Item>
              ))}
            </List>
            {application.suggested_offer && (
              <Text size="sm" c={COLORS.textSecondary} className="num" mt="xs">
                По запрошенным условиям: {money(application.suggested_offer.amount)} на {months(application.suggested_offer.term_months)} под{" "}
                {percent(application.suggested_offer.rate)}, платёж {money(application.suggested_offer.monthly_payment)} в месяц.
              </Text>
            )}
          </>
        ) : (
          <Text c={COLORS.textSecondary}>Система ещё не приняла решение.</Text>
        )}
      </Stack>

      <Stack gap={4}>
        <SummaryLabel>Главные риски</SummaryLabel>
        {risks.length === 0 && <Text c={COLORS.textSecondary}>{scoring ? "Все факторы набрали максимум." : "—"}</Text>}
        {risks.map((factor) => (
          <Group key={factor.code} justify="space-between" wrap="nowrap" align="flex-start" gap="sm">
            <Text size="sm">
              <Text span fw={600}>
                {factor.name}
              </Text>
              : {factor.value_text}
            </Text>
            <Text size="sm" fw={600} c={COLORS.accentText} className="num" style={{ whiteSpace: "nowrap" }}>
              −{factor.max_points - factor.points}
            </Text>
          </Group>
        ))}
      </Stack>
    </SimpleGrid>
  );
}

export function ScoringBars({ scoring }: { scoring: Scoring }) {
  const scale = Math.max(1, ...scoring.factors.map((factor) => factor.max_points));
  return (
    <Stack gap="md" data-testid="scoring">
      <Group gap="lg">
        <Group gap={6}>
          <Box w={12} h={12} bg={COLORS.positiveTrack} style={{ borderRadius: 3 }} />
          <Text size="xs" c={COLORS.textSecondary}>
            набрано баллов
          </Text>
        </Group>
        <Group gap={6}>
          <Box w={12} h={12} bg={LOST_COLOR} style={{ borderRadius: 3 }} />
          <Text size="xs" c={COLORS.textSecondary}>
            потеряно до максимума
          </Text>
        </Group>
      </Group>
      {scoring.factors.map((factor) => (
        <Stack key={factor.code} gap={6}>
          <Group justify="space-between" wrap="nowrap" gap="sm" align="baseline">
            <Text fw={600} size="sm">
              {factor.name}: <span className="num">{factor.value_text}</span>
            </Text>
            <Text size="sm" className="num" style={{ whiteSpace: "nowrap" }}>
              <Text span fw={600}>
                {factor.points}
              </Text>
              <Text span c={COLORS.textSecondary}>
                {" "}
                из {factor.max_points}
              </Text>
            </Text>
          </Group>
          {/* Дорожка длиной в максимум фактора: так видно и вес фактора, и сколько из него набрано */}
          <Box
            h={12}
            w={`${(factor.max_points / scale) * 100}%`}
            style={{ display: "flex", borderRadius: 6, overflow: "hidden", gap: 2 }}
            role="img"
            aria-label={`${factor.name}: ${factor.points} из ${factor.max_points} баллов`}
          >
            {factor.points > 0 && <Box h="100%" bg={COLORS.positiveTrack} style={{ flexGrow: factor.points, flexBasis: 0 }} />}
            {factor.max_points > factor.points && <Box h="100%" bg={LOST_COLOR} style={{ flexGrow: factor.max_points - factor.points, flexBasis: 0 }} />}
          </Box>
          <Text size="xs" c={COLORS.textSecondary}>
            {factor.explanation}
          </Text>
        </Stack>
      ))}
      <Text size="xs" c={COLORS.textSecondary}>
        Правила скоринга: {scoring.rules_version}
      </Text>
    </Stack>
  );
}
