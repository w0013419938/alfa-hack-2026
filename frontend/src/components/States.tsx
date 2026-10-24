/** Общие состояния экрана: загрузка, ошибка, пусто. Используются на каждом экране. */
import { Alert, Box, Button, Card, Center, Grid, Group, Loader, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { useReducedMotion } from "@mantine/hooks";
import { IconAlertTriangle, IconInbox } from "@tabler/icons-react";
import type { ReactNode } from "react";

import { errorText } from "../api/client";
import { COLORS, RADIUS } from "../theme";

export function LoadingState({ text = "Загружаем…" }: { text?: string }) {
  return (
    <Center py={60}>
      <Stack align="center" gap="sm">
        <Loader color="brand" />
        <Text c={COLORS.textSecondary}>{text}</Text>
      </Stack>
    </Center>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <Alert color="brand" radius="lg" icon={<IconAlertTriangle />} title="Не получилось загрузить данные">
      <Stack gap="sm" align="flex-start">
        <Text size="sm">{errorText(error)}</Text>
        {onRetry && (
          <Button variant="light" size="xs" onClick={onRetry}>
            Попробовать ещё раз
          </Button>
        )}
      </Stack>
    </Alert>
  );
}

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <Center py={40}>
      <Stack align="center" gap="xs" maw={420} ta="center">
        <ThemeIcon size={56} radius="xl" variant="light" color="gray">
          <IconInbox size={28} />
        </ThemeIcon>
        <Text fw={600} size="lg">
          {title}
        </Text>
        {text && <Text c={COLORS.textSecondary}>{text}</Text>}
        {action}
      </Stack>
    </Center>
  );
}

/*
 * Скелетоны: будущая раскладка экрана, где каждое значение заменено серой плашкой его размера.
 * Когда данные приходят, ничего не сдвигается. Пульсация отключается при prefers-reduced-motion.
 */

function Bar({ h = 16, w = "100%", radius = 8 }: { h?: number; w?: number | string; radius?: number }) {
  const reduced = useReducedMotion();
  return <Skeleton h={h} w={w} radius={radius} animate={!reduced} />;
}

/** Страница заявки (клиента или сотрудника): карточка статуса, шкала этапов, две колонки */
export function ApplicationSkeleton({ label = "Загружаем заявку" }: { label?: string }) {
  return (
    <Stack gap="lg" aria-busy="true" aria-label={label}>
      <Bar h={14} w={120} />
      <Card>
        <Stack gap="md">
          <Bar h={16} w="45%" />
          <Bar h={42} w="38%" radius={12} />
          <Bar h={18} w="70%" />
          <Group gap="sm">
            <Bar h={44} w={190} radius={RADIUS.control} />
            <Bar h={44} w={220} radius={RADIUS.control} />
          </Group>
        </Stack>
      </Card>
      <Card>
        <Group justify="space-between" wrap="nowrap">
          {Array.from({ length: 7 }, (_, index) => (
            <Stack key={index} align="center" gap={10} style={{ flex: 1 }}>
              <Bar h={36} w={36} radius={18} />
              <Bar h={12} w="60%" />
            </Stack>
          ))}
        </Group>
      </Card>
      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card>
            <Stack gap="md">
              <Bar h={24} w="40%" />
              <Bar h={44} w="35%" radius={12} />
              <RowsSkeleton rows={3} height={28} />
            </Stack>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card>
            <Stack gap="md">
              <Bar h={24} w="50%" />
              <RowsSkeleton rows={4} height={52} />
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}

/** Список строк фиксированной высоты: очередь, заявки, подсказки */
export function RowsSkeleton({ rows = 5, height = 48 }: { rows?: number; height?: number }) {
  return (
    <Stack gap="sm" aria-busy="true" aria-label="Загружаем">
      {Array.from({ length: rows }, (_, index) => (
        <Box key={index}>
          <Bar h={height} radius={RADIUS.control} />
        </Box>
      ))}
    </Stack>
  );
}
