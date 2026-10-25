/**
 * «Получить финансирование»: подбор продукта по нескольким простым вопросам (POST /products/recommend)
 * или выбор из списка. На каждой карточке продукта — калькулятор платежа.
 */
import { Badge, Button, Card, Group, List, NumberInput, SegmentedControl, Select, SimpleGrid, Stack, Switch, Tabs, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCheck, IconX } from "@tabler/icons-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, call, type Schemas } from "../../api/client";
import { Calculator, defaultAmount, defaultTerm } from "../../components/Calculator";
import { NumberedCard } from "../../components/NumberedCard";
import { EmptyState, ErrorState, RowsSkeleton } from "../../components/States";
import { Term } from "../../components/Term";
import { COLORS } from "../../theme";
import { days } from "../../utils/format";

type Product = Schemas["ProductOut"];

export function usePurposes() {
  return useQuery({ queryKey: ["purposes"], queryFn: () => call(api.GET("/api/v1/dictionaries/purposes")), staleTime: Infinity });
}

export function useProducts() {
  return useQuery({ queryKey: ["products"], queryFn: () => call(api.GET("/api/v1/products")), staleTime: 60_000 });
}

function applyLink(product: Product, extra: Record<string, string | number | undefined>) {
  const params = new URLSearchParams({ product: product.code });
  Object.entries(extra).forEach(([key, value]) => value !== undefined && params.set(key, String(value)));
  return `/client/apply?${params.toString()}`;
}

function ProductCard({ product, children, footer }: { product: Product; children?: React.ReactNode; footer?: React.ReactNode }) {
  const navigate = useNavigate();
  const [terms, setTerms] = useState({ amount: defaultAmount(product), term: defaultTerm(product) });
  return (
    <Card data-testid={`product-${product.code}`}>
      <Stack gap="sm">
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <Title order={3}>{product.name}</Title>
          <Badge variant="light" size="lg">
            <Term id="rate">{product.rate_text}</Term>
          </Badge>
        </Group>
        {children}
        <Text>{product.description}</Text>
        <Text size="sm" c={COLORS.textSecondary}>
          <b>Подходит, если:</b> {product.suitable_for}
        </Text>
        <Group gap="xs">
          <Badge color="gray" variant="light">
            решение ~{days(product.decision_days)}
          </Badge>
          {product.requires_collateral && (
            <Badge color="violet" variant="light">
              <Term id="collateral">нужен залог</Term>
            </Badge>
          )}
        </Group>
        <Calculator product={product} onChange={(amount, term) => setTerms({ amount, term })} />
        {footer}
        <Group>
          <Button onClick={() => navigate(applyLink(product, terms))} data-testid={`apply-${product.code}`}>
            Оформить заявку
          </Button>
        </Group>
      </Stack>
    </Card>
  );
}

function Recommendation({ item, request }: { item: Schemas["RecommendationOut"]; request: Schemas["RecommendRequest"] }) {
  const navigate = useNavigate();
  // Для подходящего продукта сразу показываем платёж по сумме и сроку из ответов; их можно подвигать
  const [terms, setTerms] = useState({ amount: Number(request.amount), term: request.term_months });
  return (
    <Card style={item.suitable ? { outline: `2px solid ${COLORS.positive}` } : undefined} data-testid={`recommendation-${item.product.code}`}>
      <Stack gap="sm">
        <Group justify="space-between" wrap="wrap">
          <Title order={3}>{item.product.name}</Title>
          <Badge color={item.suitable ? "lime" : "gray"} variant="light" c={item.suitable ? COLORS.positiveText : undefined} size="lg">
            {item.suitable ? "Подходит" : "Не подходит"}
          </Badge>
        </Group>
        <Text size="sm">{item.product.description}</Text>
        <List spacing={4} size="sm" center>
          {item.reasons.map((reason) => (
            <List.Item key={reason} icon={<ThemeIcon color="lime" size={20} radius="xl"><IconCheck size={14} color={COLORS.text} /></ThemeIcon>}>
              {reason}
            </List.Item>
          ))}
          {item.warnings.map((warning) => (
            <List.Item key={warning} icon={<ThemeIcon color="gray" size={20} radius="xl"><IconX size={14} /></ThemeIcon>}>
              {warning}
            </List.Item>
          ))}
        </List>
        {item.suitable && (
          <Calculator
            product={item.product}
            initialAmount={Number(request.amount)}
            initialTerm={request.term_months}
            onChange={(amount, term) => setTerms({ amount, term })}
          />
        )}
        <Group justify="space-between" wrap="wrap">
          <Badge variant="light" size="lg">
            <Term id="rate">{item.product.rate_text}</Term>
          </Badge>
          {item.suitable && (
            <Button
              onClick={() => navigate(applyLink(item.product, { amount: terms.amount, term: terms.term, purpose: request.purpose_code }))}
              data-testid={`apply-recommended-${item.product.code}`}
            >
              Оформить заявку
            </Button>
          )}
        </Group>
      </Stack>
    </Card>
  );
}

