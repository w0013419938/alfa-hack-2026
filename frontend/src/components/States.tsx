/** Общие состояния экрана: загрузка, ошибка, пусто. Используются на каждом экране. */
import { Alert, Button, Center, Loader, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconAlertTriangle, IconInbox } from "@tabler/icons-react";
import type { ReactNode } from "react";

import { errorText } from "../api/client";
import { COLORS } from "../theme";

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
