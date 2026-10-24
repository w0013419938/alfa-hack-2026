/** Очередь заявок сотрудника: фильтры по статусу, продукту и грейду, пагинация, выделение ручного рассмотрения. */
import { Box, Button, Card, Group, MultiSelect, Pagination, Select, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, call } from "../../api/client";
import { EmptyState, ErrorState, RowsSkeleton } from "../../components/States";
import { gradeColor } from "../../components/bank/grade";
import { Term } from "../../components/Term";
import { COLORS } from "../../theme";
import { dateTime, money, months } from "../../utils/format";
import { useProducts } from "../client/ProductsPage";

const PAGE_SIZE = 15;
const GRADES = ["A", "B", "C", "D", "E"];


export function QueuePage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const products = useProducts();
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => call(api.GET("/api/v1/backoffice/stats")) });

  const statuses = params.getAll("status");
  const product = params.get("product");
  const grade = params.get("grade");
  const [page, setPage] = useState(1);

  const queue = useQuery({
    queryKey: ["queue", statuses, product, grade, page],
    queryFn: () =>
      call(
        api.GET("/api/v1/backoffice/applications", {
          params: { query: { status: statuses, product: product ?? undefined, grade: grade ?? undefined, page, page_size: PAGE_SIZE } },
        }),
      ),
    refetchInterval: 5000, // очередь живая: новые заявки и смены статусов появляются сами
    placeholderData: (previous) => previous,
  });

  function setFilter(key: string, values: string[] | string | null) {
    const next = new URLSearchParams(params);
    next.delete(key);
    (Array.isArray(values) ? values : values ? [values] : []).forEach((value) => next.append(key, value));
    setParams(next, { replace: true });
    setPage(1);
  }

  // Список статусов и их названия для фильтра — из ответа /backoffice/stats (он перечисляет все статусы)
  const statusOptions = (stats.data?.by_status ?? []).map((item) => ({ value: item.status, label: `${item.label} (${item.count})` }));
  const manualCount = stats.data?.manual_review_queue ?? 0;

  return (
    <Stack gap="lg">
      <Group justify="space-between" wrap="wrap">
        <Stack gap={4}>
          <Title order={1}>Очередь заявок</Title>
          <Text c={COLORS.textSecondary} size="lg">
            Красная точка у заявок, по которым нужно ваше решение.
          </Text>
        </Stack>
        <Button
          variant={statuses.length === 1 && statuses[0] === "MANUAL_REVIEW" ? "filled" : "light"}
          onClick={() => setFilter("status", statuses.length === 1 && statuses[0] === "MANUAL_REVIEW" ? [] : ["MANUAL_REVIEW"])}
          data-testid="filter-manual"
        >
          Ждут решения: {manualCount}
        </Button>
      </Group>

      <Card>
        <Stack gap="md">
          <Group gap="md" wrap="wrap" align="flex-end">
            <MultiSelect
              label="Статус"
              placeholder={statuses.length ? undefined : "Все статусы"}
              data={statusOptions}
              value={statuses}
              onChange={(values) => setFilter("status", values)}
              clearable
              w={{ base: "100%", sm: 320 }}
              data-testid="filter-status"
            />
            <Select
              label="Продукт"
              placeholder="Все продукты"
              data={(products.data ?? []).map((item) => ({ value: item.code, label: item.name }))}
              value={product}
              onChange={(value) => setFilter("product", value)}
              clearable
              w={{ base: "100%", sm: 260 }}
            />
            <Select
              label={<Term id="grade">Грейд</Term>}
              placeholder="Любой"
              data={GRADES}
              value={grade}
              onChange={(value) => setFilter("grade", value)}
              clearable
              w={{ base: "100%", sm: 140 }}
            />
          </Group>

          {queue.isLoading && <RowsSkeleton rows={8} height={52} />}
          {queue.isError && <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />}
          {queue.data && queue.data.items.length === 0 && (
            <EmptyState
              title="Заявок не найдено"
              text="Под выбранные фильтры заявок нет."
              action={
                params.toString() ? (
                  <Button variant="default" onClick={() => setParams(new URLSearchParams(), { replace: true })}>
                    Сбросить фильтры
                  </Button>
                ) : undefined
              }
            />
          )}
          {queue.data && queue.data.items.length > 0 && (
            <Table.ScrollContainer minWidth={600}>
              <Table className="clean-table" verticalSpacing="sm" highlightOnHover={false} withRowBorders data-testid="queue-table">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>№</Table.Th>
                    <Table.Th>Компания</Table.Th>
                    <Table.Th visibleFrom="md">Продукт</Table.Th>
                    <Table.Th ta="right">Сумма</Table.Th>
                    <Table.Th ta="right" visibleFrom="lg">Срок</Table.Th>
                    <Table.Th>Статус</Table.Th>
                    <Table.Th>Грейд</Table.Th>
                    <Table.Th visibleFrom="lg">Обновлена</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {queue.data.items.map((item) => (
                    <Table.Tr
                      key={item.id}
                      className="row-clickable"
                      onClick={() => navigate(`/bank/applications/${item.id}`)}
                      // Строку можно открыть и с клавиатуры: Tab до строки, затем Enter
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          navigate(`/bank/applications/${item.id}`);
                        }
                      }}
                      aria-label={`Заявка № ${item.number}, ${item.company_name}, ${item.status_label}`}
                      data-testid="queue-row"
                      data-status={item.status}
                      data-number={item.number}
                    >
                      <Table.Td className="num" fw={600}>
                        {item.number}
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" fw={500}>
                          {item.company_name}
                        </Text>
                        <Text size="xs" c={COLORS.textSecondary} className="num">
                          ИНН {item.company_inn}
                        </Text>
                      </Table.Td>
                      <Table.Td visibleFrom="md">{item.product.name}</Table.Td>
                      <Table.Td ta="right" className="num">
                        {money(item.amount, true)}
                      </Table.Td>
                      <Table.Td ta="right" className="num" visibleFrom="lg">
                        {months(item.term_months)}
                      </Table.Td>
                      <Table.Td>
                        {/* Ждёт решения — красная точка и жирный текст; остальные статусы спокойные */}
                        <Group gap={8} wrap="nowrap" align="baseline">
                          <Box
                            w={8}
                            h={8}
                            style={{ borderRadius: "50%", flexShrink: 0, alignSelf: "center" }}
                            bg={item.status === "MANUAL_REVIEW" ? COLORS.accent : "transparent"}
                            aria-hidden
                          />
                          <Text size="sm" fw={item.status === "MANUAL_REVIEW" ? 600 : 400} c={item.is_final ? COLORS.textSecondary : COLORS.text}>
                            {item.status_label}
                          </Text>
                        </Group>
                      </Table.Td>
                      <Table.Td>
                        {item.grade ? (
                          <Text size="sm" className="num" style={{ whiteSpace: "nowrap" }}>
                            <Text span fw={700} c={gradeColor(item.grade)}>
                              {item.grade}
                            </Text>
                            <Text span c={COLORS.textSecondary}>
                              {" "}
                              {item.score} б.
                            </Text>
                          </Text>
                        ) : (
                          <Text size="sm" c={COLORS.textSecondary}>
                            —
                          </Text>
                        )}
                      </Table.Td>
                      <Table.Td visibleFrom="lg">
                        <Text size="sm" c={COLORS.textSecondary}>
                          {dateTime(item.updated_at)}
                        </Text>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
          {queue.data && queue.data.total > PAGE_SIZE && (
            <Group justify="space-between">
              <Text size="sm" c={COLORS.textSecondary}>
                Всего: {queue.data.total}
              </Text>
              <Pagination total={Math.ceil(queue.data.total / PAGE_SIZE)} value={page} onChange={setPage} />
            </Group>
          )}
        </Stack>
      </Card>
    </Stack>
  );
}
