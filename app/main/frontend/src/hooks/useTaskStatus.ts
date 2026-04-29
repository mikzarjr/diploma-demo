"use client";

import { useEffect, useRef, useState } from "react";

import { tasksApi, type TaskStatusResponse } from "@/lib/api";

export interface UseTaskStatusOptions {
  /** Интервал опроса в мс, по умолчанию 2000. */
  intervalMs?: number;
  /** Колбэки для удобства — вызываются когда таска завершилась. */
  onSuccess?: (status: TaskStatusResponse) => void;
  onFailure?: (status: TaskStatusResponse) => void;
}

/**
 * Поллит GET /tasks/{id}/status пока state не станет терминальным
 * (SUCCESS/FAILURE/REVOKED). Возвращает последний полученный статус.
 *
 * Передай `null` чтобы остановить опрос (например, когда task_id ещё не создан).
 */
export function useTaskStatus(
  taskId: string | null,
  options: UseTaskStatusOptions = {}
) {
  const { intervalMs = 2000, onSuccess, onFailure } = options;

  const [status, setStatus] = useState<TaskStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSuccessRef = useRef(onSuccess);
  const onFailureRef = useRef(onFailure);
  useEffect(() => {
    onSuccessRef.current = onSuccess;
    onFailureRef.current = onFailure;
  }, [onSuccess, onFailure]);

  useEffect(() => {
    if (!taskId) {
      setStatus(null);
      setError(null);
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const TERMINAL: Array<TaskStatusResponse["state"]> = [
      "SUCCESS",
      "FAILURE",
      "REVOKED",
    ];

    const tick = async () => {
      if (cancelled) return;
      try {
        const s = await tasksApi.status(taskId);
        if (cancelled) return;
        setStatus(s);
        setError(null);

        if (TERMINAL.includes(s.state)) {
          if (s.state === "SUCCESS") onSuccessRef.current?.(s);
          else onFailureRef.current?.(s);
          return; // не планируем следующий тик
        }

        timer = setTimeout(tick, intervalMs);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        // продолжаем поллить — возможно сеть мигнула
        timer = setTimeout(tick, intervalMs);
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [taskId, intervalMs]);

  return { status, error };
}

/** Человекочитаемый лейбл для step'а из бэкенда. */
export function describeStep(step: string | null | undefined): string {
  switch (step) {
    case "queued":
      return "В очереди...";
    case "downloading":
      return "Загрузка аудио...";
    case "transcribing":
      return "Транскрипция с диаризацией...";
    case "analyzing":
      return "Разбор реплик, метрики...";
    case "llm_checks":
      return "LLM-проверки...";
    case "summary":
      return "Генерация резюме...";
    case "done":
      return "Готово";
    default:
      return "Обработка...";
  }
}
