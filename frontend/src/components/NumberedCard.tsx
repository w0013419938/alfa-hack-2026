/** Карточка с красным номером и заголовком — как на слайде «Как помогает предпринимателю» в макете. */
import { Box, Card, Group, Stack, Title } from "@mantine/core";
import type { ReactNode } from "react";

import { COLORS } from "../theme";

export function NumberBadge({ number, muted }: { number: number; muted?: boolean }) {
  return (
    <Box
      w={40}
      h={40}
      style={{
        borderRadius: "50%",
        background: muted ? COLORS.border : COLORS.accent,
        color: muted ? COLORS.textSecondary : "#fff",
        display: "grid",
        placeItems: "center",
        fontWeight: 600,
        fontSize: 20,
        flexShrink: 0,
      }}
    >
      {number}
    </Box>
  );
}

export function NumberedCard({ number, title, children }: { number: number; title: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <Stack gap="md">
        <Group gap="md" wrap="nowrap">
          <NumberBadge number={number} />
          <Title order={3}>{title}</Title>
        </Group>
        {children}
      </Stack>
    </Card>
  );
}
