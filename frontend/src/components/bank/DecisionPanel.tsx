/**
 * Панель решения сотрудника. Какие решения доступны — строго из available_actions;
 * условия по умолчанию — из suggested_offer; комментарий обязателен (requires_comment из API).
 */
import { Alert, Button, Card, Group, Modal, MultiSelect, NumberInput, SegmentedControl, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, call, errorText, type Schemas } from "../../api/client";
import { useProducts } from "../../pages/client/ProductsPage";
import { COLORS } from "../../theme";
import { useDocumentKinds } from "../application/DocumentsBlock";
import { Term } from "../Term";

type BankApplication = Schemas["BackofficeApplicationOut"];

export function DecisionPanel({ application }: { application: BankApplication }) {
  const queryClient = useQueryClient();
  const products = useProducts();
  const documentKinds = useDocumentKinds();
  const actions = application.available_actions;
  const [action, setAction] = useState<string | null>(actions[0]?.code ?? null);
  const [comment, setComment] = useState("");
  const [terms, setTerms] = useState({
    amount: application.suggested_offer?.amount ?? application.amount ?? 0,
    term_months: application.suggested_offer?.term_months ?? application.term_months ?? 0,
    rate: application.suggested_offer?.rate ?? 0,
  });
  const [fields, setFields] = useState<string[]>([]);
  const [documents, setDocuments] = useState<string[]>([]);
  const [confirming, setConfirming] = useState(false);

  // Если набор доступных действий изменился (заявку решили в другом окне) — выбираем заново
  useEffect(() => {
    if (!actions.some((item) => item.code === action)) setAction(actions[0]?.code ?? null);
  }, [actions, action]);

  const decide = useMutation({
    mutationFn: () => {
      const body: Schemas["EmployeeActionRequest"] = { comment, version: application.version };
      if (action === "approve" || action === "counter_offer") Object.assign(body, terms);
      if (action === "request_info") Object.assign(body, { requested_fields: fields, requested_documents: documents });
      return call(
        api.POST("/api/v1/backoffice/applications/{application_id}/actions/{action}", {
          params: { path: { application_id: application.id, action: action! } },
          body,
        }),
      );
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(["bank-application", application.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["stats"] });
      notifications.show({ color: "lime", title: `Готово: «${actions.find((item) => item.code === action)?.label ?? "Решение"}»`, message: `Клиент увидит новый статус у себя: «${updated.status_label}».`, autoClose: 4000 });
      setComment("");
      setConfirming(false);
    },
    onError: () => setConfirming(false),
  });

  if (actions.length === 0) {
    return (
      <Card>
        <Stack gap="xs">
          <Title order={3}>Решение</Title>
          <Text c={COLORS.textSecondary}>
            Сейчас решение сотрудника не требуется: заявка в статусе «{application.status_label}».
          </Text>
        </Stack>
      </Card>
    );
  }

  const current = actions.find((item) => item.code === action);
  const productInfo = products.data?.find((item) => item.code === application.product.code);
  const commentMissing = Boolean(current?.requires_comment) && comment.trim().length < 3;

  return (
    <Card style={{ outline: `2px solid ${COLORS.accent}` }} data-testid="decision-panel">
      <Stack gap="md">
        <Title order={3}>Ваше решение</Title>
        <SegmentedControl
          orientation="vertical"
          fullWidth
          value={action ?? ""}
          onChange={setAction}
          data={actions.map((item) => ({ value: item.code, label: item.label, disabled: !item.enabled }))}
          data-testid="decision-actions"
        />

        {(action === "approve" || action === "counter_offer") && (
          <Stack gap="xs">
            {application.suggested_offer && (
              <Text size="xs" c={COLORS.textSecondary}>
                По умолчанию стоят запрошенные условия и <Term id="rate">ставка</Term> по грейду {application.suggested_offer.grade_used}.
              </Text>
            )}
            <NumberInput label="Сумма, ₽" value={terms.amount} onChange={(value) => setTerms({ ...terms, amount: Number(value) || 0 })} thousandSeparator=" " min={0}
              description={productInfo ? `лимит продукта: ${productInfo.min_amount.toLocaleString("ru-RU")} – ${productInfo.max_amount.toLocaleString("ru-RU")} ₽` : undefined} />
            <NumberInput label="Срок, мес." value={terms.term_months} onChange={(value) => setTerms({ ...terms, term_months: Number(value) || 0 })} min={1}
              description={productInfo ? `от ${productInfo.min_term_months} до ${productInfo.max_term_months} мес.` : undefined} />
            <NumberInput label={<Term id="rate">Ставка, % годовых</Term>} value={terms.rate} onChange={(value) => setTerms({ ...terms, rate: Number(value) || 0 })} decimalScale={2} step={0.5} min={0} />
          </Stack>
        )}

        {action === "request_info" && (
          <Stack gap="xs">
            <MultiSelect
              label="Что исправить в анкете"
              placeholder="Поля анкеты (необязательно)"
              data={(productInfo?.required_fields ?? []).map((item) => ({ value: item.field, label: item.label }))}
              value={fields}
              onChange={setFields}
            />
            <MultiSelect
              label="Какие документы загрузить"
              placeholder="Документы (необязательно)"
              data={(documentKinds.data ?? []).filter((item) => item.client_can_upload).map((item) => ({ value: item.code, label: item.label }))}
              value={documents}
              onChange={setDocuments}
              data-testid="request-documents"
            />
          </Stack>
        )}

        <Textarea
          label={current?.requires_comment ? "Комментарий для клиента (обязательно)" : "Комментарий для клиента"}
          description="Клиент увидит его в истории заявки"
          value={comment}
          onChange={(event) => setComment(event.currentTarget.value)}
          autosize
          minRows={3}
          maxLength={2000}
          error={decide.isError ? errorText(decide.error) : undefined}
          data-testid="decision-comment"
        />

        <Button
          disabled={!current?.enabled || commentMissing}
          loading={decide.isPending}
          color={action === "reject" ? "gray" : "brand"}
          onClick={() => (current?.confirm_text ? setConfirming(true) : decide.mutate())}
          data-testid="decision-submit"
        >
          {current?.label}
        </Button>
        {commentMissing && (
          <Text size="xs" c={COLORS.textSecondary}>
            Без комментария решение не отправить.
          </Text>
        )}
      </Stack>

      <Modal opened={confirming} onClose={() => setConfirming(false)} title={current?.label} centered radius="lg">
        <Stack>
          <Alert color="violet" radius="lg">
            {current?.confirm_text}
          </Alert>
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirming(false)}>
              Назад
            </Button>
            <Button color="gray" loading={decide.isPending} onClick={() => decide.mutate()} data-testid="decision-confirm">
              {current?.label}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Card>
  );
}
