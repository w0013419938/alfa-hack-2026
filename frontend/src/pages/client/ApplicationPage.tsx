/**
 * Страница заявки — главный экран демо.
 * Пока заявка не в финальном статусе, она опрашивается каждые 3 секунды: статус, шкала этапов и история
 * обновляются на глазах, без перезагрузки страницы.
 */
import { Alert, Anchor, Box, Card, Grid, Group, SimpleGrid, Stack, Text, Title } from "@mantine/core";
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
import { MoneyFigure } from "../../components/MoneyFigure";
import { COLORS } from "../../theme";
import { money, months, percent } from "../../utils/format";

export const POLL_INTERVAL_MS = 3000;

export function useApplication(id: string) {
  return useQuery({
    queryKey: ["application", id],
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}", { params: { path: { application_id: id } } })),
    // Опрашиваем, пока процесс не закончился; финальный статус больше не меняется
    refetchInterval: (query) => (query.state.data && !query.state.data.is_final ? POLL_INTERVAL_MS : false),
  });
}

/** Этап, над которым сейчас работает банк (state = current в progress), — для индикатора «Банк работает» */
function workingStep(application: Application) {
  if (application.is_final) return null;
  return application.progress.find((item) => item.state === "current") ?? null;
}

/** Все этапы пройдены — процесс завершён успешно (кредит выдан) */
function allStepsDone(application: Application): boolean {
  return application.progress.length > 0 && application.progress.every((item) => item.state === "done");
}

/** «Банк работает»: бегущая полоса и название этапа из progress, чтобы ожидание не выглядело зависанием */
function BankWorking({ label }: { label: string }) {
  return (
    <Group gap="sm" wrap="nowrap" role="status" data-testid="bank-working">
      <Box className="working-track" w={96} style={{ flexShrink: 0 }} />
      <Text size="sm" fw={500}>
        Банк работает: {label.charAt(0).toLowerCase() + label.slice(1)}
      </Text>
      <Text size="sm" c={COLORS.textSecondary} visibleFrom="sm">
        Страница обновится сама
      </Text>
    </Group>
  );
}

/** Знак завершения: салатовый круг, галочка прорисовывается один раз */
function DoneMark() {
  return (
    <Box w={64} h={64} bg={COLORS.positive} style={{ borderRadius: "50%", display: "grid", placeItems: "center", flexShrink: 0 }} aria-hidden>
      <svg width="30" height="30" viewBox="0 0 30 30" fill="none">
        <path className="check-draw" d="M7 15.5l5.5 5.5L23.5 9" stroke={COLORS.text} strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </Box>
  );
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
        <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xs">
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
  const working = workingStep(application);
  const finished = allStepsDone(application);

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/client" c={COLORS.textSecondary} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={16} /> Мои заявки
        </Group>
      </Anchor>

      <Card bg={finished ? COLORS.positiveSoft : undefined} data-testid="status-card">
        <Stack gap="md">
          <Text c={COLORS.textSecondary}>
            Заявка № {application.number}: {application.product.name.toLowerCase()} на {money(application.amount)}
          </Text>
          <Group gap="lg" wrap="nowrap" align="center">
            {finished && <DoneMark />}
            <Title order={1} data-testid="status-label" data-status={application.status} aria-live="polite">
              {application.status_label}
            </Title>
          </Group>
          <Text size="lg" maw={760} data-testid="status-description">
            {application.status_description}
          </Text>
          {finished && application.offer && (
            <Group gap={48} wrap="wrap" data-testid="issued-summary">
              <Stack gap={2}>
                <Text size="sm" c={COLORS.textSecondary}>
                  Сумма кредита
                </Text>
                <MoneyFigure value={application.offer.amount} fontSize={32} />
              </Stack>
              <Stack gap={2}>
                <Text size="sm" c={COLORS.textSecondary}>
                  <Term id="monthly_payment">Платёж в месяц</Term>
                </Text>
                <MoneyFigure value={application.offer.monthly_payment} fontSize={32} />
              </Stack>
              <Stack gap={2}>
                <Text size="sm" c={COLORS.textSecondary}>
                  <Term id="term">Срок</Term>
                </Text>
                <Text fz={32} fw={600} lh={1.05} className="num">
                  {months(application.offer.term_months)}
                </Text>
              </Stack>
              <Stack gap={2}>
                <Text size="sm" c={COLORS.textSecondary}>
                  <Term id="rate">Ставка</Term>
                </Text>
                <Text fz={32} fw={600} lh={1.05} className="num">
                  {percent(application.offer.rate)}
                </Text>
              </Stack>
            </Group>
          )}
          {latestBankMessage(application) && (
            <Alert color={application.status === "REJECTED" ? "gray" : "violet"} radius="lg" title="Сообщение банка" maw={760} data-testid="bank-message">
              {latestBankMessage(application)}
            </Alert>
          )}
          {working && <BankWorking label={working.label} />}
          {application.available_actions.length > 0 && (
            <Box mt="xs">
              <ActionBar application={application} />
            </Box>
          )}
        </Stack>
      </Card>

      <Card>
        <ProgressSteps steps={application.progress} />
      </Card>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 7 }}>
          <Stack gap="lg">
            <InfoRequestPanel application={application} />
            {/* После выдачи условия уже показаны в итоге сверху — второй раз их не повторяем */}
            {!finished && <OfferCard application={application} />}
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
