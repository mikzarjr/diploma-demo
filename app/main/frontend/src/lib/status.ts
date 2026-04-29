/**
 * Отображаемые лейблы и цвета для Call.status.
 * Источник статусов: backend `services/analysis.py` + `tasks/analysis.py`.
 *
 *   new          — загружен, не обработан
 *   queued       — поставлен в очередь Celery
 *   transcribing — идёт whisper + диаризация
 *   analyzing    — идёт анализ реплик, метрики, LLM
 *   transcribed  — legacy (старые записи)
 *   analyzed     — всё готово
 *   error        — упал на каком-то шаге
 */

export type CallStatusColor =
  | "default"
  | "info"
  | "success"
  | "error"
  | "warning";

export const statusLabels: Record<string, string> = {
  new: "Новый",
  queued: "В очереди",
  transcribing: "Транскрипция",
  analyzing: "Анализ",
  transcribed: "Транскрибирован",
  analyzed: "Проанализирован",
  error: "Ошибка",
};

export const statusColors: Record<string, CallStatusColor> = {
  new: "default",
  queued: "warning",
  transcribing: "info",
  analyzing: "info",
  transcribed: "info",
  analyzed: "success",
  error: "error",
};

export function labelFor(status: string | null | undefined): string {
  if (!status) return "—";
  return statusLabels[status] || status;
}

export function colorFor(status: string | null | undefined): CallStatusColor {
  if (!status) return "default";
  return statusColors[status] || "default";
}
