/** Документы заявки: список с загрузкой файлов и форма загрузки (когда она доступна). */
import { Alert, Button, Card, FileInput, Group, Select, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconDownload, IconFile, IconUpload } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, call, downloadFile, errorText, uploadDocument, type Application } from "../../api/client";
import { COLORS } from "../../theme";
import { dateTime } from "../../utils/format";
import { ErrorState, LoadingState } from "../States";

export function useDocumentKinds() {
  return useQuery({ queryKey: ["document-kinds"], queryFn: () => call(api.GET("/api/v1/dictionaries/document-kinds")), staleTime: Infinity });
}

/** Форма загрузки одного файла. Вид документа можно зафиксировать (когда банк просит конкретный). */
export function UploadForm({ application, fixedKind, compact }: { application: Application; fixedKind?: string; compact?: boolean }) {
  const queryClient = useQueryClient();
  const kinds = useDocumentKinds();
  const [kind, setKind] = useState<string | null>(fixedKind ?? null);
  const [file, setFile] = useState<File | null>(null);

  const upload = useMutation({
    mutationFn: () => uploadDocument(application.id, kind!, file!),
    onSuccess: (document) => {
      notifications.show({ color: "lime", title: "Файл загружен", message: `${document.kind_label}: ${document.filename}` });
      setFile(null);
      void queryClient.invalidateQueries({ queryKey: ["documents", application.id] });
      void queryClient.invalidateQueries({ queryKey: ["application", application.id] });
    },
  });

  const options = (kinds.data ?? []).filter((item) => item.client_can_upload).map((item) => ({ value: item.code, label: item.label }));

  return (
    <Stack gap="xs">
      <Group align="flex-end" gap="sm" wrap="wrap">
        {!fixedKind && (
          <Select label="Вид документа" placeholder="Выберите" data={options} value={kind} onChange={setKind} w={{ base: "100%", sm: 280 }} />
        )}
        <FileInput
          label={compact ? undefined : "Файл"}
          placeholder="PDF, JPG или PNG до 10 МБ"
          accept=".pdf,.jpg,.jpeg,.png"
          value={file}
          onChange={setFile}
          leftSection={<IconFile size={18} />}
          w={{ base: "100%", sm: 300 }}
          clearable
          data-testid={`file-input-${fixedKind ?? "any"}`}
        />
        <Button
          leftSection={<IconUpload size={18} />}
          variant="light"
          disabled={!kind || !file}
          loading={upload.isPending}
          onClick={() => upload.mutate()}
          data-testid={`upload-${fixedKind ?? "any"}`}
        >
          Загрузить
        </Button>
      </Group>
      {upload.isError && (
        <Text size="sm" c="brand">
          {errorText(upload.error)}
        </Text>
      )}
    </Stack>
  );
}

export function DocumentsBlock({ application }: { application: Application }) {
  // Если банк попросил конкретные документы, загрузка — в блоке «Что нужно от вас»; здесь — только для прочих файлов
  const requestedDocuments = (application.info_request?.documents.length ?? 0) > 0;
  const documents = useQuery({
    queryKey: ["documents", application.id, application.documents_count],
    queryFn: () => call(api.GET("/api/v1/applications/{application_id}/documents", { params: { path: { application_id: application.id } } })),
  });
  const canUpload = application.available_actions.some((action) => action.code === "upload_document" && action.enabled);

  return (
    <Card id="documents">
      <Stack gap="md">
        <Title order={3}>Документы</Title>
        {documents.isLoading && <LoadingState />}
        {documents.isError && <ErrorState error={documents.error} onRetry={() => void documents.refetch()} />}
        {documents.data && documents.data.length === 0 && (
          <Text c={COLORS.textSecondary}>
            Документы пока не загружены.
            {canUpload && !requestedDocuments && " Банк может попросить выписку по расчётному счёту за 6 месяцев: её можно загрузить здесь."}
            {requestedDocuments && " Документ, который просит банк, загрузите в блоке «Что нужно от вас» выше."}
          </Text>
        )}
        {documents.data?.map((document) => (
          <Group key={document.id} justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <ThemeIcon variant="light" color={document.kind === "contract" ? "lime" : "gray"} radius="md">
                {document.kind === "contract" ? <IconCheck size={18} /> : <IconFile size={18} />}
              </ThemeIcon>
              <Stack gap={0}>
                <Text fw={500}>{document.kind_label}</Text>
                <Text size="xs" c={COLORS.textSecondary}>
                  {document.filename}, загрузил: {document.uploaded_by.toLowerCase()}, {dateTime(document.created_at)}
                </Text>
              </Stack>
            </Group>
            <Button
              variant="subtle"
              size="xs"
              leftSection={<IconDownload size={16} />}
              onClick={() =>
                downloadFile(document.download_url, document.filename).catch((error) =>
                  notifications.show({ color: "brand", title: "Не удалось скачать", message: errorText(error) }),
                )
              }
            >
              Скачать
            </Button>
          </Group>
        ))}
        {canUpload && (
          <Alert color="gray" radius="lg" variant="light" title={requestedDocuments ? "Другие документы (необязательно)" : "Загрузить документ"}>
            <UploadForm application={application} />
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
