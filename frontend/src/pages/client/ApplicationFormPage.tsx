/**
 * Анкета заявки по шагам: параметры кредита → о компании → финансовые показатели → проверка и отправка.
 * Черновик сохраняется на сервере при переходе между шагами (POST, затем PATCH с версией).
 * Здесь только простые проверки заполненности и диапазонов продукта — окончательно анкету проверяет бэкенд.
 */
import { Alert, Box, Button, Card, Group, NumberInput, Select, SimpleGrid, Stack, Stepper, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api, call, errorText, type Application, type Schemas } from "../../api/client";
import { NumberBadge } from "../../components/NumberedCard";
import { Checklist } from "../../components/Checklist";
import { ErrorState, LoadingState } from "../../components/States";
import { Term } from "../../components/Term";
import { COLORS, RADIUS } from "../../theme";
import { date, money, months, monthsUpTo } from "../../utils/format";
import { useProducts, usePurposes } from "./ProductsPage";

type Form = {
  product_code: string;
  amount: number | "";
  term_months: number | "";
  purpose_code: string | null;
  purpose_comment: string;
  collateral_description: string;
  monthly_revenue: number | "";
  monthly_expenses: number | "";
  current_loan_payments: number | "";
};

const STEPS = ["Параметры кредита", "О компании", "Финансовые показатели", "Проверка и отправка"];

function numberOrNull(value: number | ""): number | null {
  return value === "" ? null : value;
}

function toBody(form: Form) {
  return {
    product_code: form.product_code,
    amount: numberOrNull(form.amount),
    term_months: numberOrNull(form.term_months),
    purpose_code: form.purpose_code,
    purpose_comment: form.purpose_comment || null,
    collateral_description: form.collateral_description || null,
    monthly_revenue: numberOrNull(form.monthly_revenue),
    monthly_expenses: numberOrNull(form.monthly_expenses),
    current_loan_payments: numberOrNull(form.current_loan_payments),
  };
}

function fromApplication(application: Application): Form {
  return {
    product_code: application.product.code,
    amount: application.amount ?? "",
    term_months: application.term_months ?? "",
    purpose_code: application.purpose_code,
    purpose_comment: application.purpose_comment ?? "",
    collateral_description: application.collateral_description ?? "",
    monthly_revenue: application.monthly_revenue ?? "",
    monthly_expenses: application.monthly_expenses ?? "",
    current_loan_payments: application.current_loan_payments ?? "",
  };
}

/** Что написать под заголовком каждого шага. Тексты по материалам участника 1 */
const STEP_HINTS = [
  "Выберите продукт, сумму и срок. Платёж посчитаем сразу.",
  "Эти данные мы взяли из профиля компании, вводить их не нужно. Проверьте, всё ли верно.",
  "Нужны, чтобы подобрать посильный платёж. Цифры можно указать примерно, за обычный месяц, без сезонных пиков.",
  "Проверьте данные. После отправки банк проверит заявку, обычно меньше минуты.",
];

/** Простые проверки шага. Сообщения — понятным языком, диапазоны — из данных продукта (API). */
function validateStep(step: number, form: Form, product: Schemas["ProductOut"] | undefined, purposeNeedsComment: boolean): Record<string, string> {
  const errors: Record<string, string> = {};
  if (step === 0) {
    if (!form.product_code) errors.product_code = "Выберите продукт";
    if (form.amount === "" || form.amount <= 0) errors.amount = "Укажите сумму";
    else if (product && (form.amount < product.min_amount || form.amount > product.max_amount))
      errors.amount = `Для этого продукта доступно от ${money(product.min_amount, true)} до ${money(product.max_amount, true)}`;
    if (form.term_months === "" || form.term_months <= 0) errors.term_months = "Укажите срок";
    else if (product && (form.term_months < product.min_term_months || form.term_months > product.max_term_months))
      errors.term_months = `Выберите срок от ${product.min_term_months} до ${monthsUpTo(product.max_term_months)}`;
    if (!form.purpose_code) errors.purpose_code = "Выберите цель кредита";
    if (purposeNeedsComment && !form.purpose_comment.trim()) errors.purpose_comment = "Опишите, на что нужны деньги";
    if (product?.requires_collateral && !form.collateral_description.trim()) errors.collateral_description = "Опишите, что вы готовы предложить в залог";
  }
  if (step === 2) {
    if (form.monthly_revenue === "" || form.monthly_revenue <= 0) errors.monthly_revenue = "Укажите выручку в месяц";
    if (form.monthly_expenses === "") errors.monthly_expenses = "Укажите расходы в месяц (0, если расходов нет)";
    if (form.current_loan_payments === "") errors.current_loan_payments = "Укажите платежи по другим кредитам в месяц (0, если кредитов нет)";
  }
  return errors;
}

