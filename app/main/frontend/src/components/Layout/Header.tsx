"use client";

import { usePathname } from "next/navigation";
import { AppBar, Box, Toolbar, Typography } from "@mui/material";
import { SIDEBAR_WIDTH } from "./Sidebar";

interface PageMeta {
  title: string;
  subtitle?: string;
  breadcrumb?: string;
}

const pageMeta: Record<string, PageMeta> = {
  "/": {
    title: "Дашборд",
    subtitle: "Общая сводка по звонкам и аналитике",
    breadcrumb: "Главная",
  },
  "/calls": {
    title: "Звонки",
    subtitle: "История звонков, анализ и статусы обработки",
    breadcrumb: "Звонки",
  },
  "/upload": {
    title: "Загрузка звонков",
    subtitle: "Загрузите аудиофайлы для автоматического анализа",
    breadcrumb: "Загрузка",
  },
  "/analytics": {
    title: "Аналитика",
    subtitle: "Статистика по менеджерам и проверкам",
    breadcrumb: "Аналитика",
  },
  "/checks": {
    title: "Конструктор проверок",
    subtitle: "Создавайте правила для автоматической оценки звонков",
    breadcrumb: "Проверки",
  },
  "/users": {
    title: "Пользователи",
    subtitle: "Управление командой и правами доступа",
    breadcrumb: "Пользователи",
  },
  "/integrations": {
    title: "Интеграции",
    subtitle: "Подключение ВАТС, CRM и сторонних сервисов",
    breadcrumb: "Интеграции",
  },
};

function resolveMeta(pathname: string): { meta: PageMeta; isDetail: boolean; detailId?: string } {
  if (pageMeta[pathname]) {
    return { meta: pageMeta[pathname], isDetail: false };
  }

  for (const key of Object.keys(pageMeta)) {
    if (key === "/") continue;
    if (pathname.startsWith(key + "/")) {
      const rest = pathname.slice(key.length + 1);
      return {
        meta: pageMeta[key],
        isDetail: true,
        detailId: rest.split("/")[0],
      };
    }
  }

  return { meta: { title: "", breadcrumb: "" }, isDetail: false };
}

export default function Header() {
  const pathname = usePathname();
  const currentPath = pathname || "/";
  const { meta, isDetail, detailId } = resolveMeta(currentPath);

  return (
    <AppBar
      position="fixed"
      elevation={0}
      sx={{
        width: `calc(100% - ${SIDEBAR_WIDTH}px)`,
        ml: `${SIDEBAR_WIDTH}px`,
        bgcolor: (t) =>
          t.palette.mode === "dark"
            ? "rgba(11, 11, 14, 0.85)"
            : "rgba(250, 250, 249, 0.85)",
        backdropFilter: "saturate(180%) blur(12px)",
        WebkitBackdropFilter: "saturate(180%) blur(12px)",
        borderBottom: "1px solid",
        borderColor: "divider",
        color: "text.primary",
      }}
    >
      <Toolbar sx={{ minHeight: "80px !important", px: { xs: 2.5, md: 4 }, py: 1.25 }}>
        <Box sx={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {meta.breadcrumb && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: 11,
                  fontWeight: 500,
                  color: "text.disabled",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                {meta.breadcrumb}
                {isDetail && (
                  <>
                    {" "}
                    <Box component="span" sx={{ mx: 0.5, color: "text.disabled" }}>/</Box>
                    <Box component="span" sx={{ color: "text.secondary" }}>{detailId}</Box>
                  </>
                )}
              </Typography>
            )}
          </Box>
          {!isDetail && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, mt: 0.25 }}>
              <Typography
                sx={{
                  fontSize: 20,
                  fontWeight: 700,
                  letterSpacing: "-0.015em",
                  color: "text.primary",
                  lineHeight: 1.2,
                }}
              >
                {meta.title}
              </Typography>
            </Box>
          )}
          {meta.subtitle && !isDetail && (
            <Typography
              sx={{
                fontSize: 13,
                color: "text.secondary",
                lineHeight: 1.3,
                mt: 0.25,
              }}
            >
              {meta.subtitle}
            </Typography>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
