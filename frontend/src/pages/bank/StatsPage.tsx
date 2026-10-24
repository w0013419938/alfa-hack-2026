/** Статистика из GET /backoffice/stats. */
import { Box, Card, SimpleGrid, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { api, call } from "../../api/client";
import { ErrorState, LoadingState } from "../../components/States";
import { COLORS } from "../../theme";

function Metric({ label, value, hint, accent }: { label: string; value: string | number; hint?: string; accent?: boolean }) {
  return (
    <Card>
      <Stack gap={4}>
        <Text c={COLORS.textSecondary}>{label}</Text>
        <Text fz={40} fw={700} c={accent ? COLORS.accent : COLORS.text} className="num" lh={1.1}>
          {value}
        </Text>
        {hint && (
          <Text size="sm" c={COLORS.textSecondary}>
            {hint}
          </Text>
        )}
      </Stack>
    </Card>
  );
}

export function StatsPage() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: () => call(api.GET("/api/v1/backoffice/stats")), refetchInterval: 10_000 });
  if (stats.isLoading) return <LoadingState />;
  if (stats.isError || !stats.data) return <ErrorState error={stats.error} onRetry={() => void stats.refetch()} />;
  const data = stats.data;
  const maxCount = Math.max(1, ...data.by_status.map((item) => item.count));

  return (
    <Stack gap="lg">
      <Title order={1}>Статистика</Title>
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="lg">
        <Metric label="Всего заявок" value={data.total} />
        <Metric label="Ждут решения специалиста" value={data.manual_review_queue} accent />
        <Metric label="Доля автоодобрений" value={data.auto_approval_rate_text} hint={`${data.auto_approved_count} из ${data.decided_count} рассмотренных`} />
        <Metric label="Среднее время до решения" value={data.average_processing_text ?? "—"} hint="от отправки заявки до решения банка" />
      </SimpleGrid>
      <Card>
        <Stack gap="md">
          <Title order={3}>Заявки по статусам</Title>
          <Table className="clean-table" verticalSpacing="xs">
            <Table.Tbody>
              {data.by_status.map((item) => (
                <Table.Tr key={item.status}>
                  <Table.Td w="35%">{item.label}</Table.Td>
                  <Table.Td>
                    <Box h={10} w={`${(item.count / maxCount) * 100}%`} miw={item.count ? 6 : 0} bg={item.status === "MANUAL_REVIEW" ? COLORS.accent : "#C9CBD2"} style={{ borderRadius: 6 }} />
                  </Table.Td>
                  <Table.Td ta="right" className="num" w={60} fw={600}>
                    {item.count}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Stack>
      </Card>
    </Stack>
  );
}
