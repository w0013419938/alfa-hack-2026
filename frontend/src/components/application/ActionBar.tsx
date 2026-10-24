/**
 * Кнопки действий. Рисуются строго из available_actions: какие кнопки есть, их подписи, активность,
 * причина неактивности и текст подтверждения — всё приходит из API.
 * Здесь решается только «как показать»: некоторые действия открывают форму или окно, а не вызываются сразу.
 */
import { Button, Group, Modal, Stack, Text, Textarea, Tooltip } from "@mantine/core";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Application, ApplicationAction } from "../../api/client";
import { SigningModal } from "./SigningModal";
import { useClientAction } from "./useClientAction";

// Действия, которые отменяют процесс, показываем спокойной кнопкой, а не красной
const QUIET_ACTIONS = new Set(["cancel", "decline_offer"]);
// Действия-переходы: не вызывают API, а ведут к форме или блоку на странице
const NAVIGATION_ACTIONS = new Set(["edit", "upload_document"]);

export function ActionBar({ application }: { application: Application }) {
  const navigate = useNavigate();
  const mutation = useClientAction(application);
  const [confirming, setConfirming] = useState<ApplicationAction | null>(null);
  const [comment, setComment] = useState("");
  const [signing, setSigning] = useState(false);

  const actions = application.available_actions;
  if (actions.length === 0) return null;

  function onClick(action: ApplicationAction) {
    if (action.code === "edit") {
      navigate(`/client/applications/${application.id}/edit`);
    } else if (action.code === "upload_document") {
      document.getElementById("documents")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (action.code === "sign") {
      setSigning(true);
    } else if (action.confirm_text || action.code === "provide_info") {
      setComment("");
      setConfirming(action);
    } else {
      mutation.mutate({ action: action.code });
    }
  }

  // Главное действие (первое активное «не отменяющее») — красной кнопкой
  const primary = actions.find((action) => action.enabled && !QUIET_ACTIONS.has(action.code) && !NAVIGATION_ACTIONS.has(action.code));

  return (
    <>
      <Group gap="sm" data-testid="actions">
        {actions.map((action) => {
          const variant = action === primary ? "filled" : QUIET_ACTIONS.has(action.code) ? "default" : "light";
          const button = (
            <Button
              key={action.code}
              variant={variant}
              color={QUIET_ACTIONS.has(action.code) ? "gray" : "brand"}
              disabled={!action.enabled}
              loading={mutation.isPending && mutation.variables?.action === action.code}
              onClick={() => onClick(action)}
              data-action={action.code}
            >
              {action.label}
            </Button>
          );
          return action.enabled ? (
            button
          ) : (
            <Tooltip key={action.code} label={action.disabled_reason ?? "Сейчас недоступно"}>
              <span>{button}</span>
            </Tooltip>
          );
        })}
      </Group>
      {actions.map(
        (action) =>
          !action.enabled &&
          action.disabled_reason && (
            <Text key={`${action.code}-reason`} size="sm" c="violet.7" mt="xs">
              {action.label}: {action.disabled_reason}
            </Text>
          ),
      )}

      <Modal opened={confirming !== null} onClose={() => setConfirming(null)} title={confirming?.label} centered radius="lg">
        <Stack>
          {confirming?.confirm_text && <Text>{confirming.confirm_text}</Text>}
          {confirming?.code === "provide_info" && (
            <Text size="sm">Заявка снова уйдёт на проверку. Если хотите, оставьте комментарий для банка.</Text>
          )}
          {(confirming?.code === "provide_info" || confirming?.code === "decline_offer" || confirming?.requires_comment) && (
            <Textarea
              label={confirming?.requires_comment ? "Комментарий (обязательно)" : "Комментарий (необязательно)"}
              value={comment}
              onChange={(event) => setComment(event.currentTarget.value)}
              autosize
              minRows={2}
              maxLength={2000}
            />
          )}
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setConfirming(null)}>
              Назад
            </Button>
            <Button
              color={confirming && QUIET_ACTIONS.has(confirming.code) ? "gray" : "brand"}
              loading={mutation.isPending}
              disabled={Boolean(confirming?.requires_comment && !comment.trim())}
              onClick={() => {
                if (!confirming) return;
                mutation.mutate({ action: confirming.code, comment }, { onSuccess: () => setConfirming(null) });
              }}
              data-testid="confirm-action"
            >
              {confirming?.label}
            </Button>
          </Group>
        </Stack>
      </Modal>

      <SigningModal
        application={application}
        opened={signing}
        onClose={() => setSigning(false)}
        signAction={actions.find((action) => action.code === "sign")}
      />
    </>
  );
}
