"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  Button,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined";
import ContentCopyIcon from "@mui/icons-material/ContentCopyOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutlineOutlined";
import RefreshIcon from "@mui/icons-material/RefreshOutlined";
import SecurityIcon from "@mui/icons-material/VerifiedUserOutlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmberOutlined";
import WebhookIcon from "@mui/icons-material/WebhookOutlined";
import StorageIcon from "@mui/icons-material/StorageOutlined";
import InboxIcon from "@mui/icons-material/InboxOutlined";
import { integrationsApi } from "@/lib/api";
import type { IntegrationLog, IntegrationStatus } from "@/types";
import { formatDateTime } from "@/lib/format";
import { TableRowSkeleton } from "@/components/Skeleton";
import { useTableSort, SortableCell } from "@/hooks/useTableSort";

type LogSortKey = "created_at" | "provider" | "event_type" | "external_id" | "status" | "call_id" | "message";

const statusLabels: Record<string, string> = {
  received: "Принят",
  processed: "Обработан",
  skipped: "Дубликат",
  error: "Ошибка",
};

type Tone = "violet" | "teal" | "amber" | "rose" | "sky" | "slate";

const statusTones: Record<string, Tone> = {
  received: "sky",
  processed: "teal",
  skipped: "amber",
  error: "rose",
};

const tones: Record<
  Tone,
  { bg: string; ring: string; fg: string; avatarBg: string; avatarFg: string }
> = {
  violet: {
    bg: "linear-gradient(180deg, #F5F3FF 0%, #EDE9FE 100%)",
    ring: "rgba(139,92,246,0.20)",
    fg: "#5B21B6",
    avatarBg: "#EDE9FE",
    avatarFg: "#6D28D9",
  },
  teal: {
    bg: "linear-gradient(180deg, #ECFDF5 0%, #D1FAE5 100%)",
    ring: "rgba(16,185,129,0.22)",
    fg: "#047857",
    avatarBg: "#D1FAE5",
    avatarFg: "#047857",
  },
  amber: {
    bg: "linear-gradient(180deg, #FFFBEB 0%, #FEF3C7 100%)",
    ring: "rgba(245,158,11,0.25)",
    fg: "#B45309",
    avatarBg: "#FEF3C7",
    avatarFg: "#B45309",
  },
  rose: {
    bg: "linear-gradient(180deg, #FFF1F2 0%, #FFE4E6 100%)",
    ring: "rgba(244,63,94,0.22)",
    fg: "#BE123C",
    avatarBg: "#FFE4E6",
    avatarFg: "#BE123C",
  },
  sky: {
    bg: "linear-gradient(180deg, #F0F9FF 0%, #E0F2FE 100%)",
    ring: "rgba(14,165,233,0.22)",
    fg: "#0369A1",
    avatarBg: "#E0F2FE",
    avatarFg: "#0369A1",
  },
  slate: {
    bg: "linear-gradient(180deg, #F8FAFC 0%, #F1F5F9 100%)",
    ring: "rgba(100,116,139,0.20)",
    fg: "#334155",
    avatarBg: "#E2E8F0",
    avatarFg: "#475569",
  },
};

