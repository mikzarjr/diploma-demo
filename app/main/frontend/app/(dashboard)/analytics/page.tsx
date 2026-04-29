"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
  Alert,
  Chip,
  Grid,
  LinearProgress,
  Tooltip,
  Avatar,
  Button,
} from "@mui/material";
import BarChartIcon from "@mui/icons-material/BarChartOutlined";
import ChecklistIcon from "@mui/icons-material/ChecklistOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelIcon from "@mui/icons-material/CancelOutlined";
import RuleIcon from "@mui/icons-material/RuleOutlined";
import SmartToyIcon from "@mui/icons-material/SmartToyOutlined";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalkOutlined";
import VerifiedIcon from "@mui/icons-material/VerifiedOutlined";
import InsightsIcon from "@mui/icons-material/InsightsOutlined";
import EmojiEventsIcon from "@mui/icons-material/EmojiEventsOutlined";
import { analyticsApi } from "@/lib/api";
import type { ManagerStatsResponse, CheckStatsResponse } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { useTableSort, SortableCell } from "@/hooks/useTableSort";
import { StatCardsSkeleton, TableSkeleton } from "@/components/Skeleton";
import { downloadCsv } from "@/lib/csvExport";
import FileDownloadIcon from "@mui/icons-material/FileDownloadOutlined";

type ManagerSortKey = "manager" | "total_calls" | "error_calls" | "avg_duration" | "checks_total" | "pass_rate";
type CheckSortKey = "name" | "type" | "total_runs" | "passed" | "failed" | "pass_rate" | "avg_score" | "active";

interface Tone {
  bg: string;
  ring: string;
  icon: string;
  iconBg: string;
}

const tones: Record<string, Tone> = {
  violet: {
    bg: "linear-gradient(135deg, #FBFAFF 0%, #F2F0FE 100%)",
    ring: "#E5E2FC",
    icon: "#4F46E5",
    iconBg: "#EEEDFE",
  },
  teal: {
    bg: "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)",
    ring: "#C7EFDF",
    icon: "#047857",
    iconBg: "#D1FAE5",
  },
  amber: {
    bg: "linear-gradient(135deg, #FFFBF2 0%, #FEF4DD 100%)",
    ring: "#FBE8B7",
    icon: "#B45309",
    iconBg: "#FEF3C7",
  },
  sky: {
    bg: "linear-gradient(135deg, #F5FAFF 0%, #E3F0FE 100%)",
    ring: "#C4DDFB",
    icon: "#1D4ED8",
    iconBg: "#DBEAFE",
  },
  rose: {
    bg: "linear-gradient(135deg, #FFF8F8 0%, #FEEEEE 100%)",
    ring: "#FBCFCF",
    icon: "#B91C1C",
    iconBg: "#FEE2E2",
  },
};

