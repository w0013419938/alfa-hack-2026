/** Каркас страницы: шапка (кто вошёл, роль, выход, разделы) и контент на светло-сером фоне. */
import { Anchor, Badge, Box, Button, Container, Group, Stack, Text } from "@mantine/core";
import { IconLogout } from "@tabler/icons-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { COLORS, RADIUS } from "../theme";

const CLIENT_LINKS = [
  { to: "/client", label: "Мои заявки", end: true },
  { to: "/client/products", label: "Получить финансирование", end: false },
];
const BANK_LINKS = [
  { to: "/bank", label: "Очередь заявок", end: true },
  { to: "/bank/stats", label: "Статистика", end: false },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = user?.role === "employee" ? BANK_LINKS : CLIENT_LINKS;

  return (
    <Box bg={COLORS.page} mih="100vh">
      <Box component="header" bg={COLORS.card} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
        <Container size="xl" py="sm">
          <Group justify="space-between" wrap="wrap" gap="sm">
            <Group gap="lg" wrap="wrap">
              <Group gap={10}>
                <Box
                  w={36}
                  h={36}
                  bg={COLORS.accent}
                  style={{ borderRadius: 12, display: "grid", placeItems: "center", color: "white", fontWeight: 700 }}
                >
                  К
                </Box>
                <Text fw={700} size="lg">
                  Кредитный кабинет
                </Text>
              </Group>
              <Group gap="xs" component="nav">
                {links.map((link) => (
                  <Anchor
                    key={link.to}
                    component={NavLink}
                    to={link.to}
                    end={link.end}
                    underline="never"
                    c={COLORS.text}
                    px="sm"
                    py={6}
                    style={({ isActive }: { isActive: boolean }) => ({
                      borderRadius: RADIUS.control,
                      fontWeight: 500,
                      background: isActive ? COLORS.page : "transparent",
                    })}
                  >
                    {link.label}
                  </Anchor>
                ))}
              </Group>
            </Group>
            {user && (
              <Group gap="md" wrap="nowrap">
                <Stack gap={0} align="flex-end">
                  <Text size="sm" fw={600} data-testid="current-user">
                    {user.full_name}
                  </Text>
                  <Group gap={6}>
                    <Badge color={user.role === "employee" ? "violet" : "brand"} variant="light" size="sm">
                      {user.role_label}
                    </Badge>
                    {user.company && (
                      <Text size="xs" c={COLORS.textSecondary}>
                        {user.company.name}
                      </Text>
                    )}
                  </Group>
                </Stack>
                <Button
                  variant="subtle"
                  color="gray"
                  leftSection={<IconLogout size={18} />}
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  Выйти
                </Button>
              </Group>
            )}
          </Group>
        </Container>
      </Box>
      <Container size="xl" py="xl">
        <Outlet />
      </Container>
    </Box>
  );
}
