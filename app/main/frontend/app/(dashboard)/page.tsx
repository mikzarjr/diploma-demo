"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Chip,
  List,
  ListItemButton,
  ListItemText,
  LinearProgress,
  Button,
  Avatar,
  useTheme,
} from "@mui/material";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalkOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined";
import TimerIcon from "@mui/icons-material/TimerOutlined";
import ErrorIcon from "@mui/icons-material/ErrorOutlineOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { callsApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { statusLabels, statusColors } from "@/lib/status";
import { formatDuration, formatRelative } from "@/lib/format";
import { StatCardsSkeleton, DetailCardSkeleton, Shimmer } from "@/components/Skeleton";
import type { Call } from "@/types";

interface StatCard {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  tone: "violet" | "teal" | "amber" | "rose" | "sky";
  delta?: number;
}

type ToneStyle = { bg: string; ring: string; icon: string; iconBg: string; accent: string };

const lightToneStyles: Record<StatCard["tone"], ToneStyle> = {
  violet: {
    bg: "linear-gradient(135deg, #FBFAFF 0%, #F2F0FE 100%)",
    ring: "#E5E2FC",
    icon: "#4F46E5",
    iconBg: "#EEEDFE",
    accent: "#635BFF",
  },
  teal: {
    bg: "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)",
    ring: "#C7EFDF",
    icon: "#047857",
    iconBg: "#D1FAE5",
    accent: "#10B981",
  },
  amber: {
    bg: "linear-gradient(135deg, #FFFBF2 0%, #FEF4DD 100%)",
    ring: "#FBE8B7",
    icon: "#B45309",
    iconBg: "#FEF3C7",
    accent: "#F59E0B",
  },
  rose: {
    bg: "linear-gradient(135deg, #FFF8F8 0%, #FEEEEE 100%)",
    ring: "#FBCFCF",
    icon: "#B91C1C",
    iconBg: "#FEE2E2",
    accent: "#EF4444",
  },
  sky: {
    bg: "linear-gradient(135deg, #F5FAFF 0%, #E3F0FE 100%)",
    ring: "#C4DDFB",
    icon: "#1D4ED8",
    iconBg: "#DBEAFE",
    accent: "#3B82F6",
  },
};

