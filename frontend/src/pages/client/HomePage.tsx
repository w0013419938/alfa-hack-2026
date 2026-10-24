/** Главная клиента: мои заявки со статусом и следующим шагом, кнопка «Получить финансирование», персональная лента. */
import { Badge, Box, Button, Card, Grid, Group, Stack, Text, Title, UnstyledButton } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
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

/** Мини-шкала этапов: полоска из сегментов по полю progress, цвет сегмента — состояние этапа */
const SEGMENT_COLOR: Record<string, string> = {
  done: COLORS.positive,
  current: COLORS.accent,
  action: COLORS.attention,
  stopped: "#8E9099",
  upcoming: "#E6E7EB",
};

function MiniProgress({ application }: { application: Application }) {
  const steps = application.progress;
  const activeIndex = steps.findIndex((item) => item.state !== "done" && item.state !== "upcoming");
  const active = activeIndex === -1 ? null : steps[activeIndex];
  return (
    <Stack gap={8}>
      <Box style={{ display: "flex", gap: 4 }} aria-hidden>
        {steps.map((step) => (
          <Box
            key={step.code}
            h={8}
            bg={SEGMENT_COLOR[step.state] ?? SEGMENT_COLOR.upcoming}
            style={{ flex: 1, borderRadius: 4, transition: "background-color 400ms ease" }}
            className={step.state === "current" ? "step-working" : undefined}
          />
        ))}
      </Box>
      {active && (
        <Text size="sm" c={COLORS.textSecondary}>
          Этап {activeIndex + 1} из {steps.length}: {active.label.toLowerCase()}, {active.state_label.toLowerCase()}
        </Text>
      )}
    </Stack>
  );
}

/** Текущая заявка — самая свежая незавершённая: крупно, со шкалой и следующим шагом */
function CurrentApplication({ application }: { application: Application }) {
  const next = nextStep(application);
  return (
    <Card data-testid="current-application">
      <Stack gap="md">
        <Text c={COLORS.textSecondary}>
          {application.product.name}, заявка № {application.number}, <span className="num">{money(application.amount)}</span> на {months(application.term_months)}
        </Text>
        <Title order={2} fz={30}>
          {application.status_label}
        </Title>
        <MiniProgress application={application} />
        <Text size="lg" maw={640}>
          {next.isAction ? (
            <>
              <Text span fw={600} c={COLORS.attentionText}>
                Ваш следующий шаг:{" "}
              </Text>
              {next.text.charAt(0).toLowerCase() + next.text.slice(1)}
            </>
          ) : (
            next.text
          )}
        </Text>
        <Group>
          <Button component={Link} to={`/client/applications/${application.id}`} variant={next.isAction ? "filled" : "default"} data-testid="open-current">
            Открыть заявку
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

function Feed() {
  const feed = useQuery({ queryKey: ["feed"], queryFn: () => call(api.GET("/api/v1/feed")) });
  return (
    <Card>
      <Stack gap="md">
        <Title order={3}>Подсказки для вас</Title>
        {feed.isLoading && <LoadingState />}
        {feed.isError && <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />}
        {feed.data?.length === 0 && <Text c={COLORS.textSecondary}>Пока подсказок нет.</Text>}
        {feed.data?.map((item) => (
          <Box key={item.id} p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid="feed-item">
            <Text size="xs" c={COLORS.textSecondary} mb={4}>
              {item.tag}
            </Text>
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
  const items = applications.data?.items ?? [];
  const current = items.find((item) => !item.is_final) ?? null;
  const others = items.filter((item) => item !== current);

  return (
    <Stack gap="lg">
      <Group justify="space-between" wrap="wrap" gap="md" align="flex-end">
        <Stack gap={4}>
          <Title order={1} fz={32}>
            Здравствуйте, {firstName}!
          </Title>
          <Text c={COLORS.textSecondary}>{user?.company?.name}</Text>
        </Stack>
        <Button component={Link} to="/client/products" leftSection={<IconPlus size={18} />} data-testid="get-financing">
          Получить финансирование
        </Button>
      </Group>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Stack gap="lg">
            {applications.isLoading && <LoadingState />}
            {applications.isError && <ErrorState error={applications.error} onRetry={() => void applications.refetch()} />}
            {current && <CurrentApplication application={current} />}
            {applications.data && (
              <Card>
                <Stack gap="md">
                  <Title order={3}>{current ? "Другие заявки" : "Мои заявки"}</Title>
                  {items.length === 0 && (
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
                  {items.length > 0 && others.length === 0 && <Text c={COLORS.textSecondary}>Других заявок нет.</Text>}
                  {others.map((application) => (
                    <ApplicationRow key={application.id} application={application} />
                  ))}
                </Stack>
              </Card>
            )}
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Feed />
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
