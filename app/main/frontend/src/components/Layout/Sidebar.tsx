"use client";

import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Avatar,
  Box,
  Divider,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Typography,
} from "@mui/material";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalkOutlined";
import CloudUploadIcon from "@mui/icons-material/CloudUploadOutlined";
import BarChartIcon from "@mui/icons-material/BarChartOutlined";
import ChecklistIcon from "@mui/icons-material/ChecklistOutlined";
import PeopleIcon from "@mui/icons-material/PeopleAltOutlined";
import DashboardIcon from "@mui/icons-material/SpaceDashboardOutlined";
import HubIcon from "@mui/icons-material/HubOutlined";
import LogoutIcon from "@mui/icons-material/LogoutOutlined";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import DarkModeIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeIcon from "@mui/icons-material/LightModeOutlined";
import { useAuth } from "@/context/AuthContext";
import { useThemeMode } from "@/context/ThemeModeContext";
import { canAccess } from "@/lib/rbac";

const SIDEBAR_WIDTH = 244;

interface MenuItem {
  label: string;
  icon: React.ReactNode;
  href: string;
  section: "main" | "management" | "system";
}

const menuItems: MenuItem[] = [
  { label: "Дашборд", icon: <DashboardIcon fontSize="small" />, href: "/", section: "main" },
  { label: "Аналитика", icon: <BarChartIcon fontSize="small" />, href: "/analytics", section: "main" },
  { label: "Звонки", icon: <PhoneInTalkIcon fontSize="small" />, href: "/calls", section: "main" },
  { label: "Загрузка", icon: <CloudUploadIcon fontSize="small" />, href: "/upload", section: "main" },
  { label: "Проверки", icon: <ChecklistIcon fontSize="small" />, href: "/checks", section: "management" },
  { label: "Пользователи", icon: <PeopleIcon fontSize="small" />, href: "/users", section: "management" },
  { label: "Интеграции", icon: <HubIcon fontSize="small" />, href: "/integrations", section: "system" },
];

const sectionTitles: Record<string, string> = {
  main: "Основное",
  management: "Управление",
  system: "Система",
};

const roleLabels: Record<string, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
};

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { mode, toggle } = useThemeMode();

  const currentPath = pathname || "/";

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const isActive = (href: string) => {
    if (href === "/") return currentPath === "/";
    return currentPath === href || currentPath.startsWith(href + "/");
  };

  const visibleItems = menuItems.filter((item) => canAccess(item.href, user?.role));
  const grouped = visibleItems.reduce<Record<string, MenuItem[]>>((acc, item) => {
    (acc[item.section] ||= []).push(item);
    return acc;
  }, {});
  const sectionOrder: Array<"main" | "management" | "system"> = ["main", "management", "system"];

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: SIDEBAR_WIDTH,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: SIDEBAR_WIDTH,
          boxSizing: "border-box",
          bgcolor: "background.paper",
          color: "text.primary",
          borderRight: "1px solid",
          borderColor: "divider",
        },
      }}
    >
      <Box sx={{ px: 2.5, pt: 3, pb: 2.5 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 2,
              background: "var(--gradient-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              boxShadow: "0 4px 12px rgba(99, 91, 255, 0.35)",
            }}
          >
            <GraphicEqIcon sx={{ fontSize: 20 }} />
          </Box>
          <Box>
            <Typography sx={{ fontWeight: 700, fontSize: 15, lineHeight: 1.2, letterSpacing: "-0.01em" }}>
              AI Calls
            </Typography>
            <Typography sx={{ fontSize: 11, color: "text.secondary", lineHeight: 1.2 }}>
              Аналитика звонков
            </Typography>
          </Box>
        </Box>
      </Box>

      <Divider sx={{ mx: 2 }} />

      <Box sx={{ px: 1.25, py: 1.5, flex: 1, overflowY: "auto" }}>
        {sectionOrder.map((section) =>
          grouped[section]?.length ? (
            <Box key={section} sx={{ mb: 1.5 }}>
              <Typography
                sx={{
                  px: 1.5,
                  py: 0.75,
                  fontSize: 10.5,
                  fontWeight: 600,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "text.disabled",
                }}
              >
                {sectionTitles[section]}
              </Typography>
              <List disablePadding>
                {grouped[section].map((item) => {
                  const active = isActive(item.href);
                  return (
                    <ListItemButton
                      key={item.href}
                      component={Link}
                      href={item.href}
                      sx={{
                        borderRadius: 2,
                        mx: 0.25,
                        my: 0.25,
                        py: 0.9,
                        px: 1.25,
                        position: "relative",
                        color: active ? "primary.dark" : "text.secondary",
                        bgcolor: active ? "brand.violetTint" : "transparent",
                        "&:hover": {
                          bgcolor: active ? "brand.violetTint" : "surface.subtle",
                          color: active ? "primary.dark" : "text.primary",
                        },
                        "&::before": active
                          ? {
                              content: '""',
                              position: "absolute",
                              left: -5,
                              top: "20%",
                              bottom: "20%",
                              width: 3,
                              borderRadius: 4,
                              bgcolor: "primary.main",
                            }
                          : undefined,
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 30,
                          color: active ? "primary.main" : "text.disabled",
                        }}
                      >
                        {item.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={item.label}
                        slotProps={{
                          primary: {
                            sx: {
                              fontSize: 13.5,
                              fontWeight: active ? 600 : 500,
                              letterSpacing: "-0.005em",
                            },
                          },
                        }}
                      />
                    </ListItemButton>
                  );
                })}
              </List>
            </Box>
          ) : null
        )}
      </Box>

      {user && (
        <>
          <Divider sx={{ mx: 2 }} />
          <Box sx={{ p: 1.5 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.25,
                px: 1,
                py: 1,
                borderRadius: 2,
              }}
            >
              <Avatar
                sx={{
                  width: 34,
                  height: 34,
                  background: "var(--gradient-primary)",
                  fontSize: 13,
                  fontWeight: 600,
                }}
              >
                {user.name[0]?.toUpperCase()}
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  sx={{
                    fontSize: 13,
                    fontWeight: 600,
                    lineHeight: 1.3,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "text.primary",
                  }}
                >
                  {user.name}
                </Typography>
                <Typography sx={{ fontSize: 11, color: "text.secondary", lineHeight: 1.3 }}>
                  {roleLabels[user.role || "manager"] || user.role}
                </Typography>
              </Box>
              <Tooltip title={mode === "dark" ? "Светлая тема" : "Тёмная тема"} placement="top">
                <ListItemButton
                  onClick={toggle}
                  sx={{
                    flex: "none",
                    borderRadius: 1.5,
                    p: 0.75,
                    color: "text.disabled",
                    "&:hover": { bgcolor: "surface.subtle", color: "text.primary" },
                  }}
                >
                  {mode === "dark" ? (
                    <LightModeIcon sx={{ fontSize: 18 }} />
                  ) : (
                    <DarkModeIcon sx={{ fontSize: 18 }} />
                  )}
                </ListItemButton>
              </Tooltip>
              <Tooltip title="Выйти" placement="top">
                <ListItemButton
                  onClick={handleLogout}
                  sx={{
                    flex: "none",
                    borderRadius: 1.5,
                    p: 0.75,
                    color: "text.disabled",
                    "&:hover": { bgcolor: "error.light", color: "error.contrastText" },
                  }}
                >
                  <LogoutIcon sx={{ fontSize: 18 }} />
                </ListItemButton>
              </Tooltip>
            </Box>
          </Box>
        </>
      )}
    </Drawer>
  );
}

export { SIDEBAR_WIDTH };
