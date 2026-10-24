/**
 * Карточка заявки для сотрудника: анкета, компания, проверки ЕГРЮЛ и БКИ, скоринг с вкладом факторов,
 * итог автоматического решения, история и панель решения. Обновляется каждые 3 секунды, пока заявка в работе.
 */
import { Accordion, Anchor, Badge, Box, Button, Card, Code, Grid, Group, List, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconArrowLeft, IconDownload } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { api, call, downloadFile, errorText, type Schemas } from "../../api/client";
import { DecisionPanel } from "../../components/bank/DecisionPanel";
import { ScoringBars } from "../../components/bank/ScoringBars";
import { ProgressSteps } from "../../components/ProgressSteps";
import { ErrorState, LoadingState } from "../../components/States";
import { Term } from "../../components/Term";
import { COLORS, RADIUS } from "../../theme";
import { date, dateTime, money, months, percent } from "../../utils/format";

type BankApplication = Schemas["BackofficeApplicationOut"];

function Field({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <Group justify="space-between" wrap="nowrap" py={5} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
      <Text size="sm" c={COLORS.textSecondary}>
        {label}
      </Text>
      <Text size="sm" fw={500} ta="right" className="num">
        {value ?? "—"}
      </Text>
    </Group>
  );
}

function Checks({ application }: { application: BankApplication }) {
  // Последние проверки каждого типа (после повторной обработки их может быть несколько)
  const latest = new Map<string, Schemas["CheckOut"]>();
  application.checks.forEach((check) => !latest.has(check.check_type) && latest.set(check.check_type, check));
  if (latest.size === 0) return <Text c={COLORS.textSecondary}>Проверки ещё не проводились.</Text>;
  return (
    <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
      {[...latest.values()].map((check) => (
        <Box key={check.id} p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid={`check-${check.check_type}`}>
          <Group justify="space-between" mb="xs" wrap="nowrap">
            <Text fw={600}>{check.check_type === "bki" ? <Term id="bki">{check.check_type_label}</Term> : <Term id="egrul">{check.check_type_label}</Term>}</Text>
            <Badge color={check.status === "ok" ? "lime" : "brand"} variant="light" c={check.status === "ok" ? COLORS.positiveText : undefined}>
              {check.status_label}
            </Badge>
          </Group>
          <List size="sm" spacing={2}>
            {check.summary.map((line) => (
              <List.Item key={line}>{line}</List.Item>
            ))}
          </List>
          <Text size="xs" c={COLORS.textSecondary} mt="xs">
            Попыток: {check.attempts} · {check.duration_ms} мс · {dateTime(check.created_at)}
          </Text>
        </Box>
      ))}
    </SimpleGrid>
  );
}

