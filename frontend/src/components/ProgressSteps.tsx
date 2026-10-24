/**
 * Шкала этапов заявки. Строится строго по полю progress из API — фронт не знает,
 * какому этапу соответствует статус. Изменившийся этап коротко подсвечивается.
 */
import { Box, Group, Stack, Text, Tooltip } from "@mantine/core";
import { IconCheck, IconPlayerPause, IconX } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";

import type { Schemas } from "../api/client";
import { COLORS } from "../theme";

type Step = Schemas["ProgressStep"];

const DOT_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  done: { bg: COLORS.positive, color: COLORS.text, border: COLORS.positive },
  current: { bg: COLORS.accent, color: "#fff", border: COLORS.accent },
  action: { bg: COLORS.attention, color: "#fff", border: COLORS.attention },
  stopped: { bg: "#B9BBC2", color: "#fff", border: "#B9BBC2" },
  upcoming: { bg: COLORS.card, color: COLORS.textSecondary, border: COLORS.border },
};

function StepIcon({ step, index }: { step: Step; index: number }) {
  if (step.state === "done") return <IconCheck size={18} stroke={3} />;
  if (step.state === "stopped") return <IconX size={18} stroke={3} />;
  if (step.state === "action") return <IconPlayerPause size={16} stroke={3} />;
  return <>{index + 1}</>;
}

export function ProgressSteps({ steps }: { steps: Step[] }) {
  // Запоминаем, какой этап был активным, чтобы подсветить переход на новый
  const activeCode = steps.find((step) => step.state !== "done" && step.state !== "upcoming")?.code ?? "all-done";
  const previous = useRef(activeCode);
  const [changed, setChanged] = useState<string | null>(null);

  useEffect(() => {
    if (previous.current !== activeCode) {
      setChanged(activeCode);
      previous.current = activeCode;
      const timer = setTimeout(() => setChanged(null), 3500);
      return () => clearTimeout(timer);
    }
  }, [activeCode]);

  return (
    <Box style={{ overflowX: "auto" }} data-testid="progress">
      <Group gap={0} wrap="nowrap" align="flex-start" miw={620}>
        {steps.map((step, index) => {
          const style = DOT_STYLE[step.state] ?? DOT_STYLE.upcoming;
          const isLast = index === steps.length - 1;
          return (
            <Stack key={step.code} gap={8} align="center" style={{ flex: 1, position: "relative" }} data-step={step.code} data-state={step.state}>
              {!isLast && (
                <Box
                  style={{
                    position: "absolute",
                    top: 17,
                    left: "calc(50% + 22px)",
                    right: "calc(-50% + 22px)",
                    height: 3,
                    borderRadius: 2,
                    background: step.state === "done" ? COLORS.positive : COLORS.border,
                  }}
                />
              )}
              <Tooltip label={step.state_label}>
                <Box
                  className={changed === step.code ? "just-changed" : undefined}
                  w={36}
                  h={36}
                  style={{
                    borderRadius: "50%",
                    display: "grid",
                    placeItems: "center",
                    background: style.bg,
                    color: style.color,
                    border: `2px solid ${style.border}`,
                    fontWeight: 600,
                    zIndex: 1,
                  }}
                >
                  <span className={step.state === "current" ? "pulse" : undefined} style={{ display: "grid", placeItems: "center" }}>
                    <StepIcon step={step} index={index} />
                  </span>
                </Box>
              </Tooltip>
              <Stack gap={0} align="center" px={4}>
                <Text size="sm" fw={step.state === "upcoming" ? 400 : 600} ta="center" c={step.state === "upcoming" ? COLORS.textSecondary : COLORS.text}>
                  {step.label}
                </Text>
                {step.state !== "upcoming" && step.state !== "done" && (
                  <Text size="xs" fw={600} c={step.state === "action" ? COLORS.attention : step.state === "current" ? COLORS.accent : COLORS.textSecondary}>
                    {step.state_label}
                  </Text>
                )}
              </Stack>
            </Stack>
          );
        })}
      </Group>
    </Box>
  );
}
