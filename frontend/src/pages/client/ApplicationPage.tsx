/**
 * Страница заявки — главный экран демо.
 * Пока заявка не в финальном статусе, она опрашивается каждые 3 секунды: статус, шкала этапов и история
 * обновляются на глазах, без перезагрузки страницы.
 */
import { Alert, Anchor, Badge, Box, Card, Grid, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { IconArrowLeft } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api, call, type Application } from "../../api/client";
import { ActionBar } from "../../components/application/ActionBar";
import { DocumentsBlock } from "../../components/application/DocumentsBlock";
import { InfoRequestPanel } from "../../components/application/InfoRequestPanel";
import { OfferCard } from "../../components/application/OfferCard";
import { ProgressSteps } from "../../components/ProgressSteps";
import { ErrorState, LoadingState } from "../../components/States";
import { Term } from "../../components/Term";
import { Timeline } from "../../components/Timeline";
import { COLORS } from "../../theme";
import { money, months } from "../../utils/format";

export const POLL_INTERVAL_MS = 3000;

export function useApplication(id: string) {
  return useQuery({
    queryKey: ["application", id],
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}", { params: { path: { application_id: id } } })),
    // Опрашиваем, пока процесс не закончился; финальный статус больше не меняется
    refetchInterval: (query) => (query.state.data && !query.state.data.is_final ? POLL_INTERVAL_MS : false),
  });
}

/** Состояние текущего этапа (из progress) — для цвета плашки статуса */
function currentState(application: Application): { state: string; label: string } | null {
  const step = application.progress.find((item) => item.state !== "done" && item.state !== "upcoming");
  if (step) return { state: step.state, label: step.state_label };
  return application.is_final ? { state: "done", label: "Готово" } : null;
}

/**
 * Последнее пояснение банка, которое важно показать сразу под статусом: причина отказа или комментарий специалиста.
 * Для остальных статусов пояснения уже есть в отдельных блоках (предложение, запрос уточнений).
 */
function latestBankMessage(application: Application): string | null {
  if (application.status !== "REJECTED" && application.status !== "MANUAL_REVIEW") return null;
  const last = application.timeline[application.timeline.length - 1];
  return last?.status === application.status ? (last.comment ?? null) : null;
}

const STATE_COLOR: Record<string, string> = { current: "brand", action: "violet", stopped: "gray", done: "lime" };

function ApplicationDetails({ application }: { application: Application }) {
  const rows: [React.ReactNode, string][] = [
    ["Продукт", application.product.name],
    ["Сумма", money(application.amount)],
    [<Term id="term">Срок</Term>, months(application.term_months)],
    ["Цель", application.purpose_label ?? "—"],
    [<Term id="revenue">Выручка в месяц</Term>, money(application.monthly_revenue)],
    [<Term id="expenses">Расходы в месяц</Term>, money(application.monthly_expenses)],
    [<Term id="current_payments">Платежи по кредитам</Term>, money(application.current_loan_payments)],
  ];
  if (application.purpose_comment) rows.push(["Комментарий к цели", application.purpose_comment]);
  if (application.collateral_description) rows.push([<Term id="collateral">Залог</Term>, application.collateral_description]);

  return (
    <Card>
      <Stack gap="sm">
        <Title order={3}>Ваша заявка</Title>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="xs">
          {rows.map(([label, value], index) => (
            <Group key={index} justify="space-between" wrap="nowrap" py={4} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
              <Text c={COLORS.textSecondary} size="sm">
                {label}
              </Text>
              <Text size="sm" fw={500} ta="right" className="num">
                {value}
              </Text>
            </Group>
          ))}
        </SimpleGrid>
      </Stack>
    </Card>
  );
}

export function ApplicationPage() {
  const { id = "" } = useParams();
  const query = useApplication(id);

  if (query.isLoading) return <LoadingState text="Загружаем заявку…" />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;

  const application = query.data;
  const state = currentState(application);

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/client" c={COLORS.textSecondary} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={16} /> Мои заявки
        </Group>
      </Anchor>

      <Card>
        <Stack gap="md">
          <Group justify="space-between" align="flex-start" wrap="wrap">
            <Text c={COLORS.textSecondary}>
              Заявка № {application.number} · {application.product.name} · {money(application.amount)}
            </Text>
            {state && (
              <Badge size="lg" color={STATE_COLOR[state.state] ?? "gray"} variant="light" c={state.state === "done" ? COLORS.positiveText : undefined} data-testid="state-badge">
                {state.label}
              </Badge>
            )}
          </Group>
          <Title order={1} data-testid="status-label" data-status={application.status}>
            {application.status_label}
          </Title>
          <Text size="lg" maw={760} data-testid="status-description">
            {application.status_description}
          </Text>
          {latestBankMessage(application) && (
            <Alert color={application.status === "REJECTED" ? "gray" : "violet"} radius="lg" title="Сообщение банка" maw={760} data-testid="bank-message">
              {latestBankMessage(application)}
            </Alert>
          )}
          {!application.is_final && (
            <Text size="xs" c={COLORS.textSecondary}>
              Страница обновляется сама каждые 3 секунды
            </Text>
          )}
          <Box mt="xs">
            <ActionBar application={application} />
          </Box>
        </Stack>
      </Card>

      <Card>
        <ProgressSteps steps={application.progress} />
      </Card>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Stack gap="lg">
            <InfoRequestPanel application={application} />
            <OfferCard application={application} />
            <ApplicationDetails application={application} />
            <DocumentsBlock application={application} />
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 5 }}>
          <Card>
            <Stack gap="md">
              <Title order={3}>История заявки</Title>
              <Timeline items={application.timeline} />
            </Stack>
          </Card>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