function SummaryRow({ label, value }: { label: ReactNode; value: ReactNode }) {
  return (
    <Group justify="space-between" wrap="nowrap" py={6} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
      <Text c={COLORS.textSecondary} size="sm">
        {label}
      </Text>
      <Text size="sm" fw={500} ta="right" className="num">
        {value || "—"}
      </Text>
    </Group>
  );
}

export function ApplicationFormPage() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const products = useProducts();
  const purposes = usePurposes();
  const company = useQuery({ queryKey: ["company"], queryFn: () => call(api.GET("/api/v1/company")), staleTime: Infinity });
  const existing = useQuery({
    queryKey: ["application", id],
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}", { params: { path: { application_id: id! } } })),
    enabled: Boolean(id),
  });

  const [step, setStep] = useState(Number(params.get("step") ?? 0));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [form, setForm] = useState<Form>({
    product_code: params.get("product") ?? "",
    amount: params.get("amount") ? Number(params.get("amount")) : "",
    term_months: params.get("term") ? Number(params.get("term")) : "",
    purpose_code: params.get("purpose"),
    purpose_comment: "",
    collateral_description: "",
    monthly_revenue: "",
    monthly_expenses: "",
    current_loan_payments: "",
  });
  const [loadedId, setLoadedId] = useState<string | null>(null);

  // Черновик с сервера подставляем в форму один раз
  useEffect(() => {
    if (existing.data && loadedId !== existing.data.id) {
      setForm(fromApplication(existing.data));
      setLoadedId(existing.data.id);
    }
  }, [existing.data, loadedId]);

  const product = products.data?.find((item) => item.code === form.product_code);

  // Если продукту подходит ровно одна цель, а цель не выбрана — подставляем её, чтобы не спрашивать очевидное
  useEffect(() => {
    if (product && !form.purpose_code && product.purposes.length === 1) {
      setForm((current) => ({ ...current, purpose_code: product.purposes[0].code }));
    }
  }, [product, form.purpose_code]);
  const purposeOptions = (purposes.data ?? []).filter((item) => !product || product.purposes.some((purpose) => purpose.code === item.code));
  const selectedPurpose = purposes.data?.find((item) => item.code === form.purpose_code);
  const application = existing.data;

  const save = useMutation({
    mutationFn: async () => {
      if (!application) return call(api.POST("/api/v1/applications", { body: toBody(form) }));
      return call(
        api.PATCH("/api/v1/applications/{application_id}", {
          params: { path: { application_id: application.id } },
          body: { ...toBody(form), version: application.version },
        }),
      );
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(["application", saved.id], saved);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  const submit = useMutation({
    mutationFn: (saved: Application) =>
      call(
        api.POST("/api/v1/applications/{application_id}/actions/{action}", {
          params: { path: { application_id: saved.id, action: "submit" } },
          body: { version: saved.version },
        }),
      ),
    onSuccess: (submitted) => {
      queryClient.setQueryData(["application", submitted.id], submitted);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      navigate(`/client/applications/${submitted.id}`);
    },
  });

  if (products.isLoading || purposes.isLoading || company.isLoading || (id && existing.isLoading)) return <LoadingState />;
  const loadError = products.error ?? purposes.error ?? company.error ?? existing.error;
  if (loadError) return <ErrorState error={loadError} />;

  const canEdit = !application || application.available_actions.some((action) => action.code === "edit" && action.enabled);
  if (!canEdit && application) {
    return (
      <Card>
        <Stack>
          <Title order={2}>Анкету сейчас менять нельзя</Title>
          <Text>
            Заявка в статусе «{application.status_label}». {application.status_description}
          </Text>
          <Group>
            <Button component={Link} to={`/client/applications/${application.id}`}>
              К заявке
            </Button>
          </Group>
        </Stack>
      </Card>
    );
  }

  const isNeedsInfo = application?.status === "NEEDS_INFO";
  const submitAction = application?.available_actions.find((action) => action.code === "submit");

  function set<K extends keyof Form>(key: K, value: Form[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: "" }));
  }

  async function next() {
    const stepErrors = validateStep(step, form, product, Boolean(selectedPurpose?.requires_comment));
    setErrors(stepErrors);
    if (Object.values(stepErrors).some(Boolean)) return;
    // Сохраняем черновик на сервере перед переходом дальше
    if (step === 0 || step === 2) {
      try {
        const saved = await save.mutateAsync();
        if (!application) navigate(`/client/applications/${saved.id}/edit?step=${step + 1}`, { replace: true });
      } catch {
        return; // ошибку показывает блок ниже
      }
    }
    setStep(step + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={1}>{isNeedsInfo ? "Уточнение анкеты" : "Заявка на кредит"}</Title>
        <Text c={COLORS.textSecondary} size="lg">
          {application ? `Заявка № ${application.number}. Черновик сохраняется сам, когда вы переходите к следующему шагу` : "Четыре коротких шага. Черновик сохраняется, можно вернуться позже."}
        </Text>
      </Stack>

      {isNeedsInfo && application?.info_request && (
        <Alert color="violet" radius="lg" title="Банк просит уточнить">
          {application.info_request.comment}
        </Alert>
      )}

      <Card>
        <Stepper
          active={step}
          onStepClick={(target) => target < step && setStep(target)}
          size="sm"
          color="brand"
          allowNextStepsSelect={false}
          className="form-stepper"
          completedIcon={<IconCheck size={16} stroke={3} />}
        >
          {STEPS.map((label) => (
            <Stepper.Step key={label} label={label} />
          ))}
        </Stepper>
      </Card>

      <Card>
        <Stack gap="lg">
          <Group gap="md">
            <NumberBadge number={step + 1} />
            <Title order={2}>{STEPS[step]}</Title>
          </Group>
          <Text c={COLORS.textSecondary} mt={-12}>
            {STEP_HINTS[step]}
          </Text>
          {step === 0 && !isNeedsInfo && <Checklist withCollateral={Boolean(product?.requires_collateral)} />}

          {step === 0 && (
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              <Select
                label="Продукт"
                data={(products.data ?? []).map((item) => ({ value: item.code, label: `${item.name}, ${item.rate_text}` }))}
                value={form.product_code || null}
                onChange={(value) => set("product_code", value ?? "")}
                error={errors.product_code}
                description={product?.suitable_for ?? "Выберите то, что подходит под вашу задачу. У каждого продукта есть короткое описание"}
                data-testid="form-product"
              />
              <Select
                label="Цель кредита"
                data={purposeOptions.map((item) => ({ value: item.code, label: item.label }))}
                value={form.purpose_code}
                onChange={(value) => set("purpose_code", value)}
                error={errors.purpose_code}
                description="Список целей зависит от продукта"
                data-testid="form-purpose"
              />
              <NumberInput
                label="Сумма кредита, ₽"
                value={form.amount}
                onChange={(value) => set("amount", value === "" ? "" : Number(value))}
                thousandSeparator=" "
                min={0}
                step={50_000}
                error={errors.amount}
                description={product ? `От ${money(product.min_amount, true)} до ${money(product.max_amount, true)} для выбранного продукта` : undefined}
                data-testid="form-amount"
              />
              <NumberInput
                label={<Term id="term">Срок, месяцев</Term>}
                value={form.term_months}
                onChange={(value) => set("term_months", value === "" ? "" : Number(value))}
                min={1}
                error={errors.term_months}
                description={product ? `От ${product.min_term_months} до ${monthsUpTo(product.max_term_months)}` : undefined}
                data-testid="form-term"
              />
              {selectedPurpose?.requires_comment && (
                <Textarea
                  label="На что нужны деньги"
                  value={form.purpose_comment}
                  onChange={(event) => set("purpose_comment", event.currentTarget.value)}
                  error={errors.purpose_comment}
                  maxLength={1000}
                  autosize
                  minRows={2}
                />
              )}
              {product?.requires_collateral && (
                <Textarea
                  label={<Term id="collateral">Что предлагаете в залог</Term>}
                  placeholder="Например: офисное помещение 80 м², г. Москва"
                  value={form.collateral_description}
                  onChange={(event) => set("collateral_description", event.currentTarget.value)}
                  error={errors.collateral_description}
                  maxLength={1000}
                  autosize
                  minRows={2}
                />
              )}
            </SimpleGrid>
          )}

          {step === 1 && company.data && (
            <Stack gap="sm">
              <Text c={COLORS.textSecondary} size="sm">
                Если что-то не так, напишите в банк.
              </Text>
              <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid="company-data">
                <SummaryRow label="Компания" value={company.data.name} />
                <SummaryRow label="Форма" value={company.data.company_type_label} />
                <SummaryRow label={<Term id="inn">ИНН</Term>} value={company.data.inn} />
                <SummaryRow label={<Term id="ogrn">ОГРН / ОГРНИП</Term>} value={company.data.ogrn} />
                <SummaryRow label={<Term id="okved">ОКВЭД</Term>} value={`${company.data.okved}, ${company.data.industry.toLowerCase()}`} />
                <SummaryRow label="Регион" value={company.data.region} />
                <SummaryRow label="Дата регистрации" value={date(company.data.registration_date)} />
                <SummaryRow label="Выручка за год по отчётности" value={company.data.annual_revenue === null ? "нет данных" : money(company.data.annual_revenue)} />
                <SummaryRow label="Сотрудников" value={company.data.employees_count} />
              </Box>
            </Stack>
          )}

          {step === 2 && (
            <Stack gap="md">
              <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
                <NumberInput
                  label={<Term id="revenue">Выручка в месяц, ₽</Term>}
                  value={form.monthly_revenue}
                  onChange={(value) => set("monthly_revenue", value === "" ? "" : Number(value))}
                  thousandSeparator=" "
                  min={0}
                  error={errors.monthly_revenue}
                  description="Сколько в среднем поступает на счёт за месяц. Можно примерно"
                  data-testid="form-revenue"
                />
                <NumberInput
                  label={<Term id="expenses">Расходы в месяц, ₽</Term>}
                  value={form.monthly_expenses}
                  onChange={(value) => set("monthly_expenses", value === "" ? "" : Number(value))}
                  thousandSeparator=" "
                  min={0}
                  error={errors.monthly_expenses}
                  description="Аренда, зарплаты, закупки и другие постоянные траты за месяц"
                  data-testid="form-expenses"
                />
                <NumberInput
                  label={<Term id="current_payments">Платежи по другим кредитам в месяц, ₽</Term>}
                  value={form.current_loan_payments}
                  onChange={(value) => set("current_loan_payments", value === "" ? "" : Number(value))}
                  thousandSeparator=" "
                  min={0}
                  error={errors.current_loan_payments}
                  description="Сумма ежемесячных платежей по действующим кредитам и займам. Если их нет, укажите 0"
                  data-testid="form-payments"
                />
              </SimpleGrid>
            </Stack>
          )}

          {step === 3 && (
            <Stack gap="md">
              <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }}>
                <SummaryRow label="Продукт" value={product?.name} />
                <SummaryRow label="Цель" value={selectedPurpose?.label} />
                <SummaryRow label="Сумма" value={money(numberOrNull(form.amount))} />
                <SummaryRow label={<Term id="term">Срок</Term>} value={months(numberOrNull(form.term_months))} />
                {form.purpose_comment && <SummaryRow label="Комментарий к цели" value={form.purpose_comment} />}
                {form.collateral_description && <SummaryRow label={<Term id="collateral">Залог</Term>} value={form.collateral_description} />}
                <SummaryRow label="Компания" value={company.data?.name} />
                <SummaryRow label={<Term id="revenue">Выручка в месяц</Term>} value={money(numberOrNull(form.monthly_revenue))} />
                <SummaryRow label={<Term id="expenses">Расходы в месяц</Term>} value={money(numberOrNull(form.monthly_expenses))} />
                <SummaryRow label={<Term id="current_payments">Платежи по другим кредитам в месяц</Term>} value={money(numberOrNull(form.current_loan_payments))} />
              </Box>
            </Stack>
          )}

          {(save.isError || submit.isError) && (
            <Alert color="brand" radius="lg" title="Не получилось сохранить">
              {errorText(save.error ?? submit.error)}
            </Alert>
          )}

          <Group justify="space-between">
            <Button variant="default" disabled={step === 0} onClick={() => setStep(step - 1)}>
              Назад
            </Button>
            {step < 3 && (
              <Button onClick={() => void next()} loading={save.isPending} data-testid="form-next">
                {step === 0 && !application ? "Сохранить черновик и продолжить" : "Далее"}
              </Button>
            )}
            {step === 3 && !isNeedsInfo && (
              <Button
                size="lg"
                loading={save.isPending || submit.isPending}
                disabled={submitAction ? !submitAction.enabled : false}
                onClick={async () => {
                  try {
                    const saved = await save.mutateAsync();
                    submit.mutate(saved);
                  } catch {
                    /* ошибка показана выше */
                  }
                }}
                data-testid="form-submit"
              >
                {submitAction?.label ?? "Отправить заявку"}
              </Button>
            )}
            {step === 3 && isNeedsInfo && (
              <Button
                size="lg"
                loading={save.isPending}
                onClick={async () => {
                  try {
                    const saved = await save.mutateAsync();
                    notifications.show({ color: "lime", title: "Анкета обновлена", message: "Теперь нажмите «Отправить уточнения» на странице заявки." });
                    navigate(`/client/applications/${saved.id}`);
                  } catch {
                    /* ошибка показана выше */
                  }
                }}
                data-testid="form-save-needs-info"
              >
                Сохранить и вернуться к заявке
              </Button>
            )}
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
