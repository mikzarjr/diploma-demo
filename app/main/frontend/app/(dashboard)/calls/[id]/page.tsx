"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  CircularProgress,
  Alert,
  Button,
  IconButton,
  Collapse,
  Tooltip,
  LinearProgress,
  Avatar,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBackRounded";
import PersonIcon from "@mui/icons-material/PersonOutlineOutlined";
import SupportAgentIcon from "@mui/icons-material/SupportAgentOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelIcon from "@mui/icons-material/CancelOutlined";
import ScienceIcon from "@mui/icons-material/ScienceOutlined";
import SummarizeIcon from "@mui/icons-material/SummarizeOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMoreRounded";
import RuleIcon from "@mui/icons-material/RuleOutlined";
import SmartToyIcon from "@mui/icons-material/SmartToyOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNewRounded";
import ReplayIcon from "@mui/icons-material/ReplayRounded";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonthOutlined";
import TimerIcon from "@mui/icons-material/TimerOutlined";
import BadgeIcon from "@mui/icons-material/BadgeOutlined";
import ForumIcon from "@mui/icons-material/ForumOutlined";
import PhoneIcon from "@mui/icons-material/PhoneOutlined";
import { callsApi, checksApi, getAudioUrl } from "@/lib/api";
import { useTaskStatus, describeStep } from "@/hooks/useTaskStatus";
import { statusLabels, statusColors } from "@/lib/status";
import { formatDuration, formatDateTime } from "@/lib/format";
import { CallDetailSkeleton } from "@/components/Skeleton";
import { WaveformPlayer, type WaveformPlayerHandle } from "@/components/WaveformPlayer";
import type { CallDetail, Check, CheckResult } from "@/types";

