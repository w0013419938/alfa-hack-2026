/** Выполнение действия клиента над заявкой (submit, accept_offer, sign ...) через единую точку API. */
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api, call, errorText, type Application } from "../../api/client";

export function useClientAction(application: Application) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ action, comment }: { action: string; comment?: string }) =>
      call(
        api.POST("/api/v1/applications/{application_id}/actions/{action}", {
          params: { path: { application_id: application.id, action } },
          body: { comment: comment || null, version: application.version },
        }),
      ),
    onSuccess: (updated, variables) => {
      // Короткое подтверждение, названное так же, как кнопка, и новый статус заявки
      const label = application.available_actions.find((action) => action.code === variables.action)?.label ?? "Действие";
      notifications.show({ color: "lime", title: `Готово: «${label}»`, message: `Статус заявки: ${updated.status_label}.`, autoClose: 4000 });
      // Сразу показываем новый статус, не дожидаясь очередного опроса
      queryClient.setQueryData(["application", application.id], updated);
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      void queryClient.invalidateQueries({ queryKey: ["feed"] });
    },
    onError: (error) => {
      notifications.show({ color: "brand", title: "Действие не выполнено", message: errorText(error) });
      // Возможно, заявку изменили в другом месте, поэтому перечитываем
      void queryClient.invalidateQueries({ queryKey: ["application", application.id] });
    },
  });
}
