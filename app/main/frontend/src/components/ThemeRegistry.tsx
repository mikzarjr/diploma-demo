"use client";

import { useMemo } from "react";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { buildTheme } from "@/theme";
import { ThemeModeProvider, useThemeMode } from "@/context/ThemeModeContext";

function ThemedShell({ children }: { children: React.ReactNode }) {
  const { mode } = useThemeMode();
  const theme = useMemo(() => buildTheme(mode), [mode]);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}

export default function ThemeRegistry({ children }: { children: React.ReactNode }) {
  return (
    <ThemeModeProvider>
      <ThemedShell>{children}</ThemedShell>
    </ThemeModeProvider>
  );
}
