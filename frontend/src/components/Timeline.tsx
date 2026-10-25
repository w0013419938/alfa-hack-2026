/** История заявки из поля timeline. Новые события сверху; только что появившиеся подсвечены. */
import { Box, Group, Stack, Text, UnstyledButton } from "@mantine/core";
import { useEffect, useRef, useState } from "react";

import type { Schemas } from "../api/client";
import { COLORS, RADIUS } from "../theme";
import { dateTimeSeconds } from "../utils/format";

type Item = Schemas["TimelineItem"];

// Длинный комментарий (например, объяснение предложения) уже показан в своём блоке на странице,
// поэтому в истории он свёрнут до трёх строк и разворачивается по кнопке
const LONG_COMMENT = 160;

function Comment({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const isLong = text.length > LONG_COMMENT;
  return (
    <Stack gap={2} align="flex-start">
      <Text size="sm" lineClamp={isLong && !open ? 3 : undefined}>
        {text}
      </Text>
      {isLong && (
        <UnstyledButton onClick={() => setOpen(!open)} fz="sm" c={COLORS.textSecondary} td="underline" style={{ minHeight: 24 }}>
          {open ? "Свернуть" : "Показать полностью"}
        </UnstyledButton>
      )}
    </Stack>
  );
}

export function Timeline({ items }: { items: Item[] }) {
  const seen = useRef<number | null>(null);
  const [freshFrom, setFreshFrom] = useState<number | null>(null);

  // При первой загрузке ничего не подсвечиваем; дальше подсвечиваем добавившиеся события
  useEffect(() => {
    if (seen.current !== null && items.length > seen.current) {
      setFreshFrom(seen.current);
      const timer = setTimeout(() => setFreshFrom(null), 3500);
      seen.current = items.length;
      return () => clearTimeout(timer);
    }
    seen.current = items.length;
  }, [items.length]);

  const newestFirst = items.map((item, index) => ({ item, index })).reverse();

  return (
    <Stack gap="xs" data-testid="timeline">
      {newestFirst.map(({ item, index }) => (
        <Box
          key={`${item.at}-${index}`}
          className={freshFrom !== null && index >= freshFrom ? "event-new" : undefined}
          p="sm"
          style={{ borderRadius: RADIUS.control, borderLeft: `3px solid ${index === items.length - 1 ? COLORS.text : COLORS.border}` }}
        >
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
            <Stack gap={2}>
              <Text fw={600}>{item.title}</Text>
              {item.comment && <Comment text={item.comment} />}
              <Text size="xs" c={COLORS.textSecondary}>
                {item.actor}
              </Text>
            </Stack>
            <Text size="xs" c={COLORS.textSecondary} style={{ whiteSpace: "nowrap" }}>
              {dateTimeSeconds(item.at)}
            </Text>
          </Group>
        </Box>
      ))}
    </Stack>
  );
}