export default function AnalyticsPage() {
  const router = useRouter();
  const [managerStats, setManagerStats] = useState<ManagerStatsResponse[]>([]);
  const [checkStats, setCheckStats] = useState<CheckStatsResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([analyticsApi.managerStats(), analyticsApi.checkStats()])
      .then(([managers, checks]) => {
        setManagerStats(managers);
        setCheckStats(checks);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const managerSort = useTableSort<ManagerStatsResponse, ManagerSortKey>(managerStats, {
    manager: (m) => m.manager_name,
    total_calls: (m) => m.total_calls,
    error_calls: (m) => m.error_calls,
    avg_duration: (m) => m.avg_duration,
    checks_total: (m) => m.total_checks,
    pass_rate: (m) => m.check_pass_rate,
  });
  const sortedManagers = managerSort.sorted;

  const checkSort = useTableSort<CheckStatsResponse, CheckSortKey>(checkStats, {
    name: (c) => c.name,
    type: (c) => c.type,
    total_runs: (c) => c.total_runs,
    passed: (c) => c.passed,
    failed: (c) => c.failed,
    pass_rate: (c) => c.pass_rate,
    avg_score: (c) => c.avg_score,
    active: (c) => (c.active ? 1 : 0),
  });

  const exportManagers = () => {
    downloadCsv("analytics-managers", managerSort.sorted, [
      { header: "ID менеджера", value: (m) => m.manager_id },
      { header: "Менеджер", value: (m) => m.manager_name },
      { header: "Звонки", value: (m) => m.total_calls },
      { header: "Проанализированных", value: (m) => m.analyzed_calls },
      { header: "Ошибок", value: (m) => m.error_calls },
      { header: "Ср. длительность (сек)", value: (m) => m.avg_duration?.toFixed(1) ?? "" },
      { header: "Пройдено проверок", value: (m) => m.passed_checks },
      { header: "Не пройдено", value: (m) => m.failed_checks },
      {
        header: "% прохождения",
        value: (m) => (m.check_pass_rate !== null ? (m.check_pass_rate * 100).toFixed(1) : ""),
      },
      { header: "Ср. балл", value: (m) => m.avg_score?.toFixed(2) ?? "" },
    ]);
  };

  const exportChecks = () => {
    downloadCsv("analytics-checks", checkSort.sorted, [
      { header: "ID", value: (c) => c.check_id },
      { header: "Название", value: (c) => c.name },
      { header: "Тип", value: (c) => c.type },
      { header: "Формат", value: (c) => c.output_type },
      { header: "Активна", value: (c) => (c.active ? "да" : "нет") },
      { header: "Запусков", value: (c) => c.total_runs },
      { header: "Пройдено", value: (c) => c.passed },
      { header: "Не пройдено", value: (c) => c.failed },
      {
        header: "% прохождения",
        value: (c) => (c.pass_rate !== null ? (c.pass_rate * 100).toFixed(1) : ""),
      },
      { header: "Ср. балл", value: (c) => c.avg_score?.toFixed(2) ?? "" },
    ]);
  };
  const sortedChecks = checkSort.sorted;

  if (loading) {
    return (
      <Box className="fade-in">
        <StatCardsSkeleton count={4} />
        <Box sx={{ mb: 3 }}>
          <TableSkeleton rows={6} cols={6} />
        </Box>
        <TableSkeleton rows={6} cols={8} />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  const totalCalls = managerStats.reduce((s, m) => s + m.total_calls, 0);
  const totalAnalyzed = managerStats.reduce((s, m) => s + m.analyzed_calls, 0);
  const totalChecksRun = managerStats.reduce((s, m) => s + m.total_checks, 0);
  const totalPassed = managerStats.reduce((s, m) => s + m.passed_checks, 0);
  const totalFailed = managerStats.reduce((s, m) => s + m.failed_checks, 0);
  const overallPassRate =
    totalPassed + totalFailed > 0
      ? Math.round((totalPassed / (totalPassed + totalFailed)) * 100)
      : null;

  const topManager = [...managerStats]
    .filter((m) => m.check_pass_rate != null)
    .sort((a, b) => (b.check_pass_rate ?? 0) - (a.check_pass_rate ?? 0))[0];

  const statCards = [
    {
      title: "Всего звонков",
      value: totalCalls,
      subtitle: totalAnalyzed > 0 ? `${totalAnalyzed} проанализировано` : "Нет данных",
      icon: <PhoneInTalkIcon />,
      tone: "violet",
    },
    {
      title: "Проверок выполнено",
      value: totalChecksRun,
      subtitle: totalChecksRun > 0 ? `${totalPassed} пройдено` : "Пусто",
      icon: <VerifiedIcon />,
      tone: "teal",
    },
    {
      title: "Процент качества",
      value: overallPassRate != null ? `${overallPassRate}%` : "—",
      subtitle:
        overallPassRate != null
          ? overallPassRate >= 70
            ? "Отличные показатели"
            : overallPassRate >= 40
            ? "Есть над чем работать"
            : "Требует внимания"
          : "Нет проверок",
      icon: <InsightsIcon />,
      tone:
        overallPassRate == null
          ? "sky"
          : overallPassRate >= 70
          ? "teal"
          : overallPassRate >= 40
          ? "amber"
          : "rose",
    },
    {
      title: "Лидер качества",
      value: topManager?.manager_name || "—",
      subtitle: topManager?.check_pass_rate != null ? `${Math.round(topManager.check_pass_rate)}% прохождения` : "Нет данных",
      icon: <EmojiEventsIcon />,
      tone: "amber",
    },
  ] as const;

  const maxCalls = Math.max(1, ...managerStats.map((m) => m.total_calls));

  return (
    <Box className="fade-in">
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {statCards.map((stat, idx) => {
          const tone = tones[stat.tone];
          return (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={stat.title}>
              <Card
                sx={{
                  height: "100%",
                  background: tone.bg,
                  border: "1px solid",
                  borderColor: tone.ring,
                  transition: "all 0.25s ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 12px 24px -12px rgba(28,25,23,0.12)",
                  },
                  animation: `fadeInUp 0.4s ease-out ${idx * 60}ms both`,
                }}
              >
                <CardContent sx={{ p: 2.5 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      mb: 1.5,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: 12.5,
                        fontWeight: 600,
                        color: "text.secondary",
                      }}
                    >
                      {stat.title}
                    </Typography>
                    <Avatar
                      variant="rounded"
                      sx={{
                        bgcolor: tone.iconBg,
                        color: tone.icon,
                        width: 36,
                        height: 36,
                        borderRadius: 2,
                      }}
                    >
                      {stat.icon}
                    </Avatar>
                  </Box>
                  <Typography
                    sx={{
                      fontSize: typeof stat.value === "string" && stat.value.length > 10 ? 18 : 26,
                      fontWeight: 700,
                      lineHeight: 1.1,
                      letterSpacing: "-0.02em",
                      color: "text.primary",
                      fontVariantNumeric: "tabular-nums",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {stat.value}
                  </Typography>
                  <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>
                    {stat.subtitle}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2.5 }}>
            <BarChartIcon sx={{ color: "primary.main", fontSize: 20 }} />
            <Typography sx={{ fontSize: 16, fontWeight: 600 }}>
              Объём звонков по менеджерам
            </Typography>
          </Box>

          {managerStats.length === 0 ? (
            <Box sx={{ textAlign: "center", py: 4 }}>
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                Нет данных — загрузите звонки с привязкой к менеджеру
              </Typography>
            </Box>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1.75 }}>
              {managerStats.slice(0, 10).map((m, idx) => {
                const pct = (m.total_calls / maxCalls) * 100;
                const passRate = m.check_pass_rate;
                const barColor =
                  passRate == null
                    ? "#635BFF"
                    : passRate >= 70
                    ? "#10B981"
                    : passRate >= 40
                    ? "#F59E0B"
                    : "#EF4444";
                return (
                  <Box
                    key={m.manager_id}
                    onClick={() => router.push(`/calls?manager=${m.manager_id}`)}
                    sx={{
                      cursor: "pointer",
                      px: 1.5,
                      py: 1.25,
                      borderRadius: 2,
                      border: "1px solid transparent",
                      transition: "all 0.2s",
                      "&:hover": {
                        borderColor: "divider",
                        bgcolor: "surface.subtle",
                      },
                      animation: `fadeInUp 0.35s ease-out ${idx * 40}ms both`,
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        mb: 0.75,
                      }}
                    >
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Avatar
                          sx={{
                            width: 26,
                            height: 26,
                            fontSize: 11,
                            bgcolor: "brand.violetTint",
                            color: "primary.dark",
                            fontWeight: 600,
                          }}
                        >
                          {m.manager_name?.[0]?.toUpperCase()}
                        </Avatar>
                        <Typography sx={{ fontSize: 13.5, fontWeight: 500 }}>
                          {m.manager_name}
                        </Typography>
                      </Box>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                        <Typography
                          sx={{
                            fontSize: 13,
                            fontWeight: 600,
                            color: "text.primary",
                            fontVariantNumeric: "tabular-nums",
                          }}
                        >
                          {m.total_calls} звонков
                        </Typography>
                        {passRate != null && (
                          <Chip
                            label={`${Math.round(passRate)}%`}
                            size="small"
                            sx={{
                              height: 20,
                              fontSize: 11,
                              fontWeight: 600,
                              bgcolor:
                                passRate >= 70
                                  ? "#D1FAE5"
                                  : passRate >= 40
                                  ? "#FEF3C7"
                                  : "#FEE2E2",
                              color:
                                passRate >= 70
                                  ? "#047857"
                                  : passRate >= 40
                                  ? "#B45309"
                                  : "#B91C1C",
                            }}
                          />
                        )}
                      </Box>
                    </Box>
                    <Box
                      sx={{
                        height: 8,
                        borderRadius: 999,
                        bgcolor: "surface.muted",
                        overflow: "hidden",
                      }}
                    >
                      <Box
                        sx={{
                          height: "100%",
                          width: `${pct}%`,
                          borderRadius: 999,
                          background: `linear-gradient(90deg, ${barColor}40 0%, ${barColor} 100%)`,
                          transition: "width 0.6s cubic-bezier(0.22, 1, 0.36, 1)",
                        }}
                      />
                    </Box>
                  </Box>
                );
              })}
            </Box>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 1,
              mb: 2,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <InsightsIcon sx={{ color: "primary.main", fontSize: 20 }} />
              <Typography sx={{ fontSize: 16, fontWeight: 600 }}>
                Детали по менеджерам
              </Typography>
            </Box>
            <Tooltip title="Скачать CSV" arrow>
              <span>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<FileDownloadIcon />}
                  onClick={exportManagers}
                  disabled={managerStats.length === 0}
                >
                  CSV
                </Button>
              </span>
            </Tooltip>
          </Box>

          {managerStats.length === 0 ? (
            <Typography sx={{ fontSize: 13, color: "text.secondary", textAlign: "center", py: 4 }}>
              Нет данных
            </Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <SortableCell sortKey="manager" sort={managerSort}>Менеджер</SortableCell>
                    <SortableCell sortKey="total_calls" sort={managerSort} align="center">Звонки</SortableCell>
                    <SortableCell sortKey="error_calls" sort={managerSort} align="center">Ошибки</SortableCell>
                    <SortableCell sortKey="avg_duration" sort={managerSort}>Ср. длительность</SortableCell>
                    <SortableCell sortKey="checks_total" sort={managerSort} align="center">
                      <Tooltip title="Пройдено / Не пройдено проверок" arrow>
                        <span>Проверки</span>
                      </Tooltip>
                    </SortableCell>
                    <SortableCell sortKey="pass_rate" sort={managerSort}>% прохождения</SortableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedManagers.map((stat) => (
                    <TableRow
                      key={stat.manager_id}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => router.push(`/calls?manager=${stat.manager_id}`)}
                    >
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Avatar
                            sx={{
                              width: 26,
                              height: 26,
                              fontSize: 11,
                              bgcolor: "brand.violetTint",
                              color: "primary.dark",
                              fontWeight: 600,
                            }}
                          >
                            {stat.manager_name?.[0]?.toUpperCase()}
                          </Avatar>
                          <Typography sx={{ fontSize: 13, fontWeight: 500 }}>
                            {stat.manager_name}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="center">
                        <Typography sx={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                          {stat.total_calls}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        {stat.error_calls > 0 ? (
                          <Chip label={stat.error_calls} size="small" color="error" />
                        ) : (
                          <Typography sx={{ fontSize: 13, color: "text.disabled" }}>0</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Typography sx={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                          {stat.avg_duration > 0 ? formatDuration(stat.avg_duration) : "—"}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        {stat.total_checks > 0 ? (
                          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0.5 }}>
                            <Chip
                              icon={<CheckCircleIcon sx={{ fontSize: 13 }} />}
                              label={stat.passed_checks}
                              size="small"
                              color="success"
                            />
                            <Chip
                              icon={<CancelIcon sx={{ fontSize: 13 }} />}
                              label={stat.failed_checks}
                              size="small"
                              color="error"
                            />
                          </Box>
                        ) : (
                          <Typography sx={{ fontSize: 12, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {stat.check_pass_rate != null ? (
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            {stat.check_pass_rate >= 70 ? (
                              <TrendingUpIcon sx={{ fontSize: 16, color: "success.main" }} />
                            ) : (
                              <TrendingDownIcon sx={{ fontSize: 16, color: "error.main" }} />
                            )}
                            <LinearProgress
                              variant="determinate"
                              value={stat.check_pass_rate}
                              sx={{
                                flex: 1,
                                height: 6,
                                borderRadius: 999,
                              }}
                              color={
                                stat.check_pass_rate >= 70
                                  ? "success"
                                  : stat.check_pass_rate >= 40
                                  ? "warning"
                                  : "error"
                              }
                            />
                            <Typography
                              sx={{
                                fontSize: 12,
                                minWidth: 36,
                                textAlign: "right",
                                fontVariantNumeric: "tabular-nums",
                                fontWeight: 600,
                              }}
                            >
                              {Math.round(stat.check_pass_rate)}%
                            </Typography>
                          </Box>
                        ) : (
                          <Typography sx={{ fontSize: 12, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ p: 3 }}>
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 1,
              mb: 2,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <ChecklistIcon sx={{ color: "primary.main", fontSize: 20 }} />
              <Typography sx={{ fontSize: 16, fontWeight: 600 }}>
                Эффективность проверок
              </Typography>
            </Box>
            <Tooltip title="Скачать CSV" arrow>
              <span>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<FileDownloadIcon />}
                  onClick={exportChecks}
                  disabled={checkStats.length === 0}
                >
                  CSV
                </Button>
              </span>
            </Tooltip>
          </Box>

          {checkStats.length === 0 ? (
            <Typography sx={{ fontSize: 13, color: "text.secondary", textAlign: "center", py: 4 }}>
              Нет проверок — создайте их в разделе «Проверки»
            </Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <SortableCell sortKey="name" sort={checkSort}>Проверка</SortableCell>
                    <SortableCell sortKey="type" sort={checkSort} align="center">Тип</SortableCell>
                    <SortableCell sortKey="total_runs" sort={checkSort} align="center">Запусков</SortableCell>
                    <SortableCell sortKey="passed" sort={checkSort} align="center">Пройдено</SortableCell>
                    <SortableCell sortKey="failed" sort={checkSort} align="center">Не пройдено</SortableCell>
                    <SortableCell sortKey="pass_rate" sort={checkSort}>% прохождения</SortableCell>
                    <SortableCell sortKey="avg_score" sort={checkSort} align="center">Ср. балл</SortableCell>
                    <SortableCell sortKey="active" sort={checkSort} align="center">Статус</SortableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedChecks.map((stat) => (
                    <TableRow key={stat.check_id} hover>
                      <TableCell>
                        <Typography sx={{ fontSize: 13, fontWeight: 500 }}>{stat.name}</Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          icon={
                            stat.type === "llm_based" ? (
                              <SmartToyIcon sx={{ fontSize: 13 }} />
                            ) : (
                              <RuleIcon sx={{ fontSize: 13 }} />
                            )
                          }
                          label={stat.type === "llm_based" ? "LLM" : "Правило"}
                          size="small"
                          color={stat.type === "llm_based" ? "primary" : "default"}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Typography sx={{ fontSize: 13, fontVariantNumeric: "tabular-nums" }}>
                          {stat.total_runs}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography sx={{ fontSize: 13, color: "success.main", fontWeight: 600 }}>
                          {stat.passed}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Typography
                          sx={{
                            fontSize: 13,
                            color: stat.failed > 0 ? "error.main" : "text.disabled",
                            fontWeight: 600,
                          }}
                        >
                          {stat.failed}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {stat.pass_rate != null ? (
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                            <LinearProgress
                              variant="determinate"
                              value={stat.pass_rate}
                              sx={{ flex: 1, height: 6, borderRadius: 999 }}
                              color={
                                stat.pass_rate >= 70
                                  ? "success"
                                  : stat.pass_rate >= 40
                                  ? "warning"
                                  : "error"
                              }
                            />
                            <Typography
                              sx={{
                                fontSize: 12,
                                minWidth: 36,
                                textAlign: "right",
                                fontVariantNumeric: "tabular-nums",
                                fontWeight: 600,
                              }}
                            >
                              {Math.round(stat.pass_rate)}%
                            </Typography>
                          </Box>
                        ) : (
                          <Typography sx={{ fontSize: 12, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        {stat.avg_score != null ? (
                          <Chip
                            label={stat.avg_score.toFixed(1)}
                            size="small"
                            color={
                              stat.avg_score >= 7
                                ? "success"
                                : stat.avg_score >= 4
                                ? "warning"
                                : "error"
                            }
                          />
                        ) : (
                          <Typography sx={{ fontSize: 12, color: "text.disabled" }}>—</Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={stat.active ? "Активна" : "Выкл"}
                          size="small"
                          color={stat.active ? "success" : "default"}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