export function BankApplicationPage() {
  const { id = "" } = useParams();
  const query = useQuery({
    queryKey: ["bank-application", id],
    queryFn: () => call(api.GET("/api/v1/backoffice/applications/{application_id}", { params: { path: { application_id: id } } })),
    refetchInterval: (state) => (state.state.data && !state.state.data.is_final ? 3000 : false),
  });

  if (query.isLoading) return <LoadingState text="Загружаем карточку заявки…" />;
  if (query.isError || !query.data) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  const application = query.data;

  return (
    <Stack gap="lg">
      <Anchor component={Link} to="/bank" c={COLORS.textSecondary} size="sm">
        <Group gap={4}>
          <IconArrowLeft size={16} /> Очередь заявок
        </Group>
      </Anchor>

      <Card>
        <Stack gap="sm">
          <Group justify="space-between" wrap="wrap">
            <Text c={COLORS.textSecondary}>
              Заявка № {application.number} · {application.company.name} · {application.product.name}
            </Text>
            {application.scoring && (
              <Badge size="lg" variant="light" color="gray">
                <Term id="grade">Грейд</Term> {application.scoring.grade} · {application.scoring.total_score} баллов
              </Badge>
            )}
          </Group>
          <Title order={1} data-testid="status-label" data-status={application.status}>
            {application.status_label}
          </Title>
          <Text size="lg">{application.status_description}</Text>
        </Stack>
      </Card>

      <Card>
        <ProgressSteps steps={application.progress} />
      </Card>

      <Grid gap="lg">
        <Grid.Col span={{ base: 12, md: 8 }} order={{ base: 2, md: 1 }}>
          <Stack gap="lg">
            {application.decision && (
              <Card>
                <Stack gap="xs">
                  <Title order={3}>Автоматическое решение</Title>
                  <Text fw={600}>{application.decision.outcome_label}</Text>
                  <List size="sm">
                    {application.decision.reasons.map((reason) => (
                      <List.Item key={reason.code}>{reason.text}</List.Item>
                    ))}
                  </List>
                  {application.suggested_offer && (
                    <Text size="sm" c={COLORS.textSecondary} className="num">
                      Расчёт по запрошенным условиям: {money(application.suggested_offer.amount)} на {months(application.suggested_offer.term_months)} под{" "}
                      {percent(application.suggested_offer.rate)} — платёж {money(application.suggested_offer.monthly_payment)} в месяц.
                    </Text>
                  )}
                </Stack>
              </Card>
            )}

            <Card>
              <Stack gap="md">
                <Title order={3}>
                  <Term id="scoring">Скоринг</Term>
                </Title>
                {application.scoring ? <ScoringBars scoring={application.scoring} /> : <Text c={COLORS.textSecondary}>Скоринг ещё не проводился.</Text>}
              </Stack>
            </Card>

            <Card>
              <Stack gap="md">
                <Title order={3}>Проверки во внешних источниках</Title>
                <Checks application={application} />
              </Stack>
            </Card>

            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
              <Card>
                <Stack gap={4}>
                  <Title order={3} mb="xs">
                    Анкета
                  </Title>
                  <Field label="Сумма" value={money(application.amount)} />
                  <Field label="Срок" value={months(application.term_months)} />
                  <Field label="Цель" value={application.purpose_label} />
                  {application.purpose_comment && <Field label="Комментарий" value={application.purpose_comment} />}
                  {application.collateral_description && <Field label={<Term id="collateral">Залог</Term>} value={application.collateral_description} />}
                  <Field label={<Term id="revenue">Выручка в месяц</Term>} value={money(application.monthly_revenue)} />
                  <Field label={<Term id="expenses">Расходы в месяц</Term>} value={money(application.monthly_expenses)} />
                  <Field label={<Term id="current_payments">Платежи по кредитам</Term>} value={money(application.current_loan_payments)} />
                  <Field label="Заявитель" value={`${application.author.full_name}${application.author.position_label ? `, ${application.author.position_label}` : ""}`} />
                </Stack>
              </Card>
              <Card>
                <Stack gap={4}>
                  <Title order={3} mb="xs">
                    Компания
                  </Title>
                  <Field label="Название" value={application.company.name} />
                  <Field label={<Term id="inn">ИНН</Term>} value={application.company.inn} />
                  <Field label={<Term id="ogrn">ОГРН</Term>} value={application.company.ogrn} />
                  <Field label={<Term id="okved">ОКВЭД</Term>} value={`${application.company.okved} · ${application.company.industry}`} />
                  <Field label="Регион" value={application.company.region} />
                  <Field label="Регистрация" value={date(application.company.registration_date)} />
                  <Field label="Выручка за год" value={application.company.annual_revenue === null ? "нет отчётности" : money(application.company.annual_revenue)} />
                  <Field label="Сотрудников" value={application.company.employees_count} />
                </Stack>
              </Card>
            </SimpleGrid>

            {application.documents.length > 0 && (
              <Card>
                <Stack gap="sm">
                  <Title order={3}>Документы</Title>
                  {application.documents.map((document) => (
                    <Group key={document.id} justify="space-between">
                      <Text size="sm">
                        <b>{document.kind_label}</b> · {document.filename} · {document.uploaded_by}
                      </Text>
                      <Button
                        variant="subtle"
                        size="xs"
                        leftSection={<IconDownload size={16} />}
                        onClick={() => downloadFile(document.download_url, document.filename).catch((error) => notifications.show({ color: "brand", message: errorText(error) }))}
                      >
                        Скачать
                      </Button>
                    </Group>
                  ))}
                </Stack>
              </Card>
            )}

            <Card>
              <Stack gap="md">
                <Title order={3}>История</Title>
                <Accordion variant="separated" radius="lg" multiple>
                  {[...application.events].reverse().map((event) => (
                    <Accordion.Item key={event.id} value={event.id}>
                      <Accordion.Control>
                        <Group justify="space-between" wrap="nowrap" pr="sm">
                          <Stack gap={0}>
                            <Text fw={600} size="sm">
                              {event.title}
                            </Text>
                            <Text size="xs" c={COLORS.textSecondary}>
                              {event.actor}
                              {event.actor_name ? ` · ${event.actor_name}` : ""} · {event.from_status ?? "—"} → {event.to_status}
                            </Text>
                          </Stack>
                          <Text size="xs" c={COLORS.textSecondary} style={{ whiteSpace: "nowrap" }}>
                            {dateTime(event.at)}
                          </Text>
                        </Group>
                      </Accordion.Control>
                      <Accordion.Panel>
                        {event.comment && (
                          <Text size="sm" mb="xs">
                            {event.comment}
                          </Text>
                        )}
                        <Code block>{JSON.stringify(event.payload, null, 2)}</Code>
                      </Accordion.Panel>
                    </Accordion.Item>
                  ))}
                </Accordion>
              </Stack>
            </Card>
          </Stack>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 4 }} order={{ base: 1, md: 2 }}>
          <Box style={{ position: "sticky", top: 16 }}>
            <DecisionPanel key={`${application.id}-${application.status}`} application={application} />
          </Box>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
