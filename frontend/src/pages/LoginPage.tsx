/** Вход: форма логина и «Демо-доступ» — вход в один клик под каждой тестовой учёткой. */
import { Alert, Box, Button, Card, Container, Group, PasswordInput, SimpleGrid, Stack, Text, TextInput, Title, UnstyledButton } from "@mantine/core";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { errorText } from "../api/client";
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

  return (
    <Box bg={COLORS.page} mih="100vh" py={48}>
      <Container size="md">
        <Stack gap="xl">
          <Stack gap={6}>
            <Title order={1}>
              Кредитный кабинет <span style={{ color: COLORS.accent }}>предпринимателя</span>
            </Title>
            <Text c={COLORS.textSecondary} size="lg">
              Подберите кредит, подайте заявку и следите за решением банка в одном месте.
            </Text>
          </Stack>

          {params.get("expired") && (
            <Alert color="violet" radius="lg">
              Сессия истекла. Войдите снова.
            </Alert>
          )}

          <Card>
            <form onSubmit={onSubmit}>
              <Stack gap="md">
                <Title order={3}>Вход</Title>
                <SimpleGrid cols={{ base: 1, sm: 2 }}>
                  <TextInput
                    label="Логин"
                    value={form.login}
                    onChange={(event) => setForm({ ...form, login: event.currentTarget.value })}
                    autoComplete="username"
                  />
                  <PasswordInput
                    label="Пароль"
                    value={form.password}
                    onChange={(event) => setForm({ ...form, password: event.currentTarget.value })}
                    autoComplete="current-password"
                  />
                </SimpleGrid>
                {error && (
                  <Alert color="brand" radius="lg" data-testid="login-error">
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

          <Card>
            <Stack gap="md">
              <Stack gap={4}>
                <Title order={3}>Демо-доступ</Title>
                <Text c={COLORS.textSecondary}>
                  Вход в один клик. Каждая учётка показывает свой сценарий. Пароль: логин и «123».
                </Text>
              </Stack>
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                {DEMO_ACCOUNTS.map((account) => (
                  <UnstyledButton
                    key={account.login}
                    onClick={() => void signIn(account.login, `${account.login}123`)}
                    disabled={busy !== null}
                    data-testid={`demo-${account.login}`}
                    style={{
                      background: COLORS.page,
                      borderRadius: RADIUS.block,
                      padding: 16,
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
                      <Text size="xs" ff="monospace" c={COLORS.accent} style={{ whiteSpace: "nowrap" }}>
                        {busy === account.login ? "входим…" : account.login}
                      </Text>
                    </Group>
                  </UnstyledButton>
                ))}
              </SimpleGrid>
            </Stack>
          </Card>
        </Stack>
      </Container>
    </Box>
  );
}
