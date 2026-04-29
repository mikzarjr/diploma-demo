"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Button,
  Tooltip,
  Avatar,
  InputAdornment,
  TextField,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import RefreshIcon from "@mui/icons-material/RefreshOutlined";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalkOutlined";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import FilterListIcon from "@mui/icons-material/FilterListOutlined";
import CloudUploadIcon from "@mui/icons-material/CloudUploadOutlined";
import FileDownloadIcon from "@mui/icons-material/FileDownloadOutlined";
import { callsApi, usersApi } from "@/lib/api";
import { useAuth, isHeadOrAdmin } from "@/context/AuthContext";
import { statusLabels, statusColors } from "@/lib/status";
import { formatDuration, formatDateTime } from "@/lib/format";
import { useTableSort, SortableCell } from "@/hooks/useTableSort";
import { TableSkeleton } from "@/components/Skeleton";
import { downloadCsv } from "@/lib/csvExport";
import type { Call, User } from "@/types";

type CallSortKey = "id" | "created_at" | "manager" | "duration" | "status";

function CallsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const canFilterByManager = isHeadOrAdmin(user);

  const [calls, setCalls] = useState<Call[]>([]);
  const [managers, setManagers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get("status") || "");
  const [managerFilter, setManagerFilter] = useState<string>(
    canFilterByManager ? searchParams.get("manager") || "" : ""
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const apiStatus = statusFilter === "recent" ? undefined : statusFilter || undefined;
      const [callsData, usersData] = await Promise.all([
        callsApi.list({
          status: apiStatus,
          manager_id: canFilterByManager && managerFilter ? Number(managerFilter) : undefined,
          limit: 200,
        }),
        canFilterByManager ? usersApi.list("manager") : Promise.resolve([] as User[]),
      ]);

      let filtered = callsData;
      if (statusFilter === "recent") {
        const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
        filtered = callsData.filter(
          (c) => c.created_at && new Date(c.created_at) >= oneHourAgo
        );
      }

      setCalls(filtered);
      setManagers(usersData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [statusFilter, managerFilter, canFilterByManager]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = () => {
    const rows = sort.sorted.length ? sort.sorted : calls;
    downloadCsv("calls", rows, [
      { header: "ID", value: (c) => c.id },
      { header: "Дата", value: (c) => (c.created_at ? formatDateTime(c.created_at) : "") },
      {
        header: "Менеджер",
        value: (c) =>
          c.manager_name || (c.manager_id ? managerMap.get(c.manager_id) || `#${c.manager_id}` : ""),
      },
      { header: "Длительность (сек)", value: (c) => c.duration_sec ?? "" },
      { header: "Статус", value: (c) => statusLabels[c.status || ""] || c.status || "" },
      { header: "Направление", value: (c) => c.direction || "" },
      { header: "От", value: (c) => c.from_number || "" },
      { header: "Кому", value: (c) => c.to_number || "" },
    ]);
  };

  const handleDelete = async (id: number) => {
    if (!confirm(`Удалить звонок #${id}?`)) return;
    try {
      await callsApi.delete(id);
      setCalls((prev) => prev.filter((c) => c.id !== id));
    } catch (e: unknown) {
      alert(`Ошибка: ${e instanceof Error ? e.message : e}`);
    }
  };

  const managerMap = new Map(managers.map((m) => [m.id, m.name]));

  const displayedCalls = search.trim()
    ? calls.filter((c) => {
        const q = search.trim().toLowerCase();
        const managerName = (
          c.manager_name ||
          (c.manager_id ? managerMap.get(c.manager_id) : "") ||
          ""
        ).toLowerCase();
        return (
          String(c.id).includes(q) ||
          managerName.includes(q) ||
          (statusLabels[c.status || ""] || "").toLowerCase().includes(q)
        );
      })
    : calls;

  const filterCount = [statusFilter, canFilterByManager ? managerFilter : ""].filter(Boolean).length;

  const sort = useTableSort<Call, CallSortKey>(displayedCalls, {
    id: (c) => c.id,
    created_at: (c) => (c.created_at ? new Date(c.created_at) : null),
    manager: (c) =>
      c.manager_name || (c.manager_id ? managerMap.get(c.manager_id) : null) || null,
    duration: (c) => c.duration_sec,
    status: (c) => statusLabels[c.status || ""] || c.status,
  });
  const sortedCalls = sort.sorted;

  return (
    <Box className="fade-in">
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
          <TextField
            size="small"
            placeholder="Поиск по ID, менеджеру или статусу"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ minWidth: 280, flex: { xs: "1 1 100%", md: "0 1 320px" } }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: 18, color: "text.disabled" }} />
                  </InputAdornment>
                ),
              },
            }}
          />

          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel>Статус</InputLabel>
            <Select
              value={statusFilter}
              label="Статус"
              onChange={(e: SelectChangeEvent) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">Все статусы</MenuItem>
              <MenuItem value="recent">За последний час</MenuItem>
              <MenuItem value="analyzed">Проанализирован</MenuItem>
              <MenuItem value="analyzing">Анализ</MenuItem>
              <MenuItem value="transcribing">Транскрипция</MenuItem>
              <MenuItem value="queued">В очереди</MenuItem>
              <MenuItem value="error">Ошибка</MenuItem>
            </Select>
          </FormControl>

          {canFilterByManager && (
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Менеджер</InputLabel>
              <Select
                value={managerFilter}
                label="Менеджер"
                onChange={(e: SelectChangeEvent) => setManagerFilter(e.target.value)}
              >
                <MenuItem value="">Все менеджеры</MenuItem>
                {managers.map((m) => (
                  <MenuItem key={m.id} value={String(m.id)}>
                    {m.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          {filterCount > 0 && (
            <Chip
              icon={<FilterListIcon sx={{ fontSize: 14 }} />}
              label={`${filterCount} ${filterCount === 1 ? "фильтр" : "фильтра"}`}
              size="small"
              color="primary"
              onDelete={() => {
                setStatusFilter("");
                setManagerFilter("");
              }}
            />
          )}

          <Box sx={{ flex: 1 }} />

          <Button
            variant="outlined"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={loadData}
          >
            Обновить
          </Button>
          <Tooltip title={calls.length === 0 ? "Нет данных для экспорта" : "Скачать CSV"}>
            <span>
              <Button
                variant="outlined"
                size="small"
                startIcon={<FileDownloadIcon />}
                onClick={handleExport}
                disabled={calls.length === 0}
              >
                Экспорт
              </Button>
            </span>
          </Tooltip>
          <Button
            variant="contained"
            size="small"
            startIcon={<CloudUploadIcon />}
            onClick={() => router.push("/upload")}
          >
            Загрузить
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : (
      <Card>
        {displayedCalls.length === 0 ? (
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
              <PhoneInTalkIcon sx={{ fontSize: 30, color: "primary.main" }} />
            </Box>
            <Typography sx={{ fontSize: 16, fontWeight: 600, color: "text.primary", mb: 0.5 }}>
              Звонков не найдено
            </Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              {search || statusFilter || managerFilter
                ? "Попробуйте изменить фильтры или поисковый запрос"
                : "Загрузите первый звонок в разделе «Загрузка»"}
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <SortableCell sortKey="id" sort={sort}>ID</SortableCell>
                  <SortableCell sortKey="created_at" sort={sort}>Дата и время</SortableCell>
                  <SortableCell sortKey="manager" sort={sort}>Менеджер</SortableCell>
                  <SortableCell sortKey="duration" sort={sort} align="right">Длительность</SortableCell>
                  <SortableCell sortKey="status" sort={sort}>Статус</SortableCell>
                  <TableCell align="right" sx={{ width: 80 }}>
                    Действия
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedCalls.map((call) => {
                  const managerName =
                    call.manager_name ||
                    (call.manager_id ? managerMap.get(call.manager_id) : null);
                  return (
                    <TableRow
                      key={call.id}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => router.push(`/calls/${call.id}`)}
                    >
                      <TableCell>
                        <Typography
                          sx={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: "primary.dark",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          #{call.id}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography sx={{ fontSize: 13, color: "text.primary" }}>
                          {formatDateTime(call.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {managerName ? (
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            <Avatar
                              sx={{
                                width: 28,
                                height: 28,
                                fontSize: 12,
                                bgcolor: "brand.violetTint",
                                color: "primary.dark",
                                fontWeight: 600,
                              }}
                            >
                              {managerName[0]?.toUpperCase()}
                            </Avatar>
                            <Typography sx={{ fontSize: 13, fontWeight: 500 }}>
                              {managerName}
                            </Typography>
                          </Box>
                        ) : (
                          <Typography sx={{ fontSize: 13, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          sx={{
                            fontSize: 13,
                            fontWeight: 500,
                            fontVariantNumeric: "tabular-nums",
                            color: call.duration_sec ? "text.primary" : "text.disabled",
                          }}
                        >
                          {formatDuration(call.duration_sec)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={statusLabels[call.status || ""] || call.status || "—"}
                          color={statusColors[call.status || ""] || "default"}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">
                        {canFilterByManager && (
                          <Tooltip title="Удалить">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDelete(call.id);
                              }}
                              sx={{
                                color: "text.disabled",
                                "&:hover": { color: "error.main", bgcolor: "error.light" },
                              }}
                            >
                              <DeleteIcon sx={{ fontSize: 18 }} />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Card>
      )}

      {!loading && displayedCalls.length > 0 && (
        <Typography
          sx={{
            fontSize: 12.5,
            color: "text.secondary",
            mt: 2,
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          Показано {displayedCalls.length}
          {displayedCalls.length !== calls.length ? ` из ${calls.length}` : ""}
        </Typography>
      )}
    </Box>
  );
}

export default function CallsPage() {
  return (
    <Suspense
      fallback={
        <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
          <CircularProgress />
        </Box>
      }
    >
      <CallsContent />
    </Suspense>
  );
}