function formatTime(sec: number | null): string {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function describeRule(check: Check): string {
  const rc = check.rule_config as Record<string, unknown> | null;
  if (!rc) return "Правило не задано";

  const ruleType = rc.rule_type as string;
  const value = rc.value;
  const speaker = rc.speaker as string | undefined;

  const speakerLabel =
    speaker === "manager" ? "менеджера" : speaker === "client" ? "клиента" : "любого";

  switch (ruleType) {
    case "contains":
      return `Речь ${speakerLabel} содержит: «${value}»`;
    case "regex":
      return `Речь ${speakerLabel} соответствует шаблону: ${value}`;
    case "starts_with":
      return `Речь ${speakerLabel} начинается с: «${value}»`;
    case "min_turns":
      return `Минимум реплик: ${value}`;
    default:
      return `Правило: ${ruleType} = ${value}`;
  }
}

const infoTones = [
  {
    icon: <CalendarMonthIcon sx={{ fontSize: 20 }} />,
    bg: "linear-gradient(135deg, #FBFAFF 0%, #F2F0FE 100%)",
    ring: "#E5E2FC",
    iconColor: "#4F46E5",
    iconBg: "#EEEDFE",
  },
  {
    icon: <TimerIcon sx={{ fontSize: 20 }} />,
    bg: "linear-gradient(135deg, #F5FAFF 0%, #E3F0FE 100%)",
    ring: "#C4DDFB",
    iconColor: "#1D4ED8",
    iconBg: "#DBEAFE",
  },
  {
    icon: <BadgeIcon sx={{ fontSize: 20 }} />,
    bg: "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)",
    ring: "#C7EFDF",
    iconColor: "#047857",
    iconBg: "#D1FAE5",
  },
  {
    icon: <PhoneIcon sx={{ fontSize: 20 }} />,
    bg: "linear-gradient(135deg, #FFF8F8 0%, #FEEEEE 100%)",
    ring: "#FBCFCF",
    iconColor: "#B91C1C",
    iconBg: "#FEE2E2",
  },
  {
    icon: <ForumIcon sx={{ fontSize: 20 }} />,
    bg: "linear-gradient(135deg, #FFFBF2 0%, #FEF4DD 100%)",
    ring: "#FBE8B7",
    iconColor: "#B45309",
    iconBg: "#FEF3C7",
  },
];

function getClientPhone(call: { direction: string | null; from_number: string | null; to_number: string | null }): string {
  // outgoing: manager → client, то есть клиент = to_number
  // incoming / unknown: клиент = from_number
  const raw =
    call.direction === "outgoing"
      ? call.to_number ?? call.from_number
      : call.from_number ?? call.to_number;
  if (!raw) return "—";
  if (raw === "manual") return "Ручная загрузка";
  return raw;
}

export default function CallDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [call, setCall] = useState<CallDetail | null>(null);
  const [checks, setChecks] = useState<Check[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const playerRef = useRef<WaveformPlayerHandle | null>(null);
  const [currentTime, setCurrentTime] = useState(0);

  const [analyzeTaskId, setAnalyzeTaskId] = useState<string | null>(null);
  const [analyzeMsg, setAnalyzeMsg] = useState("");

  const { status: analyzeStatus } = useTaskStatus(analyzeTaskId, {
    intervalMs: 2000,
    onSuccess: async () => {
      try {
        const [callData, checksData] = await Promise.all([
          callsApi.get(id),
          checksApi.list(),
        ]);
        setCall(callData);
        setChecks(checksData);
        setAnalyzeMsg("Анализ завершён");
      } catch (e: unknown) {
        setAnalyzeMsg(`Не удалось обновить данные: ${e instanceof Error ? e.message : e}`);
      } finally {
        setAnalyzeTaskId(null);
      }
    },
    onFailure: (s) => {
      setAnalyzeMsg(`Ошибка анализа: ${s.error || "unknown"}`);
      setAnalyzeTaskId(null);
    },
  });

  const analyzing = analyzeTaskId !== null;

  const [expandedResults, setExpandedResults] = useState<Set<number>>(new Set());

  const toggleResult = (resultId: number) => {
    setExpandedResults((prev) => {
      const next = new Set(prev);
      if (next.has(resultId)) next.delete(resultId);
      else next.add(resultId);
      return next;
    });
  };

  useEffect(() => {
    Promise.all([callsApi.get(id), checksApi.list()])
      .then(([callData, checksData]) => {
        setCall(callData);
        setChecks(checksData);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const seekTo = useCallback((time: number) => {
    playerRef.current?.seekTo(time);
  }, []);

  const handleReanalyze = useCallback(async () => {
    setAnalyzeMsg("");
    try {
      const { task_id } = await callsApi.analyze(id);
      setAnalyzeTaskId(task_id);
    } catch (e: unknown) {
      setAnalyzeMsg(`Ошибка постановки в очередь: ${e instanceof Error ? e.message : e}`);
    }
  }, [id]);

  if (loading) {
    return <CallDetailSkeleton />;
  }

  if (error || !call) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => router.push("/calls")}
          sx={{ mb: 2 }}
        >
          Назад
        </Button>
        <Alert severity="error">{error || "Звонок не найден"}</Alert>
      </Box>
    );
  }

  const checkMap = new Map(checks.map((c) => [c.id, c]));

  const sortedTurns = [...call.turns].sort((a, b) => (a.t_start ?? 0) - (b.t_start ?? 0));

  const renderResultDetail = (result: CheckResult, check: Check | undefined) => {
    if (result.raw_response) {
      return (
        <Box sx={{ mt: 1.5, pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.75 }}>
            <SmartToyIcon sx={{ fontSize: 14, color: "primary.main" }} />
            <Typography
              sx={{ fontSize: 11, fontWeight: 600, color: "text.secondary", textTransform: "uppercase", letterSpacing: "0.05em" }}
            >
              Пояснение
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
            {result.raw_response}
          </Typography>
        </Box>
      );
    }

    if (check?.type === "rule_based") {
      return (
        <Box sx={{ mt: 1.5, pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.75 }}>
            <RuleIcon sx={{ fontSize: 14, color: "text.secondary" }} />
            <Typography
              sx={{ fontSize: 11, fontWeight: 600, color: "text.secondary", textTransform: "uppercase", letterSpacing: "0.05em" }}
            >
              Правило
            </Typography>
          </Box>
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            {describeRule(check)}
          </Typography>
        </Box>
      );
    }

    return null;
  };

  const infoItems = [
    { label: "Дата", value: formatDateTime(call.created_at) },
    { label: "Длительность", value: formatDuration(call.duration_sec) },
    { label: "Менеджер", value: call.manager_name || (call.manager_id ? `#${call.manager_id}` : "—") },
    { label: "Клиент", value: getClientPhone(call) },
    { label: "Реплик", value: String(call.turns.length) },
  ];

  return (
    <Box className="fade-in">
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          mb: 3,
          flexWrap: "wrap",
        }}
      >
        <IconButton
          onClick={() => router.push("/calls")}
          sx={{
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            "&:hover": { bgcolor: "surface.subtle" },
          }}
        >
          <ArrowBackIcon />
        </IconButton>
        <Box sx={{ flex: 1, minWidth: 200 }}>
          <Typography
            sx={{
              fontSize: 11,
              fontWeight: 600,
              color: "text.disabled",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Звонок
          </Typography>
          <Typography
            sx={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.2 }}
          >
            {call.id}
            {call.manager_name && (
              <Box
                component="span"
                sx={{ fontSize: 15, fontWeight: 500, color: "text.secondary", ml: 1.5 }}
              >
                · {call.manager_name}
              </Box>
            )}
          </Typography>
        </Box>
        <Chip
          label={statusLabels[call.status || ""] || call.status}
          color={statusColors[call.status || ""] || "default"}
        />
        <Button
          variant="outlined"
          size="small"
          startIcon={analyzing ? <CircularProgress size={14} /> : <ReplayIcon />}
          onClick={handleReanalyze}
          disabled={analyzing}
        >
          {analyzing ? "Анализ..." : "Проанализировать заново"}
        </Button>
      </Box>

      {analyzing && (
        <Card sx={{ mb: 2 }}>
          <CardContent sx={{ py: 2, "&:last-child": { pb: 2 } }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                {describeStep(analyzeStatus?.step)}
              </Typography>
              {(analyzeStatus?.percent ?? 0) > 0 && (
                <Typography sx={{ fontSize: 13, fontWeight: 600, color: "primary.dark" }}>
                  {analyzeStatus?.percent}%
                </Typography>
              )}
            </Box>
            {(analyzeStatus?.percent ?? 0) > 0 ? (
              <LinearProgress
                variant="determinate"
                value={analyzeStatus?.percent ?? 0}
                sx={{ "& .MuiLinearProgress-bar": { background: "var(--gradient-primary)" } }}
              />
            ) : (
              <LinearProgress
                sx={{ "& .MuiLinearProgress-bar": { background: "var(--gradient-primary)" } }}
              />
            )}
          </CardContent>
        </Card>
      )}

      {analyzeMsg && (
        <Alert
          severity={analyzeMsg.startsWith("Ошибка") ? "error" : "success"}
          sx={{ mb: 2 }}
          onClose={() => setAnalyzeMsg("")}
        >
          {analyzeMsg}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "repeat(2, 1fr)",
            sm: "repeat(3, 1fr)",
            md: "repeat(5, 1fr)",
          },
          gap: 2,
          mb: 3,
        }}
      >
        {infoItems.map((item, idx) => {
          const tone = infoTones[idx];
          return (
            <Card
              key={item.label}
              sx={{
                background: tone.bg,
                border: "1px solid",
                borderColor: tone.ring,
                height: "100%",
                animation: `fadeInUp 0.35s ease-out ${idx * 40}ms both`,
              }}
            >
              <CardContent sx={{ py: 2, px: 2, "&:last-child": { pb: 2 } }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                  <Avatar
                    variant="rounded"
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: tone.iconBg,
                      color: tone.iconColor,
                      borderRadius: 1.5,
                    }}
                  >
                    {tone.icon}
                  </Avatar>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography
                      sx={{
                        fontSize: 11,
                        color: "text.secondary",
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {item.label}
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: "text.primary",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        mt: 0.25,
                      }}
                    >
                      {item.value}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 7 }}>
          {call.audio_id && (
            <Card
              sx={{
                mb: 2.5,
                background: (t) =>
                  t.palette.mode === "dark"
                    ? "linear-gradient(135deg, rgba(99,91,255,0.10) 0%, rgba(139,85,255,0.08) 60%, rgba(236,72,153,0.06) 100%)"
                    : "linear-gradient(135deg, #FBFAFF 0%, #F2F0FE 60%, #FCE7F3 100%)",
                border: "1px solid",
                borderColor: (t) => (t.palette.mode === "dark" ? "divider" : "#E5E2FC"),
              }}
            >
              <CardContent sx={{ py: 2.5, "&:last-child": { pb: 2.5 } }}>
                <WaveformPlayer
                  ref={playerRef}
                  src={getAudioUrl(call.audio_id)}
                  onTimeUpdate={setCurrentTime}
                />
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <ForumIcon sx={{ color: "primary.main", fontSize: 20 }} />
                <Typography sx={{ fontSize: 16, fontWeight: 600 }}>
                  Транскрипция
                </Typography>
                {sortedTurns.length > 0 && (
                  <Chip
                    label={`${sortedTurns.length} реплик`}
                    size="small"
                    sx={{
                      ml: "auto",
                      bgcolor: "brand.violetTint",
                      color: "primary.dark",
                      fontWeight: 600,
                    }}
                  />
                )}
              </Box>

              {sortedTurns.length === 0 ? (
                <Box sx={{ textAlign: "center", py: 5 }}>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                    {call.status === "new"
                      ? "Звонок ещё не транскрибирован"
                      : "Реплик нет"}
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
                  {sortedTurns.map((turn) => {
                    const isManager = turn.speaker === "manager";
                    const isActive =
                      turn.t_start != null &&
                      turn.t_end != null &&
                      currentTime >= turn.t_start &&
                      currentTime <= turn.t_end;

                    return (
                      <Box
                        key={turn.id}
                        onClick={() => turn.t_start != null && seekTo(turn.t_start)}
                        sx={{
                          display: "flex",
                          gap: 1.5,
                          p: 1.5,
                          borderRadius: 2.5,
                          cursor: turn.t_start != null ? "pointer" : "default",
                          border: "1px solid",
                          borderColor: (t) => {
                            if (!isActive) return "transparent";
                            const isDark = t.palette.mode === "dark";
                            if (isManager)
                              return isDark ? "rgba(139,133,255,0.40)" : "#C4B5FD";
                            return isDark ? "rgba(248,113,113,0.30)" : "#FBCFCF";
                          },
                          bgcolor: (t) => {
                            if (!isActive) return "transparent";
                            const isDark = t.palette.mode === "dark";
                            if (isManager)
                              return isDark
                                ? "rgba(139,133,255,0.10)"
                                : "#F5F3FF";
                            return isDark
                              ? "rgba(248,113,113,0.08)"
                              : "#FFF8F8";
                          },
                          transition: "all 0.2s",
                          "&:hover": {
                            bgcolor: (t) =>
                              isManager
                                ? t.palette.mode === "dark"
                                  ? "rgba(139,133,255,0.06)"
                                  : "#FBFAFF"
                                : t.palette.surface.subtle,
                          },
                        }}
                      >
                        <Avatar
                          variant="rounded"
                          sx={{
                            width: 32,
                            height: 32,
                            bgcolor: isManager ? "brand.violetTint" : "brand.roseTint",
                            color: (t) => {
                              const isDark = t.palette.mode === "dark";
                              if (isManager) return isDark ? "#A5A0FF" : "#4F46E5";
                              return isDark ? "#FCA5A5" : "#B91C1C";
                            },
                            borderRadius: 1.5,
                            flexShrink: 0,
                          }}
                        >
                          {isManager ? (
                            <SupportAgentIcon sx={{ fontSize: 18 }} />
                          ) : (
                            <PersonIcon sx={{ fontSize: 18 }} />
                          )}
                        </Avatar>
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                              mb: 0.4,
                            }}
                          >
                            <Typography
                              sx={{
                                fontSize: 12,
                                fontWeight: 700,
                                color: isManager ? "primary.dark" : "error.dark",
                                textTransform: "uppercase",
                                letterSpacing: "0.04em",
                              }}
                            >
                              {isManager ? "Менеджер" : "Клиент"}
                            </Typography>
                            {turn.t_start != null && (
                              <Typography
                                sx={{
                                  fontSize: 11,
                                  color: "text.disabled",
                                  fontVariantNumeric: "tabular-nums",
                                }}
                              >
                                {formatTime(turn.t_start)}
                              </Typography>
                            )}
                          </Box>
                          <Typography
                            sx={{
                              fontSize: 13.5,
                              lineHeight: 1.5,
                              color: "text.primary",
                            }}
                          >
                            {turn.text}
                          </Typography>
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          {call.summary && (
            <Card
              sx={{
                mb: 2.5,
                background: (t) =>
                  t.palette.mode === "dark"
                    ? "linear-gradient(135deg, rgba(52,211,153,0.10) 0%, rgba(16,185,129,0.04) 100%)"
                    : "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)",
                border: "1px solid",
                borderColor: (t) =>
                  t.palette.mode === "dark" ? "rgba(52,211,153,0.25)" : "#C7EFDF",
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5 }}>
                  <Avatar
                    variant="rounded"
                    sx={{
                      width: 30,
                      height: 30,
                      bgcolor: "brand.tealTint",
                      color: (t) => (t.palette.mode === "dark" ? "#6EE7B7" : "#047857"),
                      borderRadius: 1.5,
                    }}
                  >
                    <SummarizeIcon sx={{ fontSize: 18 }} />
                  </Avatar>
                  <Typography sx={{ fontSize: 15, fontWeight: 600 }}>Резюме</Typography>
                </Box>
                <Typography sx={{ fontSize: 13.5, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>
                  {call.summary}
                </Typography>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                <ScienceIcon sx={{ color: "primary.main", fontSize: 20 }} />
                <Typography sx={{ fontSize: 16, fontWeight: 600, flex: 1 }}>
                  Проверки
                </Typography>
                <Tooltip title="Перейти к проверкам">
                  <IconButton size="small" onClick={() => router.push("/checks")}>
                    <OpenInNewIcon sx={{ fontSize: 18 }} />
                  </IconButton>
                </Tooltip>
              </Box>

              {call.results.length === 0 ? (
                <Typography
                  sx={{ fontSize: 13, color: "text.secondary", textAlign: "center", py: 3 }}
                >
                  {call.status === "analyzed"
                    ? "Проверок не было"
                    : "Звонок ещё не проанализирован"}
                </Typography>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                  {call.results.map((result) => {
                    const check = checkMap.get(result.check_id);
                    const passed = result.value_boolean === true;
                    const failed = result.value_boolean === false;
                    const isExpanded = expandedResults.has(result.id);
                    const hasDetail = !!result.raw_response || check?.type === "rule_based";

                    return (
                      <Box
                        key={result.id}
                        onClick={() => hasDetail && toggleResult(result.id)}
                        sx={{
                          p: 1.5,
                          borderRadius: 2.5,
                          border: "1px solid",
                          borderColor: (t) => {
                            const isDark = t.palette.mode === "dark";
                            if (failed) return isDark ? "rgba(248,113,113,0.30)" : "#FBCFCF";
                            if (passed) return isDark ? "rgba(52,211,153,0.30)" : "#C7EFDF";
                            return t.palette.divider;
                          },
                          background: (t) => {
                            const isDark = t.palette.mode === "dark";
                            if (failed)
                              return isDark
                                ? "linear-gradient(135deg, rgba(248,113,113,0.10) 0%, rgba(239,68,68,0.04) 100%)"
                                : "linear-gradient(135deg, #FFF8F8 0%, #FEEEEE 100%)";
                            if (passed)
                              return isDark
                                ? "linear-gradient(135deg, rgba(52,211,153,0.10) 0%, rgba(16,185,129,0.04) 100%)"
                                : "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)";
                            return "transparent";
                          },
                          cursor: hasDetail ? "pointer" : "default",
                          transition: "all 0.2s",
                          "&:hover": hasDetail ? { transform: "translateY(-1px)" } : {},
                        }}
                      >
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          {passed && (
                            <Avatar
                              sx={{
                                width: 24,
                                height: 24,
                                bgcolor: "brand.tealTint",
                                color: (t) =>
                                  t.palette.mode === "dark" ? "#6EE7B7" : "#047857",
                              }}
                            >
                              <CheckCircleIcon sx={{ fontSize: 14 }} />
                            </Avatar>
                          )}
                          {failed && (
                            <Avatar
                              sx={{
                                width: 24,
                                height: 24,
                                bgcolor: "brand.roseTint",
                                color: (t) =>
                                  t.palette.mode === "dark" ? "#FCA5A5" : "#B91C1C",
                              }}
                            >
                              <CancelIcon sx={{ fontSize: 14 }} />
                            </Avatar>
                          )}
                          {!passed && !failed && (
                            <Chip
                              icon={
                                check?.type === "llm_based" ? (
                                  <SmartToyIcon sx={{ fontSize: 12 }} />
                                ) : (
                                  <RuleIcon sx={{ fontSize: 12 }} />
                                )
                              }
                              label={check?.type === "llm_based" ? "LLM" : "Правило"}
                              size="small"
                              sx={{ height: 22, fontSize: 10.5 }}
                            />
                          )}
                          <Typography sx={{ fontSize: 13, fontWeight: 500, flex: 1 }}>
                            {check?.name || `Проверка #${result.check_id}`}
                          </Typography>
                          {result.value_score != null && (
                            <Chip
                              label={`${result.value_score}/10`}
                              size="small"
                              color={
                                result.value_score >= 7
                                  ? "success"
                                  : result.value_score >= 4
                                  ? "warning"
                                  : "error"
                              }
                            />
                          )}
                          {hasDetail && (
                            <ExpandMoreIcon
                              sx={{
                                fontSize: 18,
                                color: "text.secondary",
                                transform: isExpanded ? "rotate(180deg)" : "none",
                                transition: "transform 0.2s",
                              }}
                            />
                          )}
                        </Box>

                        {result.value_category && (
                          <Typography
                            sx={{ fontSize: 11.5, color: "text.secondary", mt: 0.5, ml: 4 }}
                          >
                            Категория: {result.value_category}
                          </Typography>
                        )}

                        {check?.description && (
                          <Typography
                            sx={{ fontSize: 11.5, color: "text.secondary", mt: 0.5, ml: 4 }}
                          >
                            {check.description}
                          </Typography>
                        )}

                        <Collapse in={isExpanded}>{renderResultDetail(result, check)}</Collapse>
                      </Box>
                    );
                  })}
                </Box>
              )}
            </CardContent>
          </Card>

          {call.transcript && sortedTurns.length === 0 && (
            <Card sx={{ mt: 2.5 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography sx={{ fontSize: 15, fontWeight: 600, mb: 1.5 }}>
                  Транскрипт (сырой)
                </Typography>
                <Typography sx={{ fontSize: 13, whiteSpace: "pre-wrap", lineHeight: 1.7 }}>
                  {call.transcript}
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
