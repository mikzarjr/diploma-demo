"use client";

import { useEffect, useState, useCallback } from "react";
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
  Button,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Switch,
  FormControlLabel,
  Tooltip,
  Snackbar,
  Avatar,
  InputAdornment,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import AddIcon from "@mui/icons-material/AddRounded";
import EditIcon from "@mui/icons-material/EditOutlined";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import RefreshIcon from "@mui/icons-material/RefreshOutlined";
import RuleIcon from "@mui/icons-material/RuleOutlined";
import SmartToyIcon from "@mui/icons-material/SmartToyOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import FactCheckIcon from "@mui/icons-material/FactCheckOutlined";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesomeOutlined";
import { checksApi } from "@/lib/api";
import { useTableSort, SortableCell } from "@/hooks/useTableSort";
import { TableRowSkeleton } from "@/components/Skeleton";
import type { Check } from "@/types";

type CheckSortKey = "name" | "type" | "output_type" | "weight" | "active";

const typeLabels: Record<string, string> = {
  rule_based: "Правило",
  llm_based: "LLM",
};

const outputLabels: Record<string, string> = {
  boolean: "Да / Нет",
  score: "Оценка",
  category: "Категория",
};

const ruleTypes = [
  { value: "contains", label: "Содержит текст" },
  { value: "starts_with", label: "Начинается с" },
  { value: "min_turns", label: "Мин. кол-во реплик" },
];

type Tone = "violet" | "teal" | "amber" | "rose" | "sky";

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
};

interface CheckFormData {
  name: string;
  description: string;
  type: string;
  output_type: string;
  weight: number;
  active: boolean;

  rule_type: string;
  rule_value: string;
  rule_speaker: string;

  prompt: string;
}

const emptyForm: CheckFormData = {
  name: "",
  description: "",
  type: "rule_based",
  output_type: "boolean",
  weight: 1.0,
  active: true,
  rule_type: "contains",
  rule_value: "",
  rule_speaker: "manager",
  prompt: "",
};

function formToPayload(form: CheckFormData) {
  const base = {
    name: form.name.trim(),
    description: form.description.trim() || undefined,
    scope: "call",
    type: form.type,
    output_type: form.output_type,
    weight: form.weight,
    active: form.active,
  };

  if (form.type === "rule_based") {
    return {
      ...base,
      rule_config: {
        rule_type: form.rule_type,
        value: form.rule_type === "min_turns" ? Number(form.rule_value) : form.rule_value,
        speaker: form.rule_speaker || undefined,
      },
      prompt: undefined,
      expected_format: undefined,
    };
  }

  return {
    ...base,
    rule_config: undefined,
    prompt: form.prompt.trim() || undefined,
    expected_format: '{"passed": bool, "explanation": "string"}',
  };
}

function checkToForm(check: Check): CheckFormData {
  const rc = check.rule_config as Record<string, unknown> | null;
  return {
    name: check.name,
    description: check.description || "",
    type: check.type || "rule_based",
    output_type: check.output_type || "boolean",
    weight: check.weight ?? 1.0,
    active: check.active,
    rule_type: (rc?.rule_type as string) || "contains",
    rule_value: String(rc?.value ?? ""),
    rule_speaker: (rc?.speaker as string) || "manager",
    prompt: check.prompt || "",
  };
}

