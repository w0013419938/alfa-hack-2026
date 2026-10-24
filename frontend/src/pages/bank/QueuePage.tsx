/** Очередь заявок сотрудника: фильтры по статусу, продукту и грейду, пагинация, выделение ручного рассмотрения. */
import { Badge, Button, Card, Group, MultiSelect, Pagination, Select, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, call } from "../../api/client";
import { EmptyState, ErrorState, LoadingState } from "../../components/States";
import { Term } from "../../components/Term";
import { COLORS } from "../../theme";
import { dateTime, money, months } from "../../utils/format";
import { useProducts } from "../client/ProductsPage";

const PAGE_SIZE = 15;
const GRADES = ["A", "B", "C", "D", "E"];

// Бейджи в узкой таблице переносят текст, а не обрезают его многоточием
const BADGE_NO_TRUNCATE = { root: { height: "auto", paddingBlock: 2 }, label: { whiteSpace: "normal" as const, overflow: "visible", textOverflow: "clip" } };

export const GRADE_COLOR: Record<string, string> = { A: "lime", B: "lime", C: "yellow", D: "violet", E: "brand" };

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
            Заявки на ручном рассмотрении выделены цветом: по ним нужно ваше решение.
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

          {queue.isLoading && <LoadingState />}
          {queue.isError && <ErrorState error={queue.error} onRetry={() => void queue.refetch()} />}
          {queue.data && queue.data.items.length === 0 && <EmptyState title="Заявок не найдено" text="Попробуйте убрать часть фильтров." />}
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
                      className={`row-clickable ${item.status === "MANUAL_REVIEW" ? "row-highlight" : ""}`}
                      onClick={() => navigate(`/bank/applications/${item.id}`)}
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
                        <Badge variant="light" color={item.status === "MANUAL_REVIEW" ? "brand" : "gray"} styles={BADGE_NO_TRUNCATE}>
                          {item.status_label}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {item.grade ? (
                          <Badge color={GRADE_COLOR[item.grade] ?? "gray"} variant="light" styles={BADGE_NO_TRUNCATE}>
                            {item.grade}, {item.score} б.
                          </Badge>
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
