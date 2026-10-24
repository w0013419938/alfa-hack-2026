/** Запрос уточнений: что именно нужно, загрузка запрошенных документов, ссылка на исправление анкеты. */
import { Badge, Box, Button, Card, Group, List, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCheck, IconPencil } from "@tabler/icons-react";
import { Link } from "react-router-dom";

import type { Application } from "../../api/client";
import { COLORS, RADIUS } from "../../theme";
import { UploadForm } from "./DocumentsBlock";

export function InfoRequestPanel({ application }: { application: Application }) {
  const request = application.info_request;
  if (!request) return null;
  const canEdit = application.available_actions.some((action) => action.code === "edit" && action.enabled);

  return (
    <Card style={{ outline: `2px solid ${COLORS.attention}` }} data-testid="info-request">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={3}>Что нужно от вас</Title>
          <Badge color="violet" variant="light">
            Запрос от: {request.created_by}
          </Badge>
        </Group>
        <Text>{request.comment}</Text>

        {request.fields.length > 0 && (
          <Box p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }}>
            <Text fw={600} mb="xs">
              Исправьте в анкете
            </Text>
            <List spacing={4}>
              {request.fields.map((field) => (
                <List.Item key={field.field}>
                  <b>{field.label}</b>
                  {field.message ? `: ${field.message}` : ""}
                </List.Item>
              ))}
            </List>
            {canEdit && (
              <Button component={Link} to={`/client/applications/${application.id}/edit`} mt="sm" variant="light" leftSection={<IconPencil size={18} />}>
                Исправить анкету
              </Button>
            )}
          </Box>
        )}

        {request.documents.map((document) => (
          <Box key={document.kind} p="md" bg={COLORS.page} style={{ borderRadius: RADIUS.block }} data-testid={`requested-${document.kind}`}>
            <Group justify="space-between" mb={document.uploaded ? 0 : "sm"}>
              <Text fw={600}>{document.label}</Text>
              {document.uploaded ? (
                <Group gap={6}>
                  <ThemeIcon color="lime" radius="xl" size="sm">
                    <IconCheck size={14} color={COLORS.text} />
                  </ThemeIcon>
                  <Text size="sm" fw={500}>
                    Загружено
                  </Text>
                </Group>
              ) : (
                <Badge color="violet" variant="light">
                  Нужно загрузить
                </Badge>
              )}
            </Group>
            {!document.uploaded && <UploadForm application={application} fixedKind={document.kind} compact />}
          </Box>
        ))}

        <Text size="sm" c={COLORS.textSecondary}>
          Когда всё будет готово, нажмите «Отправить уточнения» вверху страницы, и заявка снова уйдёт на проверку.
        </Text>
      </Stack>
    </Card>
  );
}