const darkToneStyles: Record<StatCard["tone"], ToneStyle> = {
  violet: {
    bg: "linear-gradient(135deg, rgba(99,91,255,0.10) 0%, rgba(99,91,255,0.04) 100%)",
    ring: "rgba(139,133,255,0.30)",
    icon: "#A5A0FF",
    iconBg: "#2B2560",
    accent: "#8B85FF",
  },
  teal: {
    bg: "linear-gradient(135deg, rgba(52,211,153,0.10) 0%, rgba(16,185,129,0.04) 100%)",
    ring: "rgba(52,211,153,0.30)",
    icon: "#6EE7B7",
    iconBg: "#0F3B2E",
    accent: "#34D399",
  },
  amber: {
    bg: "linear-gradient(135deg, rgba(251,191,36,0.10) 0%, rgba(245,158,11,0.04) 100%)",
    ring: "rgba(251,191,36,0.30)",
    icon: "#FCD34D",
    iconBg: "#3D2A0B",
    accent: "#FBBF24",
  },
  rose: {
    bg: "linear-gradient(135deg, rgba(248,113,113,0.10) 0%, rgba(239,68,68,0.04) 100%)",
    ring: "rgba(248,113,113,0.30)",
    icon: "#FCA5A5",
    iconBg: "#3F1717",
    accent: "#F87171",
  },
  sky: {
    bg: "linear-gradient(135deg, rgba(96,165,250,0.10) 0%, rgba(59,130,246,0.04) 100%)",
    ring: "rgba(96,165,250,0.30)",
    icon: "#93C5FD",
    iconBg: "#0F2A4D",
    accent: "#60A5FA",
  },
};

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const theme = useTheme();
  const toneStyles = theme.palette.mode === "dark" ? darkToneStyles : lightToneStyles;
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    callsApi
      .list({ limit: 200 })
      .then(setCalls)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box className="fade-in">
        <Box sx={{ mb: 3 }}>
          <Shimmer width={140} height={12} sx={{ mb: 0.75 }} />
          <Shimmer width={320} height={26} />
        </Box>
        <StatCardsSkeleton count={4} />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "7fr 5fr" },
            gap: 2.5,
          }}
        >
          <DetailCardSkeleton height={260} />
          <DetailCardSkeleton height={260} />
        </Box>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Ошибка загрузки: {error}</Alert>;
  }

  const totalCalls = calls.length;
  const analyzedCalls = calls.filter((c) => c.status === "analyzed").length;
  const errorCalls = calls.filter((c) => c.status === "error").length;
  const inProgressCalls = calls.filter((c) =>
    ["queued", "transcribing", "analyzing"].includes(c.status || "")
  ).length;

  const callsWithDuration = calls.filter((c) => c.duration_sec && c.duration_sec > 0);
  const avgDuration =
    callsWithDuration.length > 0
      ? callsWithDuration.reduce((sum, c) => sum + (c.duration_sec || 0), 0) /
        callsWithDuration.length
      : 0;

  const analyzeRate = totalCalls > 0 ? Math.round((analyzedCalls / totalCalls) * 100) : 0;

  const recentCalls = calls.slice(0, 6);

  const statusCounts: Record<string, number> = {};
  calls.forEach((c) => {
    const s = c.status || "unknown";
    statusCounts[s] = (statusCounts[s] || 0) + 1;
  });

  const stats: StatCard[] = [
    {
      title: "Всего звонков",
      value: totalCalls,
      subtitle: totalCalls > 0 ? `${inProgressCalls} в обработке` : "Пока пусто",
      icon: <PhoneInTalkIcon />,
      tone: "violet",
    },
    {
      title: "Проанализировано",
      value: analyzedCalls,
      subtitle: totalCalls > 0 ? `${analyzeRate}% от общего числа` : "—",
      icon: <CheckCircleIcon />,
      tone: "teal",
    },
    {
      title: "Средняя длительность",
      value: avgDuration > 0 ? formatDuration(avgDuration) : "—",
      subtitle:
        callsWithDuration.length > 0
          ? `По ${callsWithDuration.length} звонкам`
          : "Нет данных",
      icon: <TimerIcon />,
      tone: "sky",
    },
    {
      title: "Ошибки",
      value: errorCalls,
      subtitle: errorCalls > 0 ? "Требуют внимания" : "Всё в порядке",
      icon: <ErrorIcon />,
      tone: errorCalls > 0 ? "rose" : "amber",
    },
  ];

  const hour = new Date().getHours();
  const greeting =
    hour < 6 ? "Доброй ночи" : hour < 12 ? "Доброе утро" : hour < 18 ? "Добрый день" : "Добрый вечер";

  return (
    <Box className="fade-in">
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          mb: 3,
          flexWrap: "wrap",
        }}
      >
        <Box>
          <Typography
            sx={{
              fontSize: 13,
              fontWeight: 500,
              color: "text.secondary",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Добро пожаловать
          </Typography>
          <Typography
            sx={{
              fontSize: 24,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "text.primary",
              mt: 0.25,
            }}
          >
            {greeting}
            {user?.name ? `, ${user.name}` : ""}
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        {stats.map((stat, idx) => {
          const style = toneStyles[stat.tone];
          return (
            <Grid size={{ xs: 12, sm: 6, md: 3 }} key={stat.title}>
              <Card
                sx={{
                  height: "100%",
                  background: style.bg,
                  border: "1px solid",
                  borderColor: style.ring,
                  position: "relative",
                  overflow: "hidden",
                  transition: "all 0.25s ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "elevation.md",
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
                      mb: 2,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: 12.5,
                        fontWeight: 600,
                        color: "text.secondary",
                        letterSpacing: "-0.005em",
                      }}
                    >
                      {stat.title}
                    </Typography>
                    <Avatar
                      variant="rounded"
                      sx={{
                        bgcolor: style.iconBg,
                        color: style.icon,
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
                      fontSize: 28,
                      fontWeight: 700,
                      lineHeight: 1.1,
                      letterSpacing: "-0.02em",
                      color: "text.primary",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {stat.value}
                  </Typography>
                  <Typography
                    sx={{
                      fontSize: 12,
                      color: "text.secondary",
                      mt: 0.5,
                    }}
                  >
                    {stat.subtitle}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {totalCalls > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                mb: 1.5,
              }}
            >
              <Box>
                <Typography sx={{ fontSize: 15, fontWeight: 600, color: "text.primary" }}>
                  Прогресс анализа
                </Typography>
                <Typography sx={{ fontSize: 12.5, color: "text.secondary", mt: 0.25 }}>
                  Из {totalCalls} звонков обработано {analyzedCalls}
                </Typography>
              </Box>
              <Typography
                sx={{
                  fontSize: 24,
                  fontWeight: 700,
                  letterSpacing: "-0.02em",
                  color: "primary.dark",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {analyzeRate}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={analyzeRate}
              sx={{
                height: 8,
                borderRadius: 999,
                bgcolor: "surface.muted",
                "& .MuiLinearProgress-bar": {
                  background: "var(--gradient-primary)",
                },
              }}
            />
          </CardContent>
        </Card>
      )}

      <Grid container spacing={2.5}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  mb: 2,
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <TrendingUpIcon sx={{ color: "primary.main", fontSize: 20 }} />
                  <Typography sx={{ fontSize: 15, fontWeight: 600 }}>
                    Последние звонки
                  </Typography>
                </Box>
                <Button
                  size="small"
                  endIcon={<ArrowForwardIcon />}
                  onClick={() => router.push("/calls")}
                  sx={{ fontSize: 12.5 }}
                >
                  Все звонки
                </Button>
              </Box>

              {recentCalls.length === 0 ? (
                <Box
                  sx={{
                    py: 5,
                    textAlign: "center",
                    border: "1px dashed",
                    borderColor: "divider",
                    borderRadius: 2,
                    bgcolor: "surface.subtle",
                  }}
                >
                  <PhoneInTalkIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
                  <Typography sx={{ fontSize: 14, fontWeight: 500, color: "text.secondary" }}>
                    Звонков пока нет
                  </Typography>
                  <Typography sx={{ fontSize: 12.5, color: "text.disabled", mt: 0.5 }}>
                    Загрузите первый звонок в разделе «Загрузка»
                  </Typography>
                </Box>
              ) : (
                <List disablePadding>
                  {recentCalls.map((call) => {
                    const color = statusColors[call.status || ""] || "default";
                    return (
                      <ListItemButton
                        key={call.id}
                        onClick={() => router.push(`/calls/${call.id}`)}
                        sx={{
                          borderRadius: 2,
                          mb: 0.5,
                          px: 1.5,
                          py: 1.25,
                          border: "1px solid transparent",
                          "&:hover": {
                            bgcolor: "surface.subtle",
                            borderColor: "divider",
                          },
                        }}
                      >
                        <Avatar
                          variant="rounded"
                          sx={{
                            width: 36,
                            height: 36,
                            bgcolor: "brand.violetTint",
                            color: "primary.dark",
                            mr: 1.5,
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          #{call.id}
                        </Avatar>
                        <ListItemText
                          primary={
                            <Typography sx={{ fontSize: 13.5, fontWeight: 500 }}>
                              {call.manager_name || "Без менеджера"}
                            </Typography>
                          }
                          secondary={
                            <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                              {formatRelative(call.created_at)}
                              {call.duration_sec ? ` · ${formatDuration(call.duration_sec)}` : ""}
                            </Typography>
                          }
                        />
                        <Chip
                          label={statusLabels[call.status || ""] || call.status}
                          color={color}
                          size="small"
                        />
                      </ListItemButton>
                    );
                  })}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Typography sx={{ fontSize: 15, fontWeight: 600, mb: 2 }}>
                По статусам
              </Typography>

              {totalCalls === 0 ? (
                <Box sx={{ py: 5, textAlign: "center" }}>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                    Нет данных
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {Object.entries(statusCounts)
                    .sort(([, a], [, b]) => b - a)
                    .map(([status, count]) => {
                      const percent = Math.round((count / totalCalls) * 100);
                      const color =
                        status === "analyzed"
                          ? "success.main"
                          : status === "error"
                          ? "error.main"
                          : ["queued", "transcribing", "analyzing", "transcribed"].includes(status)
                          ? "info.main"
                          : "grey.400";
                      return (
                        <Box key={status}>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              mb: 0.75,
                            }}
                          >
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                              <Box
                                sx={{
                                  width: 8,
                                  height: 8,
                                  borderRadius: "50%",
                                  bgcolor: color,
                                }}
                              />
                              <Typography sx={{ fontSize: 13, fontWeight: 500 }}>
                                {statusLabels[status] || status}
                              </Typography>
                            </Box>
                            <Box sx={{ display: "flex", gap: 1, alignItems: "baseline" }}>
                              <Typography
                                sx={{
                                  fontSize: 13,
                                  fontWeight: 600,
                                  color: "text.primary",
                                  fontVariantNumeric: "tabular-nums",
                                }}
                              >
                                {count}
                              </Typography>
                              <Typography
                                sx={{
                                  fontSize: 11.5,
                                  color: "text.disabled",
                                  fontVariantNumeric: "tabular-nums",
                                }}
                              >
                                {percent}%
                              </Typography>
                            </Box>
                          </Box>
                          <Box
                            sx={{
                              height: 6,
                              borderRadius: 999,
                              bgcolor: "surface.muted",
                              overflow: "hidden",
                            }}
                          >
                            <Box
                              sx={{
                                height: "100%",
                                width: `${percent}%`,
                                borderRadius: 999,
                                bgcolor: color,
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
        </Grid>
      </Grid>
    </Box>
  );
}
