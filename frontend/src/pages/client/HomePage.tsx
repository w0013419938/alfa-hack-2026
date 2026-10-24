/** Главная клиента: мои заявки со статусом и следующим шагом, кнопка «Получить финансирование», персональная лента. */
import { Badge, Box, Button, Card, Grid, Group, Stack, Text, Title, UnstyledButton } from "@mantine/core";
import { IconBulb, IconPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";

import { api, call, type Application } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { COLORS, RADIUS } from "../../theme";
import { dateTime, money, months } from "../../utils/format";

const STATE_COLOR: Record<string, string> = { current: "brand", action: "violet", stopped: "gray" };

/** Следующий шаг для клиента: подписи доступных действий из API, иначе — пояснение статуса */
function nextStep(application: Application): { text: string; isAction: boolean } {
  // «Редактировать», «Загрузить документ» и «Отозвать» — не следующий шаг, а возможности; показываем главное действие
  const actions = application.available_actions.filter((action) => action.enabled && !["edit", "upload_document", "cancel"].includes(action.code));
  if (actions.length > 0) {
    const labels = actions.map((action, index) => (index === 0 ? action.label : action.label.charAt(0).toLowerCase() + action.label.slice(1)));
    return { text: labels.join(" или "), isAction: true };
  }
  return { text: application.status_description, isAction: false };
}

function ApplicationRow({ application }: { application: Application }) {
  const navigate = useNavigate();
  const step = application.progress.find((item) => item.state !== "done" && item.state !== "upcoming");
  const next = nextStep(application);
  return (
    <UnstyledButton
      onClick={() => navigate(`/client/applications/${application.id}`)}
      p="lg"
      bg={COLORS.page}
      style={{ borderRadius: RADIUS.block, display: "block", width: "100%" }}
      data-testid="application-row"
    >
      <Stack gap={8}>
        <Group justify="space-between" wrap="wrap" gap="xs">
          <Text fw={600}>
            {application.product.name}, заявка № {application.number}
          </Text>
          <Badge
            color={step ? (STATE_COLOR[step.state] ?? "gray") : application.status === "ISSUED" ? "lime" : "gray"}
            variant="light"
            c={!step && application.status === "ISSUED" ? COLORS.positiveText : undefined}
          >
            {application.status_label}
          </Badge>
        </Group>
        <Text size="sm" c={COLORS.textSecondary} className="num">
          {money(application.amount)} на {months(application.term_months)}, обновлена {dateTime(application.updated_at)}
        </Text>
        <Text size="sm">
          <Text span fw={600} c={next.isAction ? COLORS.attention : COLORS.textSecondary}>
            {next.isAction ? "Ваш следующий шаг: " : "Что происходит: "}
          </Text>
          {next.text}
        </Text>
      </Stack>
    </UnstyledButton>
  );
}

function Feed() {
  const feed = useQuery({ queryKey: ["feed"], queryFn: () => call(api.GET("/api/v1/feed")) });
  return (
    <Card>
      <Stack gap="md">
        <Group gap="xs">
          <IconBulb color={COLORS.accent} />
          <Title order={3}>Подсказки для вас</Title>
        </Group>
        {feed.isLoading && <LoadingState />}
        {feed.isError && <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />}
        {feed.data?.length === 0 && <Text c={COLORS.textSecondary}>Пока подсказок нет.</Text>}
        {feed.data?.map((item) => (
          <Box key={item.id} p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid="feed-item">
            <Badge variant="light" color="gray" size="sm" mb={6}>
              {item.tag}
            </Badge>
            <Text fw={600}>{item.title}</Text>
            <Text size="sm" mt={4}>
              {item.text}
            </Text>
            <Text size="xs" c={COLORS.textSecondary} mt={8} data-testid="feed-reason">
              Почему показано: {item.reason}
            </Text>
          </Box>
        ))}
      </Stack>
    </Card>
  );
}

export function HomePage() {
  const { user } = useAuth();
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => call(api.GET("/api/v1/applications", { params: { query: { page: 1, page_size: 50 } } })),
    // Пока есть заявки в работе, список обновляется сам
    refetchInterval: (query) => (query.state.data?.items.some((item) => !item.is_final) ? 5000 : false),
  });
  const firstName = user?.full_name.split(" ")[1] ?? user?.full_name;

  return (
    <Stack gap="lg">
      <Card>
        <Group justify="space-between" wrap="wrap" gap="md">
          <Stack gap={4}>
            <Title order={1}>Здравствуйте, {firstName}!</Title>
            <Text c={COLORS.textSecondary} size="lg">
              {user?.company?.name}. Здесь ваши заявки на кредит и подсказки для бизнеса.
            </Text>
          </Stack>
          <Button component={Link} to="/client/products" size="lg" leftSection={<IconPlus />} data-testid="get-financing">
            Получить финансирование
          </Button>
        </Group>
      </Card>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Card>
            <Stack gap="md">
              <Title order={3}>Мои заявки</Title>
              {applications.isLoading && <LoadingState />}
              {applications.isError && <ErrorState error={applications.error} onRetry={() => void applications.refetch()} />}
              {applications.data?.items.length === 0 && (
                <EmptyState
                  title="У вас пока нет заявок"
                  text="Подберём кредит под вашу задачу за пару минут и покажем примерный платёж."
                  action={
                    <Button component={Link} to="/client/products">
                      Получить финансирование
                    </Button>
                  }
                />
              )}
              {applications.data?.items.map((application) => <ApplicationRow key={application.id} application={application} />)}
            </Stack>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Feed />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
