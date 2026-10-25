/** «Что понадобится» на первом шаге анкеты: какие сведения и документы нужны и можно ли без них. */
import { Badge, Box, Group, List, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconCheck } from "@tabler/icons-react";

import { CHECKLIST, CHECKLIST_COLLATERAL } from "../texts/checklist";
import { COLORS, RADIUS } from "../theme";

export function Checklist({ withCollateral }: { withCollateral: boolean }) {
  const items = withCollateral ? [...CHECKLIST.slice(0, 2), CHECKLIST_COLLATERAL, ...CHECKLIST.slice(2)] : CHECKLIST;
  return (
    <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid="checklist">
      <Stack gap="sm">
        <Text fw={600}>Что понадобится</Text>
        <List
          spacing="sm"
          size="sm"
          center={false}
          icon={
            <ThemeIcon color="lime" size={20} radius="xl">
              <IconCheck size={14} color={COLORS.text} />
            </ThemeIcon>
          }
        >
          {items.map((item) => (
            <List.Item key={item.title}>
              <Group gap="xs" wrap="wrap">
                <Text size="sm" fw={500}>
                  {item.title}
                </Text>
                {!item.required && (
                  <Badge variant="light" color="gray" size="sm">
                    Можно без этого
                  </Badge>
                )}
              </Group>
              <Text size="sm" c={COLORS.textSecondary}>
                {item.why} {item.note}
              </Text>
            </List.Item>
          ))}
        </List>
      </Stack>
    </Box>
  );
}
