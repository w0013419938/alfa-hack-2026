/** Имитация подписания: договор (HTML с бэкенда) + подтверждение. Реальной электронной подписи нет. */
import { Alert, Box, Button, Checkbox, Group, Modal, Stack, Text } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, call, type Application, type ApplicationAction } from "../../api/client";
import { COLORS, RADIUS } from "../../theme";
import { ErrorState, LoadingState } from "../States";
import { Term } from "../Term";
import { useClientAction } from "./useClientAction";

type Props = { application: Application; opened: boolean; onClose: () => void; signAction?: ApplicationAction };

export function SigningModal({ application, opened, onClose, signAction }: Props) {
  const [agreed, setAgreed] = useState(false);
  const mutation = useClientAction(application);
  const contract = useQuery({
    queryKey: ["contract", application.id],
    queryFn: () =>
      call(api.GET("/api/v1/applications/{application_id}/contract", { params: { path: { application_id: application.id } }, parseAs: "text" })),
    enabled: opened,
  });

  return (
    <Modal opened={opened} onClose={onClose} title="Подписание кредитного договора" size="xl" radius="lg" centered>
      <Stack>
        <Alert color="violet" radius="lg">
          Это демо: <Term id="signing">подписание</Term> здесь имитируется. Прочитайте договор и подтвердите согласие. После этого банк
          перечислит деньги на счёт компании.
        </Alert>
        {contract.isLoading && <LoadingState text="Готовим договор…" />}
        {contract.isError && <ErrorState error={contract.error} onRetry={() => void contract.refetch()} />}
        {contract.data && (
          <Box style={{ border: `1px solid ${COLORS.border}`, borderRadius: RADIUS.control, overflow: "hidden" }}>
            {/* sandbox: внутри документа не выполняются скрипты */}
            <iframe title="Кредитный договор" srcDoc={contract.data as string} sandbox="" style={{ width: "100%", height: 420, border: 0, background: "#fff" }} />
          </Box>
        )}
        <Checkbox
          checked={agreed}
          onChange={(event) => setAgreed(event.currentTarget.checked)}
          label="Я прочитал(а) договор и согласен(на) с условиями"
          data-testid="sign-agree"
        />
        <Group justify="space-between">
          <Text size="sm" c={COLORS.textSecondary}>
            Нажимая кнопку, вы подписываете договор простой электронной подписью (имитация).
          </Text>
          <Group>
            <Button variant="default" onClick={onClose}>
              Позже
            </Button>
            <Button
              disabled={!agreed || !signAction?.enabled}
              loading={mutation.isPending}
              onClick={() => mutation.mutate({ action: "sign" }, { onSuccess: onClose })}
              data-testid="sign-confirm"
            >
              {signAction?.label ?? "Подписать договор"}
            </Button>
          </Group>
        </Group>
      </Stack>
    </Modal>
  );
}