export default function ChecksPage() {
  const [checks, setChecks] = useState<Check[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");

  const [typeFilter, setTypeFilter] = useState<string>("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingCheck, setEditingCheck] = useState<Check | null>(null);
  const [form, setForm] = useState<CheckFormData>(emptyForm);
  const [formError, setFormError] = useState("");

  const [snackbar, setSnackbar] = useState({ open: false, message: "" });
  const [highlightId, setHighlightId] = useState<number | null>(null);

  const loadChecks = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await checksApi.list(
        typeFilter ? { type: typeFilter } : undefined
      );
      setChecks(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [typeFilter]);

  useEffect(() => {
    loadChecks();
  }, [loadChecks]);

  useEffect(() => {
    if (highlightId === null) return;
    const timer = setTimeout(() => setHighlightId(null), 3000);
    return () => clearTimeout(timer);
  }, [highlightId]);

  const openCreate = () => {
    setEditingCheck(null);
    setForm(emptyForm);
    setFormError("");
    setDialogOpen(true);
  };

  const openEdit = (check: Check) => {
    setEditingCheck(check);
    setForm(checkToForm(check));
    setFormError("");
    setDialogOpen(true);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setEditingCheck(null);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      setFormError("Название обязательно");
      return;
    }
    if (form.type === "llm_based" && !form.prompt.trim()) {
      setFormError("Промпт обязателен для LLM-проверки");
      return;
    }
    if (form.type === "rule_based" && !form.rule_value.trim()) {
      setFormError("Значение правила обязательно");
      return;
    }

    setSaving(true);
    setFormError("");

    try {
      const payload = formToPayload(form);
      if (editingCheck) {
        await checksApi.update(editingCheck.id, payload);
        setSnackbar({ open: true, message: `Проверка «${form.name}» обновлена` });
      } else {
        const created = await checksApi.create(payload);
        setSnackbar({ open: true, message: `Проверка «${form.name}» создана` });
        setHighlightId(created.id);
      }
      handleClose();
      loadChecks();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (check: Check) => {
    if (!confirm(`Удалить проверку «${check.name}»?`)) return;
    try {
      await checksApi.delete(check.id);
      setChecks((prev) => prev.filter((c) => c.id !== check.id));
      setSnackbar({ open: true, message: `Проверка «${check.name}» удалена` });
    } catch (e: unknown) {
      alert(`Ошибка: ${e instanceof Error ? e.message : e}`);
    }
  };

  const handleToggleActive = async (check: Check) => {
    try {
      await checksApi.update(check.id, { active: !check.active });
      setChecks((prev) =>
        prev.map((c) => (c.id === check.id ? { ...c, active: !c.active } : c))
      );
      setSnackbar({
        open: true,
        message: `Проверка «${check.name}» ${!check.active ? "включена" : "выключена"}`,
      });
    } catch (e: unknown) {
      alert(`Ошибка: ${e instanceof Error ? e.message : e}`);
    }
  };

  const filtered = checks.filter((c) => {
    if (!search.trim()) return true;
    const q = search.trim().toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      (c.description || "").toLowerCase().includes(q) ||
      (typeLabels[c.type || ""] || "").toLowerCase().includes(q)
    );
  });

  const ruleCount = checks.filter((c) => c.type === "rule_based").length;
  const llmCount = checks.filter((c) => c.type === "llm_based").length;
  const activeCount = checks.filter((c) => c.active).length;

  const checkSort = useTableSort<Check, CheckSortKey>(filtered, {
    name: (c) => c.name,
    type: (c) => typeLabels[c.type || ""] || c.type,
    output_type: (c) => outputLabels[c.output_type || ""] || c.output_type,
    weight: (c) => c.weight,
    active: (c) => (c.active ? 1 : 0),
  });
  const sortedChecks = checkSort.sorted;

  return (
    <Box className="fade-in">
      {/* Tonal stat row */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(3, 1fr)" },
          gap: 1.5,
          mb: 2.5,
        }}
      >
        {(
          [
            {
              tone: "violet" as Tone,
              icon: <FactCheckIcon />,
              label: "Всего проверок",
              value: checks.length,
              sub: `${activeCount} активно`,
            },
            {
              tone: "teal" as Tone,
              icon: <RuleIcon />,
              label: "Правила",
              value: ruleCount,
              sub: "детерминированные",
            },
            {
              tone: "amber" as Tone,
              icon: <SmartToyIcon />,
              label: "LLM-проверки",
              value: llmCount,
              sub: "на основе промптов",
            },
          ]
        ).map((s) => {
          const t = tones[s.tone];
          return (
            <Card
              key={s.label}
              sx={{
                background: t.bg,
                border: `1px solid ${t.ring}`,
                boxShadow: "none",
              }}
            >
              <CardContent
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.5,
                  py: 2,
                  "&:last-child": { pb: 2 },
                }}
              >
                <Avatar sx={{ width: 42, height: 42, bgcolor: t.avatarBg, color: t.avatarFg }}>
                  {s.icon}
                </Avatar>
                <Box sx={{ flex: 1 }}>
                  <Typography
                    sx={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: t.fg,
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {s.label}
                  </Typography>
                  <Typography sx={{ fontSize: 22, fontWeight: 700, color: t.fg, lineHeight: 1.1 }}>
                    {s.value}
                  </Typography>
                  <Typography sx={{ fontSize: 11.5, color: t.fg, opacity: 0.75 }}>
                    {s.sub}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>

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
          <TextField
            size="small"
            placeholder="Поиск по названию или описанию"
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
            <InputLabel>Тип</InputLabel>
            <Select
              value={typeFilter}
              label="Тип"
              onChange={(e: SelectChangeEvent) => setTypeFilter(e.target.value)}
            >
              <MenuItem value="">Все типы</MenuItem>
              <MenuItem value="rule_based">Правило</MenuItem>
              <MenuItem value="llm_based">LLM</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flex: 1 }} />

          <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={loadChecks}>
            Обновить
          </Button>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate}>
            Создать проверку
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Card>
        {loading ? (
          <Box>
            {Array.from({ length: 6 }).map((_, i) => (
              <TableRowSkeleton key={i} cols={6} />
            ))}
          </Box>
        ) : filtered.length === 0 ? (
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
              <AutoAwesomeIcon sx={{ fontSize: 30, color: "primary.main" }} />
            </Box>
            <Typography sx={{ fontSize: 16, fontWeight: 600, color: "text.primary", mb: 0.5 }}>
              {search || typeFilter ? "Ничего не нашли" : "Здесь пока пусто"}
            </Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>
              {search || typeFilter
                ? "Попробуйте изменить фильтры или поисковый запрос"
                : "Создайте первую проверку — она будет применяться к каждому новому звонку"}
            </Typography>
            {!search && !typeFilter && (
              <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate}>
                Создать проверку
              </Button>
            )}
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <SortableCell sortKey="name" sort={checkSort}>Название</SortableCell>
                  <SortableCell sortKey="type" sort={checkSort}>Тип</SortableCell>
                  <SortableCell sortKey="output_type" sort={checkSort}>Результат</SortableCell>
                  <SortableCell sortKey="weight" sort={checkSort} align="center">Вес</SortableCell>
                  <SortableCell sortKey="active" sort={checkSort} align="center">Активна</SortableCell>
                  <TableCell align="right" sx={{ width: 110 }}>Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedChecks.map((check) => {
                  const isLlm = check.type === "llm_based";
                  const tone = isLlm ? tones.amber : tones.teal;
                  return (
                    <TableRow
                      key={check.id}
                      hover
                      sx={{
                        transition: "background 0.5s",
                        ...(highlightId === check.id && {
                          bgcolor: "brand.violetTint",
                        }),
                        opacity: check.active ? 1 : 0.55,
                      }}
                    >
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.25 }}>
                          <Avatar
                            sx={{
                              width: 34,
                              height: 34,
                              bgcolor: tone.avatarBg,
                              color: tone.avatarFg,
                            }}
                          >
                            {isLlm ? <SmartToyIcon sx={{ fontSize: 18 }} /> : <RuleIcon sx={{ fontSize: 18 }} />}
                          </Avatar>
                          <Box sx={{ minWidth: 0 }}>
                            <Typography sx={{ fontSize: 13.5, fontWeight: 600, color: "text.primary" }}>
                              {check.name}
                            </Typography>
                            {check.description && (
                              <Typography
                                sx={{
                                  fontSize: 12,
                                  color: "text.secondary",
                                  mt: 0.25,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: "vertical",
                                }}
                              >
                                {check.description}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={isLlm ? <SmartToyIcon sx={{ fontSize: 14 }} /> : <RuleIcon sx={{ fontSize: 14 }} />}
                          label={typeLabels[check.type || ""] || check.type}
                          size="small"
                          sx={{
                            bgcolor: tone.avatarBg,
                            color: tone.fg,
                            fontWeight: 600,
                            border: `1px solid ${tone.ring}`,
                            "& .MuiChip-icon": { color: tone.avatarFg },
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                          {outputLabels[check.output_type || ""] || check.output_type}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`×${check.weight}`}
                          size="small"
                          sx={{
                            bgcolor: "brand.violetTint",
                            color: "primary.dark",
                            fontWeight: 600,
                            fontVariantNumeric: "tabular-nums",
                          }}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Switch
                          checked={check.active}
                          size="small"
                          onChange={() => handleToggleActive(check)}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Редактировать">
                          <IconButton
                            size="small"
                            onClick={() => openEdit(check)}
                            sx={{
                              color: "text.disabled",
                              "&:hover": { color: "primary.main", bgcolor: "brand.violetTint" },
                            }}
                          >
                            <EditIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Удалить">
                          <IconButton
                            size="small"
                            onClick={() => handleDelete(check)}
                            sx={{
                              color: "text.disabled",
                              "&:hover": { color: "error.main", bgcolor: "error.light" },
                            }}
                          >
                            <DeleteIcon sx={{ fontSize: 18 }} />
                          </IconButton>
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

      {!loading && filtered.length > 0 && (
        <Typography
          sx={{
            fontSize: 12.5,
            color: "text.secondary",
            mt: 2,
            textAlign: "right",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          Показано {filtered.length}
          {filtered.length !== checks.length ? ` из ${checks.length}` : ""}
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>
          {editingCheck ? `Редактировать: ${editingCheck.name}` : "Новая проверка"}
        </DialogTitle>
        <DialogContent
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 2.5,
            pt: "16px !important",
          }}
        >
          {formError && <Alert severity="error">{formError}</Alert>}

          <TextField
            label="Название"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
            required
            autoFocus
          />

          <TextField
            label="Описание"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            fullWidth
            multiline
            rows={2}
            helperText="Краткое описание — что проверяет эта проверка"
          />

          <Box sx={{ display: "flex", gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Тип проверки</InputLabel>
              <Select
                value={form.type}
                label="Тип проверки"
                onChange={(e: SelectChangeEvent) =>
                  setForm({ ...form, type: e.target.value })
                }
              >
                <MenuItem value="rule_based">Правило (rule-based)</MenuItem>
                <MenuItem value="llm_based">LLM (промпт)</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Тип результата</InputLabel>
              <Select
                value={form.output_type}
                label="Тип результата"
                onChange={(e: SelectChangeEvent) =>
                  setForm({ ...form, output_type: e.target.value })
                }
              >
                <MenuItem value="boolean">Да / Нет</MenuItem>
                <MenuItem value="score">Оценка (0-10)</MenuItem>
                <MenuItem value="category">Категория</MenuItem>
              </Select>
            </FormControl>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: -1.5 }}>
            {form.output_type === "boolean"
              ? "Результат: пройдена / не пройдена (да или нет)"
              : form.output_type === "score"
                ? "Результат: числовая оценка от 0 до 10"
                : "Результат: текстовая категория (напр. «позитивный», «нейтральный», «негативный»)"}
          </Typography>

          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <TextField
              label="Вес"
              type="number"
              value={form.weight}
              onChange={(e) => setForm({ ...form, weight: Number(e.target.value) })}
              sx={{ width: 140 }}
              slotProps={{ htmlInput: { min: 0, max: 10, step: 0.5 } }}
              helperText="Влияние на итог"
            />
            <Tooltip
              title="Вес определяет, насколько сильно эта проверка влияет на итоговую оценку звонка. Чем больше вес — тем важнее проверка."
              arrow
            >
              <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
            </Tooltip>
            <FormControlLabel
              control={
                <Switch
                  checked={form.active}
                  onChange={(e) => setForm({ ...form, active: e.target.checked })}
                />
              }
              label="Активна"
            />
          </Box>

          <Typography variant="subtitle2" color="text.secondary" sx={{ mt: 1 }}>
            {form.type === "rule_based" ? "Настройка правила" : "Настройка LLM-промпта"}
          </Typography>

          {form.type === "rule_based" ? (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Box sx={{ display: "flex", gap: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>Тип правила</InputLabel>
                  <Select
                    value={form.rule_type}
                    label="Тип правила"
                    onChange={(e: SelectChangeEvent) =>
                      setForm({ ...form, rule_type: e.target.value })
                    }
                  >
                    {ruleTypes.map((rt) => (
                      <MenuItem key={rt.value} value={rt.value}>
                        {rt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth>
                  <InputLabel>Спикер</InputLabel>
                  <Select
                    value={form.rule_speaker}
                    label="Спикер"
                    onChange={(e: SelectChangeEvent) =>
                      setForm({ ...form, rule_speaker: e.target.value })
                    }
                  >
                    <MenuItem value="manager">Менеджер</MenuItem>
                    <MenuItem value="client">Клиент</MenuItem>
                    <MenuItem value="">Любой</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              <TextField
                label={form.rule_type === "min_turns" ? "Минимальное количество" : "Искомый текст"}
                value={form.rule_value}
                onChange={(e) => setForm({ ...form, rule_value: e.target.value })}
                fullWidth
                required
                placeholder={
                  form.rule_type === "contains"
                    ? "Здравствуйте"
                    : form.rule_type === "starts_with"
                      ? "Добрый день"
                      : "5"
                }
              />
            </Box>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="Промпт"
                value={form.prompt}
                onChange={(e) => setForm({ ...form, prompt: e.target.value })}
                fullWidth
                required
                multiline
                rows={5}
                placeholder={`Проанализируй диалог и определи, выявил ли менеджер потребность клиента.`}
              />
              <Alert
                severity="info"
                variant="outlined"
                sx={{ "& .MuiAlert-message": { fontSize: 13 } }}
              >
                LLM автоматически вернёт результат в формате: пройдена/не пройдена + человекочитаемое пояснение.
                Формат ответа настроен в системе — вам достаточно описать что именно нужно проверить.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={saving}>
            Отмена
          </Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? <CircularProgress size={20} /> : editingCheck ? "Сохранить" : "Создать"}
          </Button>
        </DialogActions>
      </Dialog>

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
