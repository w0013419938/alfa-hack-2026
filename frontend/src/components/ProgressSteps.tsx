/**
 * Шкала этапов заявки это живая линия. Строится строго по полю progress из API: фронт не знает,
 * какому этапу соответствует статус.
 *
 * Движение отвечает только на изменение данных:
 * - когда этап пройден, заливка линии дорастает до следующего шага;
 * - новый текущий шаг один раз отмечается расходящимся кольцом (после того, как линия дошла).
 * Постоянного движения у шкалы нет: что банк работает, показывает индикатор над шкалой.
 * При prefers-reduced-motion всё это отключено (см. global.css).
 */
import { Box, Text, VisuallyHidden } from "@mantine/core";
import { IconCheck, IconUser, IconX } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";

import type { Schemas } from "../api/client";
import { COLORS } from "../theme";

type Step = Schemas["ProgressStep"];

const DOT = 36;
const RING_ROOM = 22; // место над кружком под кольцо прибытия, px
const SEGMENT_MS = 450; // задержка между отрезками, когда пройдено сразу несколько этапов

const DOT_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  done: { bg: COLORS.positive, color: COLORS.text, border: COLORS.positive },
  current: { bg: COLORS.accent, color: "#fff", border: COLORS.accent },
  action: { bg: COLORS.attention, color: "#fff", border: COLORS.attention },
  stopped: { bg: "#8E9099", color: "#fff", border: "#8E9099" },
  upcoming: { bg: COLORS.card, color: COLORS.textSecondary, border: "#D3D5DB" },
};

const SUBLABEL_COLOR: Record<string, string> = {
  current: COLORS.accentText,
  action: COLORS.attentionText,
  stopped: COLORS.textSecondary,
};

function StepIcon({ step, index }: { step: Step; index: number }) {
  if (step.state === "done") return <IconCheck size={18} stroke={3} aria-hidden />;
  if (step.state === "stopped") return <IconX size={18} stroke={3} aria-hidden />;
  if (step.state === "action") return <IconUser size={18} stroke={2.5} aria-hidden />;
  // У текущего шага номер белый на фирменном красном (4.1:1): 19 px весом 700 это крупный текст по WCAG, ему хватает 3:1
  if (step.state === "current")
    return (
      <span aria-hidden style={{ fontSize: 19, fontWeight: 700, lineHeight: 1 }}>
        {index + 1}
      </span>
    );
  return <span aria-hidden>{index + 1}</span>;
}

export function ProgressSteps({ steps }: { steps: Step[] }) {
  // Запоминаем активный этап, чтобы отметить переход на новый
  const activeCode = steps.find((step) => step.state !== "done" && step.state !== "upcoming")?.code ?? "all-done";
  const previous = useRef(activeCode);
  const [arrived, setArrived] = useState<string | null>(null);

  // Сколько этапов было пройдено при прошлом показе. За один опрос заявка может пройти несколько этапов —
  // тогда отрезки линии заполняются по очереди, и линия «бежит» от шага к шагу
  const doneCount = steps.filter((step) => step.state === "done").length;
  const previousDone = useRef(doneCount);
  const fromDone = Math.min(previousDone.current, doneCount);
  const runMs = (doneCount - fromDone) * SEGMENT_MS;

  useEffect(() => {
    previousDone.current = doneCount;
  }, [doneCount]);

  useEffect(() => {
    if (previous.current !== activeCode) {
      previous.current = activeCode;
      setArrived(activeCode);
      const timer = setTimeout(() => setArrived(null), 2600 + runMs);
      return () => clearTimeout(timer);
    }
  }, [activeCode, runMs]);

  return (
    // overflow-x: auto обрезает и по вертикали, поэтому сверху оставляем место под кольцо прибытия
    // (расходится на 18 px от кружка) и возвращаем его отрицательным отступом, чтобы шкала не сдвинулась
    <Box style={{ overflowX: "auto", paddingTop: RING_ROOM, marginTop: -RING_ROOM }} data-testid="progress">
      <Box component="ol" aria-label="Этапы заявки" m={0} p={0} miw={640} style={{ display: "flex", listStyle: "none", alignItems: "flex-start" }}>
        {steps.map((step, index) => {
          const style = DOT_STYLE[step.state] ?? DOT_STYLE.upcoming;
          const isLast = index === steps.length - 1;
          const isActive = step.code === activeCode;
          const dotClass = step.code === arrived ? "step-dot step-arrived" : "step-dot";
          return (
            <Box
              component="li"
              key={step.code}
              aria-current={isActive ? "step" : undefined}
              style={{ flex: 1, position: "relative", display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}
              data-step={step.code}
              data-state={step.state}
            >
              {!isLast && (
                // Дорожка до следующего шага; заливка растёт, когда этот шаг пройден
                <Box
                  aria-hidden
                  style={{
                    position: "absolute",
                    top: DOT / 2 - 2,
                    left: `calc(50% + ${DOT / 2 + 6}px)`,
                    right: `calc(-50% + ${DOT / 2 + 6}px)`,
                    height: 4,
                    borderRadius: 2,
                    background: "#E6E7EB",
                    overflow: "hidden",
                  }}
                >
                  <Box
                    className="step-line-fill"
                    h="100%"
                    bg={COLORS.positive}
                    style={{
                      transform: `scaleX(${step.state === "done" ? 1 : 0})`,
                      transitionDelay: index >= fromDone ? `${(index - fromDone) * SEGMENT_MS}ms` : undefined,
                    }}
                  />
                </Box>
              )}
              <Box
                className={dotClass}
                w={DOT}
                h={DOT}
                style={{
                  borderRadius: "50%",
                  display: "grid",
                  placeItems: "center",
                  background: style.bg,
                  color: style.color,
                  border: `2px solid ${style.border}`,
                  fontWeight: 600,
                  zIndex: 1,
                  transition: "background-color 300ms ease, border-color 300ms ease",
                  // Кольцо прибытия ждёт, пока линия добежит до шага
                  ["--ring-delay" as string]: `${runMs + 300}ms`,
                  ["--ring-color" as string]: step.state === "action" ? "rgba(155, 92, 255, 0.6)" : "rgba(239, 49, 36, 0.6)",
                }}
              >
                <StepIcon step={step} index={index} />
              </Box>
              <Box px={4} ta="center">
                <Text size="sm" fw={step.state === "upcoming" ? 400 : 600} c={step.state === "upcoming" ? COLORS.textSecondary : COLORS.text} lh={1.3}>
                  {step.label}
                </Text>
                {step.state !== "upcoming" && step.state !== "done" ? (
                  <Text size="xs" fw={600} c={SUBLABEL_COLOR[step.state] ?? COLORS.textSecondary} mt={2}>
                    {step.state_label}
                  </Text>
                ) : (
                  <VisuallyHidden>{step.state_label}</VisuallyHidden>
                )}
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
