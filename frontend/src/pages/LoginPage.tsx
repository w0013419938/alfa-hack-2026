/** Вход: форма логина и «Демо-доступ» — вход в один клик под каждой тестовой учёткой. */
import { Alert, Box, Button, Card, Container, Grid, Group, Image, PasswordInput, SimpleGrid, Stack, Text, TextInput, Title, UnstyledButton } from "@mantine/core";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { errorText } from "../api/client";
import lightning from "../assets/lightning-3d.png";
import { useAuth } from "../auth/AuthContext";
import { homePathFor } from "../auth/RequireRole";
import { DEMO_ACCOUNTS } from "../texts/demoAccounts";
import { COLORS, RADIUS } from "../theme";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ login: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  async function signIn(loginValue: string, password: string) {
    setError(null);
    setBusy(loginValue);
    try {
      const signedIn = await login(loginValue, password);
      navigate(homePathFor(signedIn.role), { replace: true });
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(null);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form.login || !form.password) {
      setError("Введите логин и пароль");
      return;
    }
    void signIn(form.login.trim(), form.password);
  }

  const demoAccess = (
    <Card>
      <Stack gap="md">
        <Stack gap={4}>
          <Title order={2} fz={24}>
            Демо-доступ
          </Title>
          <Text c={COLORS.textSecondary}>Вход в один клик. Каждая учётка показывает свой сценарий. Пароль: логин и «123».</Text>
        </Stack>
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          {DEMO_ACCOUNTS.map((account) => (
            <UnstyledButton
              key={account.login}
              onClick={() => void signIn(account.login, `${account.login}123`)}
              disabled={busy !== null}
              data-testid={`demo-${account.login}`}
              className="demo-account"
              style={{
                borderRadius: RADIUS.block,
                padding: 16,
                minHeight: 44,
                opacity: busy && busy !== account.login ? 0.6 : 1,
              }}
            >
              <Group justify="space-between" align="flex-start" wrap="nowrap">
                <Stack gap={2}>
                  <Text fw={600}>{account.title}</Text>
                  <Text size="sm" c={COLORS.textSecondary}>
                    {account.scenario}
                  </Text>
                </Stack>
                <Text size="xs" c={COLORS.textSecondary} style={{ whiteSpace: "nowrap" }}>
                  {busy === account.login ? "Входим…" : account.login}
                </Text>
              </Group>
            </UnstyledButton>
          ))}
        </SimpleGrid>
      </Stack>
    </Card>
  );

  const loginForm = (
    <Card>
      <form onSubmit={onSubmit}>
        <Stack gap="md">
          <Title order={2} fz={24}>
            Вход по логину
          </Title>
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput label="Логин" value={form.login} onChange={(event) => setForm({ ...form, login: event.currentTarget.value })} autoComplete="username" />
            <PasswordInput
              label="Пароль"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.currentTarget.value })}
              autoComplete="current-password"
            />
          </SimpleGrid>
          {error && (
            <Alert color="brand" radius="lg" data-testid="login-error" role="alert">
              {error}
            </Alert>
          )}
          <Group>
            <Button type="submit" loading={busy === form.login.trim()}>
              Войти
            </Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );

  return (
    <Box bg={COLORS.page} mih="100vh" py={48}>
      <Container size="xl">
        <Grid gap="xl" align="flex-start">
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Stack gap="xl">
              <Stack gap={8}>
                <Title order={1} fz={{ base: 34, sm: 44 }}>
                  Кредитный кабинет предпринимателя
                </Title>
                <Text size="lg" maw={620}>
                  Подберите кредит, подайте заявку и следите за решением банка в одном месте.
                </Text>
              </Stack>
              {params.get("expired") && (
                <Alert color="violet" radius="lg">
                  Сессия истекла. Войдите снова.
                </Alert>
              )}
              {demoAccess}
              {loginForm}
            </Stack>
          </Grid.Col>
          {/* 3D-молния из макета Альфы (Figma «кейс-школа-альфа»). Только на широком экране, без анимации */}
          <Grid.Col span={{ base: 12, md: 4 }} visibleFrom="md">
            <Box style={{ position: "sticky", top: 48 }}>
              <Image src={lightning} alt="" w="100%" maw={420} mx="auto" />
            </Box>
          </Grid.Col>
        </Grid>
      </Container>
    </Box>
  );
}
