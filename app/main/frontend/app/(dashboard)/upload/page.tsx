"use client";

import React, { DragEvent, useRef, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stepper,
  Step,
  StepLabel,
  LinearProgress,
  Avatar,
  Chip,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import type { Theme } from "@mui/material/styles";
import CloudUploadIcon from "@mui/icons-material/CloudUploadOutlined";
import AudioFileIcon from "@mui/icons-material/AudioFileOutlined";
import CheckCircleIcon from "@mui/icons-material/CheckCircleOutlined";
import MusicNoteIcon from "@mui/icons-material/MusicNoteOutlined";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesomeOutlined";
import GroupIcon from "@mui/icons-material/GroupOutlined";
import { callsApi, usersApi } from "@/lib/api";
import { useAuth, isHeadOrAdmin } from "@/context/AuthContext";
import { useTaskStatus, describeStep } from "@/hooks/useTaskStatus";
import type { User } from "@/types";

const steps = ["Загрузка файла", "Анализ", "Готово"];

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { user } = useAuth();
  const canChooseManager = isHeadOrAdmin(user);

  const [managers, setManagers] = useState<User[]>([]);
  const [managerId, setManagerId] = useState<string>("");

  const [drag, setDrag] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  const [activeStep, setActiveStep] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [callId, setCallId] = useState<number | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (canChooseManager) {
      usersApi
        .list("manager")
        .then((list) => {
          // admin/head не в списке роли "manager" — добавляем себя явно, чтобы могли привязать звонок к себе
          if (user && !list.some((m) => m.id === user.id)) {
            setManagers([...list, user]);
          } else {
            setManagers(list);
          }
        })
        .catch(() => {});
    }
  }, [canChooseManager, user]);

  const { status: taskStatus } = useTaskStatus(taskId, {
    intervalMs: 2000,
    onSuccess: () => {
      setActiveStep(2);
      setDone(true);
    },
    onFailure: (s) => {
      setError(s.error || "Анализ завершился с ошибкой");
      setDone(false);
    },
  });

  const analyzing = taskId !== null && !done && !error;
  const isProcessing = uploading || analyzing;

  const progressPercent = taskStatus?.percent ?? 0;
  const progressLabel = uploading
    ? "Загрузка файла..."
    : describeStep(taskStatus?.step);

  const processFile = (f: File) => {
    setFile(f);
    setError("");
    setActiveStep(0);
    setCallId(null);
    setTaskId(null);
    setDone(false);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) processFile(f);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) processFile(f);
  };

  const handleStart = async () => {
    if (!file) return;
    setError("");

    setActiveStep(0);
    setUploading(true);
    try {
      const mid = canChooseManager && managerId ? Number(managerId) : undefined;
      const result = await callsApi.upload(file, mid);
      setCallId(result.call_id);
      setUploading(false);

      setActiveStep(1);
      const { task_id } = await callsApi.analyze(result.call_id);
      setTaskId(task_id);
    } catch (e: unknown) {
      setUploading(false);
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const retryAnalyze = async () => {
    if (!callId) return;
    setError("");
    setDone(false);
    setActiveStep(1);
    try {
      const { task_id } = await callsApi.analyze(callId);
      setTaskId(task_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleReset = () => {
    setFile(null);
    setCallId(null);
    setTaskId(null);
    setActiveStep(0);
    setDone(false);
    setError("");
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const perks: Array<{
    icon: React.ReactNode;
    label: string;
    tone: "violet" | "teal" | "amber";
  }> = [
    {
      icon: <GraphicEqIcon sx={{ fontSize: 18 }} />,
      label: "Транскрипция T-one",
      tone: "violet",
    },
    {
      icon: <GroupIcon sx={{ fontSize: 18 }} />,
      label: "Разделение по ролям",
      tone: "teal",
    },
    {
      icon: <AutoAwesomeIcon sx={{ fontSize: 18 }} />,
      label: "Оценка YandexGPT",
      tone: "amber",
    },
  ];

  const perkTintKey = {
    violet: "brand.violetTint" as const,
    teal: "brand.tealTint" as const,
    amber: "brand.amberTint" as const,
  };
  const perkOnTint = {
    violet: (t: Theme) => (t.palette.mode === "dark" ? "#A5A0FF" : "#4F46E5"),
    teal: (t: Theme) => (t.palette.mode === "dark" ? "#6EE7B7" : "#047857"),
    amber: (t: Theme) => (t.palette.mode === "dark" ? "#FCD34D" : "#B45309"),
  };

  return (
    <Box className="fade-in">
      {canChooseManager && (
        <Card sx={{ mb: 2.5 }}>
          <CardContent
            sx={{
              display: "flex",
              gap: 2,
              alignItems: "center",
              py: 2,
              "&:last-child": { pb: 2 },
            }}
          >
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel>Менеджер</InputLabel>
              <Select
                value={managerId}
                label="Менеджер"
                onChange={(e: SelectChangeEvent) => setManagerId(e.target.value)}
                disabled={isProcessing}
              >
                <MenuItem value="">Не указан</MenuItem>
                {managers.map((m) => {
                  const isSelf = user?.id === m.id;
                  const roleSuffix =
                    m.role === "admin" ? " (админ)" : m.role === "head" ? " (руководитель)" : "";
                  return (
                    <MenuItem key={m.id} value={String(m.id)}>
                      {m.name}
                      {roleSuffix}
                      {isSelf ? " — я" : ""}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              Привяжите запись к менеджеру для точной аналитики
            </Typography>
          </CardContent>
        </Card>
      )}

      <Card
        sx={{
          overflow: "hidden",
          background: (t) =>
            t.palette.mode === "dark"
              ? "linear-gradient(180deg, #15151B 0%, #0F0F13 100%)"
              : "linear-gradient(180deg, #FFFFFF 0%, #FAFAF9 100%)",
        }}
      >
        <CardContent sx={{ p: { xs: 3, md: 4 } }}>
          {!file ? (
            <>
              <Box
                onDragOver={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragLeave={() => setDrag(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                sx={{
                  position: "relative",
                  border: "2px dashed",
                  borderColor: drag ? "primary.main" : "divider",
                  borderRadius: 4,
                  p: { xs: 4, md: 6 },
                  minHeight: { xs: 380, md: 520 },
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  textAlign: "center",
                  cursor: "pointer",
                  overflow: "hidden",
                  transition: "all 0.25s ease",
                  background: (t) =>
                    t.palette.mode === "dark"
                      ? drag
                        ? "linear-gradient(135deg, rgba(99,91,255,0.18) 0%, rgba(236,72,153,0.10) 100%)"
                        : "linear-gradient(135deg, rgba(245,158,11,0.08) 0%, rgba(245,158,11,0.04) 50%, rgba(239,68,68,0.06) 100%)"
                      : drag
                        ? "linear-gradient(135deg, #F5F3FF 0%, #FCE7F3 100%)"
                        : "linear-gradient(135deg, #FFFBF2 0%, #FEF4DD 50%, #FDE8E4 100%)",
                  "&:hover": {
                    borderColor: "primary.main",
                    transform: "translateY(-1px)",
                    boxShadow: "0 8px 24px -8px rgba(99, 91, 255, 0.18)",
                  },
                }}
              >
                <Box
                  sx={{
                    position: "absolute",
                    top: -30,
                    right: -30,
                    width: 140,
                    height: 140,
                    borderRadius: "50%",
                    background: "radial-gradient(circle, rgba(255,255,255,0.7) 0%, transparent 70%)",
                  }}
                />
                <Box
                  sx={{
                    position: "absolute",
                    bottom: -40,
                    left: -20,
                    width: 120,
                    height: 120,
                    borderRadius: "50%",
                    background: "radial-gradient(circle, rgba(255,255,255,0.5) 0%, transparent 70%)",
                  }}
                />

                <Box sx={{ position: "relative", display: "inline-flex", gap: 1, mb: 2 }}>
                  {[0, 1, 2].map((i) => (
                    <Avatar
                      key={i}
                      variant="rounded"
                      sx={{
                        width: 52,
                        height: 52,
                        borderRadius: 2.5,
                        bgcolor: "background.paper",
                        color: (t) =>
                          t.palette.mode === "dark"
                            ? ["#A5A0FF", "#F472B6", "#FBBF24"][i]
                            : ["#635BFF", "#EC4899", "#F59E0B"][i],
                        border: "1px solid",
                        borderColor: "divider",
                        boxShadow: (t) => t.palette.elevation.sm,
                        transform: `rotate(${i === 0 ? -8 : i === 2 ? 8 : 0}deg) translateY(${
                          i === 1 ? -4 : 0
                        }px)`,
                        transition: "transform 0.25s",
                      }}
                    >
                      {i === 0 ? (
                        <MusicNoteIcon />
                      ) : i === 1 ? (
                        <GraphicEqIcon />
                      ) : (
                        <CloudUploadIcon />
                      )}
                    </Avatar>
                  ))}
                </Box>

                <Typography
                  sx={{
                    position: "relative",
                    fontSize: 18,
                    fontWeight: 700,
                    letterSpacing: "-0.015em",
                    color: "text.primary",
                    mb: 0.5,
                  }}
                >
                  Перетащите запись сюда
                </Typography>
                <Typography
                  sx={{
                    position: "relative",
                    fontSize: 13.5,
                    color: "text.secondary",
                    mb: 2,
                  }}
                >
                  или нажмите, чтобы выбрать файл на устройстве
                </Typography>

                <Box
                  sx={{
                    position: "relative",
                    display: "inline-flex",
                    gap: 0.75,
                    flexWrap: "wrap",
                    justifyContent: "center",
                  }}
                >
                  {["mp3", "wav", "ogg", "m4a", "flac"].map((f) => (
                    <Chip
                      key={f}
                      label={f}
                      size="small"
                      sx={{
                        bgcolor: (t) =>
                          t.palette.mode === "dark"
                            ? "rgba(255,255,255,0.06)"
                            : "rgba(255,255,255,0.7)",
                        color: "text.secondary",
                        fontWeight: 600,
                        fontSize: 11,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}
                    />
                  ))}
                </Box>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*"
                  hidden
                  onChange={handleFileInput}
                />
              </Box>

              <Box
                sx={{
                  mt: 3,
                  display: "flex",
                  gap: 1.5,
                  flexWrap: "wrap",
                  justifyContent: "center",
                }}
              >
                {perks.map((p) => (
                  <Box
                    key={p.label}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      px: 1.5,
                      py: 0.75,
                      borderRadius: 999,
                      bgcolor: perkTintKey[p.tone],
                      color: perkOnTint[p.tone],
                    }}
                  >
                    {p.icon}
                    <Typography sx={{ fontSize: 12.5, fontWeight: 600 }}>{p.label}</Typography>
                  </Box>
                ))}
              </Box>
            </>
          ) : (
            <Box>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 2,
                  p: 2,
                  mb: 3,
                  borderRadius: 3,
                  background: (t) =>
                    t.palette.mode === "dark"
                      ? "linear-gradient(135deg, rgba(99,91,255,0.10) 0%, rgba(99,91,255,0.04) 100%)"
                      : "linear-gradient(135deg, #FBFAFF 0%, #F2F0FE 100%)",
                  border: "1px solid",
                  borderColor: (t) =>
                    t.palette.mode === "dark" ? "rgba(139,133,255,0.25)" : "#E5E2FC",
                }}
              >
                <Avatar
                  variant="rounded"
                  sx={{
                    width: 44,
                    height: 44,
                    bgcolor: "background.paper",
                    color: "primary.main",
                    borderRadius: 2.5,
                    border: "1px solid",
                    borderColor: (t) =>
                      t.palette.mode === "dark"
                        ? "rgba(139,133,255,0.30)"
                        : "rgba(99,91,255,0.15)",
                  }}
                >
                  <AudioFileIcon />
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    sx={{
                      fontSize: 14,
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {file.name}
                  </Typography>
                  <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                    {(file.size / 1024 / 1024).toFixed(1)} МБ · готов к загрузке
                  </Typography>
                </Box>
                {!isProcessing && !done && (
                  <Button size="small" variant="outlined" onClick={handleReset}>
                    Другой файл
                  </Button>
                )}
              </Box>

              <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
                {steps.map((label) => (
                  <Step key={label}>
                    <StepLabel>{label}</StepLabel>
                  </Step>
                ))}
              </Stepper>

              {isProcessing && (
                <Box
                  sx={{
                    mb: 3,
                    p: 2,
                    borderRadius: 2,
                    bgcolor: "surface.subtle",
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mb: 1,
                    }}
                  >
                    <Typography sx={{ fontSize: 13, fontWeight: 500, color: "text.primary" }}>
                      {progressLabel}
                    </Typography>
                    {analyzing && progressPercent > 0 && (
                      <Typography
                        sx={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "primary.dark",
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {progressPercent}%
                      </Typography>
                    )}
                  </Box>
                  {analyzing && progressPercent > 0 ? (
                    <LinearProgress
                      variant="determinate"
                      value={progressPercent}
                      sx={{
                        height: 8,
                        borderRadius: 999,
                        "& .MuiLinearProgress-bar": {
                          background: "var(--gradient-primary)",
                        },
                      }}
                    />
                  ) : (
                    <LinearProgress
                      sx={{
                        height: 8,
                        borderRadius: 999,
                        "& .MuiLinearProgress-bar": {
                          background: "var(--gradient-primary)",
                        },
                      }}
                    />
                  )}
                </Box>
              )}

              {done && callId && (
                <Box
                  sx={{
                    textAlign: "center",
                    py: 3,
                    px: 2,
                    borderRadius: 3,
                    background: (t) =>
                      t.palette.mode === "dark"
                        ? "linear-gradient(135deg, rgba(52,211,153,0.10) 0%, rgba(16,185,129,0.04) 100%)"
                        : "linear-gradient(135deg, #F6FDFB 0%, #E8F9F3 100%)",
                    border: "1px solid",
                    borderColor: (t) =>
                      t.palette.mode === "dark" ? "rgba(52,211,153,0.25)" : "#C7EFDF",
                  }}
                >
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      bgcolor: "background.paper",
                      color: "success.main",
                      mx: "auto",
                      mb: 1.5,
                      boxShadow: "0 8px 24px -8px rgba(16,185,129,0.35)",
                    }}
                  >
                    <CheckCircleIcon sx={{ fontSize: 32 }} />
                  </Avatar>
                  <Typography sx={{ fontSize: 18, fontWeight: 700, mb: 0.5 }}>
                    Готово! Всё на месте
                  </Typography>
                  <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2.5 }}>
                    Звонок {callId} успешно проанализирован
                  </Typography>
                  <Box sx={{ display: "flex", gap: 1.5, justifyContent: "center", flexWrap: "wrap" }}>
                    <Button
                      variant="contained"
                      onClick={() => router.push(`/calls/${callId}`)}
                    >
                      Посмотреть результат
                    </Button>
                    <Button variant="outlined" onClick={handleReset}>
                      Загрузить ещё
                    </Button>
                  </Box>
                </Box>
              )}

              {!isProcessing && !done && (
                <Button
                  variant="contained"
                  fullWidth
                  size="large"
                  startIcon={<CloudUploadIcon />}
                  onClick={handleStart}
                  sx={{ py: 1.5, fontSize: 15 }}
                >
                  Загрузить и проанализировать
                </Button>
              )}
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {error}
              {callId && (
                <Button size="small" sx={{ ml: 2 }} onClick={retryAnalyze}>
                  Повторить анализ
                </Button>
              )}
            </Alert>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
