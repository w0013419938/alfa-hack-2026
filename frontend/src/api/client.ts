/**
 * Клиент API. Типы запросов и ответов генерируются из docs/openapi.json (npm run gen:api) —
 * вручную их не описываем, поэтому фронт не может разойтись с бэкендом незаметно.
 */
import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

/** Схемы ответов API, например Schemas["ApplicationOut"] */
export type Schemas = components["schemas"];
export type Application = Schemas["ApplicationOut"];
export type ApplicationAction = Schemas["ActionOut"];

const TOKEN_KEY = "credit-cabinet-token";

export const tokenStore = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

/** Ошибка API с понятным человеку текстом из {"error": {"message"}} */
export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

// Подставляем токен в каждый запрос; если сессия истекла — отправляем на вход
const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = tokenStore.get();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ request, response }) {
    if (response.status === 401 && !request.url.endsWith("/auth/login") && tokenStore.get()) {
      tokenStore.clear();
      window.location.assign("/login?expired=1");
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: "" });
api.use(authMiddleware);

type ErrorBody = { error?: { code?: string; message?: string; details?: unknown } };

/** Превращает ответ openapi-fetch в данные или бросает ApiError с понятным сообщением. */
export async function call<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  let result;
  try {
    result = await request;
  } catch {
    throw new ApiError(0, "network_error", "Нет связи с сервером. Проверьте, что сервис запущен, и попробуйте ещё раз.");
  }
  const { data, error, response } = result;
  if (response.ok) return data as T;

  const body = (error ?? {}) as ErrorBody;
  if (body.error?.message) {
    throw new ApiError(response.status, body.error.code ?? "error", body.error.message, body.error.details);
  }
  if (response.status >= 502) {
    throw new ApiError(response.status, "unavailable", "Сервер временно недоступен. Подождите немного и обновите страницу.");
  }
  throw new ApiError(response.status, "error", "Что-то пошло не так. Попробуйте ещё раз.");
}

/** Текст ошибки для показа человеку (поддерживает и ApiError, и любые другие ошибки) */
export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    const details = Array.isArray(error.details)
      ? (error.details as { message?: string }[]).map((item) => item.message).filter(Boolean)
      : [];
    return details.length && error.code === "validation_error" ? `${error.message}: ${details.join("; ")}` : error.message;
  }
  return "Что-то пошло не так. Попробуйте ещё раз.";
}

/** Скачивание файла с токеном (обычная ссылка не передала бы заголовок Authorization) */
export async function downloadFile(url: string, filename: string): Promise<void> {
  const token = tokenStore.get();
  const response = await fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new ApiError(response.status, "download_failed", "Не удалось скачать файл. Попробуйте ещё раз.");
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

/** Загрузка документа (multipart). openapi-fetch плохо дружит с FormData, поэтому — обычный fetch с тем же разбором ошибок. */
export async function uploadDocument(applicationId: string, kind: string, file: File): Promise<Schemas["DocumentOut"]> {
  const form = new FormData();
  form.append("kind", kind);
  form.append("file", file);
  const token = tokenStore.get();
  let response: Response;
  try {
    response = await fetch(`/api/v1/applications/${applicationId}/documents`, {
      method: "POST",
      body: form,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new ApiError(0, "network_error", "Нет связи с сервером. Попробуйте ещё раз.");
  }
  if (response.status === 413) {
    throw new ApiError(413, "file_too_large", "Файл слишком большой. Максимальный размер — 10 МБ.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = (body as ErrorBody).error;
    throw new ApiError(response.status, error?.code ?? "error", error?.message ?? "Не удалось загрузить файл. Попробуйте ещё раз.");
  }
  return body as Schemas["DocumentOut"];
}
