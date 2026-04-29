"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { Alert, Box, IconButton, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import PlayArrowIcon from "@mui/icons-material/PlayArrowRounded";
import PauseIcon from "@mui/icons-material/PauseRounded";
import WaveSurfer from "wavesurfer.js";

export interface WaveformPlayerHandle {
  seekTo: (seconds: number) => void;
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
}

interface WaveformPlayerProps {
  src: string;
  height?: number;
  onTimeUpdate?: (seconds: number) => void;
  onPlayStateChange?: (playing: boolean) => void;
  onReady?: (duration: number) => void;
}

function formatTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export const WaveformPlayer = forwardRef<WaveformPlayerHandle, WaveformPlayerProps>(
  function WaveformPlayer(
    { src, height = 56, onTimeUpdate, onPlayStateChange, onReady },
    ref
  ) {
    const theme = useTheme();
    const containerRef = useRef<HTMLDivElement | null>(null);
    const wsRef = useRef<WaveSurfer | null>(null);

    const [ready, setReady] = useState(false);
    const [playing, setPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [error, setError] = useState(false);

    const waveColor = theme.palette.mode === "dark" ? "#3B3B43" : "rgba(99,91,255,0.25)";
    const progressColor = theme.palette.primary.main;
    const cursorColor = theme.palette.primary.dark;

    useEffect(() => {
      if (!containerRef.current) return;

      setReady(false);
      setError(false);
      setPlaying(false);
      setCurrentTime(0);

      const ws = WaveSurfer.create({
        container: containerRef.current,
        url: src,
        waveColor,
        progressColor,
        cursorColor,
        cursorWidth: 1,
        height,
        barWidth: 2,
        barGap: 2,
        barRadius: 3,
        normalize: true,
        interact: true,
      });

      wsRef.current = ws;

      ws.on("ready", () => {
        const d = ws.getDuration();
        setDuration(d);
        setReady(true);
        onReady?.(d);
      });
      ws.on("timeupdate", (t) => {
        setCurrentTime(t);
        onTimeUpdate?.(t);
      });
      ws.on("play", () => {
        setPlaying(true);
        onPlayStateChange?.(true);
      });
      ws.on("pause", () => {
        setPlaying(false);
        onPlayStateChange?.(false);
      });
      ws.on("finish", () => {
        setPlaying(false);
        onPlayStateChange?.(false);
      });
      ws.on("error", () => {
        setError(true);
        setReady(false);
      });

      return () => {
        try {
          ws.destroy();
        } catch {
          // ignore
        }
        wsRef.current = null;
      };
    }, [src, height, waveColor, progressColor, cursorColor, onReady, onTimeUpdate, onPlayStateChange]);

    const seekTo = useCallback((seconds: number) => {
      const ws = wsRef.current;
      if (!ws || !ready) return;
      const dur = ws.getDuration();
      if (!dur || dur <= 0) return;
      ws.setTime(Math.max(0, Math.min(seconds, dur)));
      if (!ws.isPlaying()) {
        ws.play().catch(() => setError(true));
      }
    }, [ready]);

    const play = useCallback(() => {
      wsRef.current?.play().catch(() => setError(true));
    }, []);

    const pause = useCallback(() => {
      wsRef.current?.pause();
    }, []);

    const togglePlay = useCallback(() => {
      const ws = wsRef.current;
      if (!ws) return;
      if (ws.isPlaying()) {
        ws.pause();
      } else {
        ws.play().catch(() => setError(true));
      }
    }, []);

    useImperativeHandle(ref, () => ({ seekTo, play, pause, togglePlay }), [seekTo, play, pause, togglePlay]);

    return (
      <Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton
            onClick={togglePlay}
            disabled={!ready || error}
            sx={{
              width: 48,
              height: 48,
              background: "var(--gradient-primary)",
              color: "#fff",
              boxShadow: "0 8px 20px -6px rgba(99,91,255,0.45)",
              flexShrink: 0,
              "&:hover": {
                background: "var(--gradient-primary)",
                transform: "scale(1.04)",
              },
              "&.Mui-disabled": {
                background: "var(--gradient-primary)",
                opacity: 0.55,
                color: "#fff",
              },
            }}
          >
            {playing ? <PauseIcon /> : <PlayArrowIcon />}
          </IconButton>
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Box
              ref={containerRef}
              sx={{
                width: "100%",
                minHeight: height,
                borderRadius: 1.5,
                opacity: ready ? 1 : 0.4,
                transition: "opacity 0.3s",
              }}
            />
            <Box sx={{ display: "flex", justifyContent: "space-between", mt: 0.75 }}>
              <Typography
                sx={{
                  fontSize: 12,
                  color: "text.secondary",
                  fontVariantNumeric: "tabular-nums",
                  fontWeight: 600,
                }}
              >
                {formatTime(currentTime)}
              </Typography>
              <Typography
                sx={{
                  fontSize: 12,
                  color: "text.secondary",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {duration > 0 ? formatTime(duration) : "—"}
              </Typography>
            </Box>
          </Box>
        </Box>
        {error && (
          <Alert severity="warning" sx={{ mt: 1.5 }}>
            Не удалось воспроизвести аудио. Файл может быть недоступен.
          </Alert>
        )}
      </Box>
    );
  }
);