function Picker() {
  const purposes = usePurposes();
  const [request, setRequest] = useState<Schemas["RecommendRequest"]>({
    purpose_code: "",
    amount: 1_500_000,
    term_months: 24,
    urgency: "week",
    has_collateral: false,
  });
  const recommend = useMutation({ mutationFn: (body: Schemas["RecommendRequest"]) => call(api.POST("/api/v1/products/recommend", { body })) });
  const ready = Boolean(request.purpose_code) && Number(request.amount) > 0 && request.term_months > 0;

  return (
    <Stack gap="lg">
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <NumberedCard number={1} title="На что нужны деньги?">
          {purposes.isError ? (
            <ErrorState error={purposes.error} />
          ) : (
            <Select
              placeholder="Выберите цель"
              data={(purposes.data ?? []).map((item) => ({ value: item.code, label: item.label }))}
              value={request.purpose_code || null}
              onChange={(value) => setRequest({ ...request, purpose_code: value ?? "" })}
              data-testid="purpose-select"
            />
          )}
        </NumberedCard>
        <NumberedCard number={2} title="Какая сумма нужна?">
          <NumberInput value={request.amount} onChange={(value) => setRequest({ ...request, amount: Number(value) || 0 })} thousandSeparator=" " suffix=" ₽" min={0} step={100_000} />
        </NumberedCard>
        <NumberedCard number={3} title={<>На какой <Term id="term">срок</Term>?</>}>
          <NumberInput value={request.term_months} onChange={(value) => setRequest({ ...request, term_months: Number(value) || 0 })} suffix=" мес." min={1} max={360} />
        </NumberedCard>
        <NumberedCard number={4} title="Как быстро нужны деньги?">
          <SegmentedControl
            fullWidth
            value={request.urgency}
            onChange={(value) => setRequest({ ...request, urgency: value as Schemas["RecommendRequest"]["urgency"] })}
            data={[
              { value: "asap", label: "Срочно" },
              { value: "week", label: "За неделю" },
              { value: "month", label: "За месяц" },
            ]}
          />
          <Switch
            checked={request.has_collateral}
            onChange={(event) => setRequest({ ...request, has_collateral: event.currentTarget.checked })}
            label={<>Есть <Term id="collateral">залог</Term> (помещение, транспорт, оборудование)</>}
          />
        </NumberedCard>
      </SimpleGrid>
      <Group>
        <Button size="lg" disabled={!ready} loading={recommend.isPending} onClick={() => recommend.mutate(request)} data-testid="recommend">
          Подобрать продукт
        </Button>
        {!request.purpose_code && <Text c={COLORS.textSecondary}>Выберите цель, и мы подскажем, какой кредит подходит.</Text>}
      </Group>
      {recommend.isError && <ErrorState error={recommend.error} />}
      {recommend.data && (
        <Stack gap="md">
          <Title order={2}>Что вам подойдёт</Title>
          {recommend.data.some((item) => item.suitable) ? null : (
            <Text c={COLORS.textSecondary}>Сейчас мы не можем предложить кредит с такими параметрами. Попробуйте изменить сумму или срок: ниже видно, что не подошло.</Text>
          )}
          {/* Карточки разной высоты (у подходящей есть калькулятор) не растягиваются друг под друга */}
          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" style={{ alignItems: "start" }}>
            {recommend.data.map((item) => (
              <Recommendation key={item.product.code} item={item} request={request} />
            ))}
          </SimpleGrid>
        </Stack>
      )}
    </Stack>
  );
}

function Catalog() {
  const products = useProducts();
  if (products.isLoading) return <RowsSkeleton rows={2} height={360} />;
  if (products.isError) return <ErrorState error={products.error} onRetry={() => void products.refetch()} />;
  if (!products.data?.length) return <EmptyState title="Продуктов пока нет" />;
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg" style={{ alignItems: "start" }}>
      {products.data.map((product) => (
        <ProductCard key={product.code} product={product} />
      ))}
    </SimpleGrid>
  );
}

export function ProductsPage() {
  return (
    <Stack gap="lg">
      <Stack gap={4}>
        <Title order={1}>Получить финансирование</Title>
        <Text c={COLORS.textSecondary} size="lg">
          Ответьте на 4 вопроса, и мы подскажем подходящий кредит. Можно и сразу выбрать продукт из списка.
        </Text>
      </Stack>
      <Tabs defaultValue="picker" variant="pills" radius="md">
        <Tabs.List mb="lg">
          <Tabs.Tab value="picker">Подобрать продукт</Tabs.Tab>
          <Tabs.Tab value="catalog" data-testid="tab-catalog">
            Все продукты
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="picker">
          <Picker />
        </Tabs.Panel>
        <Tabs.Panel value="catalog">
          <Catalog />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
