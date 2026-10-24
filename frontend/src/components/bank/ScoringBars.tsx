/**
 * Наглядный вклад факторов скоринга: справа зелёная полоса «+ набрано баллов», слева красная «− недобрано».
 * Все числа (баллы, максимум, объяснения) приходят из API — здесь только рисунок.
 */
import { Badge, Box, Group, Stack, Text } from "@mantine/core";

import type { Schemas } from "../../api/client";
import { COLORS } from "../../theme";
import { Term } from "../Term";

type Scoring = Schemas["ScoringOut"];

export function ScoringBars({ scoring }: { scoring: Scoring }) {
  const scale = Math.max(1, ...scoring.factors.map((factor) => factor.max_points));
  return (
    <Stack gap="md" data-testid="scoring">
      <Group gap="md" align="baseline" wrap="wrap">
        <Text fz={40} fw={700} c={COLORS.accent} className="num" lh={1}>
          {scoring.total_score}
          <Text span fz={20} c={COLORS.textSecondary} fw={500}>
            {" "}
            / {scoring.max_score}
          </Text>
        </Text>
        <Badge size="xl" variant="light" color="gray">
          <Term id="grade">Грейд</Term> {scoring.grade} — {scoring.grade_label}
        </Badge>
      </Group>
      <Group gap="lg">
        <Group gap={6}>
          <Box w={12} h={12} bg={COLORS.positive} style={{ borderRadius: 3 }} />
          <Text size="xs" c={COLORS.textSecondary}>
            набрано баллов
          </Text>
        </Group>
        <Group gap={6}>
          <Box w={12} h={12} bg={COLORS.accent} style={{ borderRadius: 3, opacity: 0.75 }} />
          <Text size="xs" c={COLORS.textSecondary}>
            недобрано до максимума
          </Text>
        </Group>
      </Group>
      {scoring.factors.map((factor) => {
        const lost = factor.max_points - factor.points;
        return (
          <Stack key={factor.code} gap={4}>
            <Group justify="space-between" wrap="nowrap" gap="sm">
              <Text fw={600} size="sm">
                {factor.name}: <span className="num">{factor.value_text}</span>
              </Text>
              <Text size="sm" className="num" c={COLORS.textSecondary}>
                {factor.points} из {factor.max_points}
              </Text>
            </Group>
            <Box style={{ display: "grid", gridTemplateColumns: "1fr 2px 1fr", alignItems: "center", gap: 0 }}>
              <Box style={{ display: "flex", justifyContent: "flex-end" }}>
                {lost > 0 && (
                  <Box
                    h={14}
                    w={`${(lost / scale) * 100}%`}
                    bg={COLORS.accent}
                    style={{ borderRadius: "7px 0 0 7px", opacity: 0.75, display: "flex", alignItems: "center", justifyContent: "flex-start", paddingLeft: 4 }}
                  >
                    <Text fz={10} c="#fff" fw={700}>
                      −{lost}
                    </Text>
                  </Box>
                )}
              </Box>
              <Box h={20} bg={COLORS.text} />
              <Box>
                {factor.points > 0 && (
                  <Box
                    h={14}
                    w={`${(factor.points / scale) * 100}%`}
                    bg={COLORS.positive}
                    style={{ borderRadius: "0 7px 7px 0", display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 4 }}
                  >
                    <Text fz={10} c={COLORS.text} fw={700}>
                      +{factor.points}
                    </Text>
                  </Box>
                )}
              </Box>
            </Box>
            <Text size="xs" c={COLORS.textSecondary}>
              {factor.explanation}
            </Text>
          </Stack>
        );
      })}
      <Text size="xs" c={COLORS.textSecondary}>
        Правила скоринга: {scoring.rules_version}
      </Text>
    </Stack>
  );
}