export default function IntegrationsPage() {
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [logs, setLogs] = useState<IntegrationLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [snackbar, setSnackbar] = useState({ open: false, message: "" });

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statusData, logsData] = await Promise.all([
        integrationsApi.status(),
        integrationsApi.listLogs(
          statusFilter ? { status: statusFilter, limit: 100 } : { limit: 100 }
        ),
      ]);
      setStatus(statusData);
      setLogs(logsData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const logSort = useTableSort<IntegrationLog, LogSortKey>(logs, {
    created_at: (l) => (l.created_at ? new Date(l.created_at) : null),
    provider: (l) => l.provider,
    event_type: (l) => l.event_type,
    external_id: (l) => l.external_id,
    status: (l) => l.status,
    call_id: (l) => l.call_id,
    message: (l) => l.message,
  });
  const sortedLogs = logSort.sorted;

  const handleCopyUrl = async () => {
    if (!status?.webhook_url) return;
    try {
      await navigator.clipboard.writeText(status.webhook_url);
      setSnackbar({ open: true, message: "URL скопирован в буфер обмена" });
    } catch {
      setSnackbar({ open: true, message: "Не удалось скопировать" });
    }
  };

  const hmacTone = status?.webhook_configured ? tones.teal : tones.amber;
  const violet = tones.violet;
  const sky = tones.sky;

  return (
    <Box className="fade-in">
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Webhook hero card */}
      <Card
        sx={{
          mb: 2.5,
          background: violet.bg,
          border: `1px solid ${violet.ring}`,
          boxShadow: "none",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <Box
          sx={{
            position: "absolute",
            top: -80,
            right: -60,
            width: 260,
            height: 260,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(255,255,255,0.55) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <CardContent sx={{ position: "relative", py: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 2 }}>
            <Avatar sx={{ width: 44, height: 44, bgcolor: violet.avatarBg, color: violet.avatarFg }}>
              <WebhookIcon />
            </Avatar>
            <Box>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: violet.fg,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Webhook для телефонии
              </Typography>
              <Typography sx={{ fontSize: 17, fontWeight: 700, color: violet.fg }}>
                Точка входа для интеграций
              </Typography>
            </Box>
          </Box>

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              p: 1.25,
              pl: 2,
              bgcolor: "rgba(255,255,255,0.7)",
              border: `1px solid ${violet.ring}`,
              borderRadius: 2,
              backdropFilter: "blur(4px)",
            }}
          >
            <Typography
              sx={{
                flex: 1,
                fontFamily: "'SF Mono', 'Fira Code', monospace",
                fontSize: 13,
                wordBreak: "break-all",
                color: "text.primary",
              }}
            >
              {status?.webhook_url || "—"}
            </Typography>
            <Tooltip title="Скопировать">
              <span>
                <IconButton
                  size="small"
                  onClick={handleCopyUrl}
                  disabled={!status}
                  sx={{
                    color: violet.avatarFg,
                    "&:hover": { bgcolor: violet.avatarBg },
                  }}
                >
                  <ContentCopyIcon sx={{ fontSize: 17 }} />
                </IconButton>
              </span>
            </Tooltip>
          </Box>

          <Typography sx={{ mt: 1.25, fontSize: 12.5, color: violet.fg, opacity: 0.85 }}>
            Вставьте этот URL в кабинете провайдера как адрес доставки событий о завершённых звонках.
            Метод — POST, Content-Type — application/json.
          </Typography>
        </CardContent>
      </Card>

      {/* Status cards row */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 1.5,
          mb: 2.5,
        }}
      >
        <Card
          sx={{
            background: hmacTone.bg,
            border: `1px solid ${hmacTone.ring}`,
            boxShadow: "none",
          }}
        >
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 2.25, "&:last-child": { pb: 2.25 } }}>
            <Avatar sx={{ width: 42, height: 42, bgcolor: hmacTone.avatarBg, color: hmacTone.avatarFg }}>
              <SecurityIcon />
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: hmacTone.fg,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Подпись HMAC
              </Typography>
              <Typography sx={{ fontSize: 17, fontWeight: 700, color: hmacTone.fg, lineHeight: 1.2 }}>
                {status?.webhook_configured ? "Включена" : "Не настроена"}
              </Typography>
              <Typography sx={{ fontSize: 12, color: hmacTone.fg, opacity: 0.8, mt: 0.25 }}>
                {status?.webhook_configured
                  ? "Запросы проверяются секретом"
                  : "Dev-режим без верификации"}
              </Typography>
            </Box>
          </CardContent>
        </Card>

        <Card
          sx={{
            background: sky.bg,
            border: `1px solid ${sky.ring}`,
            boxShadow: "none",
          }}
        >
          <CardContent sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 2.25, "&:last-child": { pb: 2.25 } }}>
            <Avatar sx={{ width: 42, height: 42, bgcolor: sky.avatarBg, color: sky.avatarFg }}>
              <StorageIcon />
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography
                sx={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: sky.fg,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Лимит записи
              </Typography>
              <Typography
                sx={{ fontSize: 17, fontWeight: 700, color: sky.fg, lineHeight: 1.2, fontVariantNumeric: "tabular-nums" }}
              >
                {status?.max_audio_mb ?? "—"} МБ
              </Typography>
              <Typography sx={{ fontSize: 12, color: sky.fg, opacity: 0.8, mt: 0.25 }}>
                Максимальный размер аудиофайла
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>

      {status && !status.webhook_configured && (
        <Alert
          severity="warning"
          variant="outlined"
          icon={<WarningAmberIcon />}
          sx={{ mb: 2.5, borderRadius: 2 }}
        >
          HMAC-секрет не задан (<code>TELEPHONY_WEBHOOK_SECRET</code>). Запросы принимаются без
          проверки подписи — безопасно только в dev-окружении.
        </Alert>
      )}

      {/* Filter bar */}
      <Card sx={{ mb: 2.5 }}>
        <CardContent
          sx={{
            display: "flex",
            gap: 1.5,
            alignItems: "center",
            py: 2,
            flexWrap: "wrap",
            "&:last-child": { pb: 2 },
          }}
        >
          <Typography sx={{ fontSize: 14, fontWeight: 600, color: "text.primary", mr: 1 }}>
            Журнал событий
          </Typography>

          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Статус</InputLabel>
            <Select
              value={statusFilter}
              label="Статус"
              onChange={(e: SelectChangeEvent) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">Все статусы</MenuItem>
              <MenuItem value="received">Принят</MenuItem>
              <MenuItem value="processed">Обработан</MenuItem>
              <MenuItem value="skipped">Дубликат</MenuItem>
              <MenuItem value="error">Ошибка</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flex: 1 }} />

          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={load}
            disabled={loading}
          >
            Обновить
          </Button>
        </CardContent>
      </Card>

      <Card>
        {loading ? (
          <Box>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRowSkeleton key={i} cols={7} />
            ))}
          </Box>
        ) : logs.length === 0 ? (
          <Box sx={{ textAlign: "center", py: 10, px: 3 }}>
            <Box
              sx={{
                display: "inline-flex",
                width: 64,
                height: 64,
                borderRadius: "50%",
                bgcolor: "brand.violetTint",
                alignItems: "center",
                justifyContent: "center",
                mb: 2,
              }}
            >
              <InboxIcon sx={{ fontSize: 30, color: "primary.main" }} />
            </Box>
            <Typography sx={{ fontSize: 16, fontWeight: 600, color: "text.primary", mb: 0.5 }}>
              Журнал пуст
            </Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              Webhook&apos;и от телефонии ещё не приходили
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <SortableCell sortKey="created_at" sort={logSort}>Время</SortableCell>
                  <SortableCell sortKey="provider" sort={logSort}>Провайдер</SortableCell>
                  <SortableCell sortKey="event_type" sort={logSort}>Событие</SortableCell>
                  <SortableCell sortKey="external_id" sort={logSort}>External ID</SortableCell>
                  <SortableCell sortKey="status" sort={logSort}>Статус</SortableCell>
                  <SortableCell sortKey="call_id" sort={logSort}>Call</SortableCell>
                  <SortableCell sortKey="message" sort={logSort}>Сообщение</SortableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedLogs.map((log) => {
                  const t = tones[statusTones[log.status] || "slate"];
                  return (
                    <TableRow key={log.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>
                        <Typography sx={{ fontSize: 12.5, color: "text.secondary", fontVariantNumeric: "tabular-nums" }}>
                          {formatDateTime(log.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={log.provider}
                          size="small"
                          sx={{
                            bgcolor: "brand.violetTint",
                            color: "primary.dark",
                            fontWeight: 600,
                            fontFamily: "'SF Mono', monospace",
                            fontSize: 11.5,
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography sx={{ fontSize: 12.5, color: "text.primary" }}>
                          {log.event_type || "—"}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ fontFamily: "'SF Mono', monospace", fontSize: 11.5, color: "text.secondary" }}>
                        {log.external_id || "—"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={
                            log.status === "error" ? (
                              <ErrorOutlineIcon sx={{ fontSize: 14 }} />
                            ) : log.status === "processed" ? (
                              <CheckCircleIcon sx={{ fontSize: 14 }} />
                            ) : log.status === "skipped" ? (
                              <WarningAmberIcon sx={{ fontSize: 14 }} />
                            ) : undefined
                          }
                          label={statusLabels[log.status] || log.status}
                          size="small"
                          sx={{
                            bgcolor: t.avatarBg,
                            color: t.fg,
                            fontWeight: 600,
                            border: `1px solid ${t.ring}`,
                            "& .MuiChip-icon": { color: t.avatarFg },
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        {log.call_id ? (
                          <Chip
                            label={`#${log.call_id}`}
                            size="small"
                            component="a"
                            href={`/calls/${log.call_id}`}
                            clickable
                            sx={{
                              bgcolor: "brand.violetTint",
                              color: "primary.dark",
                              fontWeight: 600,
                              fontVariantNumeric: "tabular-nums",
                              textDecoration: "none",
                            }}
                          />
                        ) : (
                          <Typography sx={{ fontSize: 13, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                      <TableCell
                        sx={{
                          maxWidth: 380,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        <Tooltip title={log.message || ""} placement="top-start">
                          <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>
                            {log.message || "—"}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>

      {!loading && logs.length > 0 && (
        <Typography
          sx={{
            fontSize: 12.5,
            color: "text.secondary",
            mt: 2,
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          Всего записей: {logs.length}
        </Typography>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      />
    </Box>
  );
}
