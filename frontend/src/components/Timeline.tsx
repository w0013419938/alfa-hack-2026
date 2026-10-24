/** История заявки из поля timeline. Новые события сверху; только что появившиеся — подсвечены. */
import { Box, Group, Stack, Text } from "@mantine/core";
import { useEffect, useRef, useState } from "react";

import type { Schemas } from "../api/client";
import { COLORS, RADIUS } from "../theme";
import { dateTime } from "../utils/format";

type Item = Schemas["TimelineItem"];

export function Timeline({ items }: { items: Item[] }) {
  const seen = useRef<number | null>(null);
  const [freshFrom, setFreshFrom] = useState<number | null>(null);

  // При первой загрузке ничего не подсвечиваем; дальше — подсвечиваем добавившиеся события
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
          className={freshFrom !== null && index >= freshFrom ? "just-changed" : undefined}
          p="sm"
          style={{ borderRadius: RADIUS.control, borderLeft: `3px solid ${index === items.length - 1 ? COLORS.accent : COLORS.border}` }}
        >
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
            <Stack gap={2}>
              <Text fw={600}>{item.title}</Text>
              {item.comment && <Text size="sm">{item.comment}</Text>}
              <Text size="xs" c={COLORS.textSecondary}>
                {item.actor}
              </Text>
            </Stack>
            <Text size="xs" c={COLORS.textSecondary} style={{ whiteSpace: "nowrap" }}>
              {dateTime(item.at)}
            </Text>
          </Group>
        </Box>
      ))}
    </Stack>
  );
}
