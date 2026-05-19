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
  Tooltip,
  Avatar,
  InputAdornment,
  useTheme,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import AddIcon from "@mui/icons-material/AddRounded";
import EditIcon from "@mui/icons-material/EditOutlined";
import DeleteIcon from "@mui/icons-material/DeleteOutlineOutlined";
import RefreshIcon from "@mui/icons-material/RefreshOutlined";
import SearchIcon from "@mui/icons-material/SearchOutlined";
import GroupsIcon from "@mui/icons-material/GroupsOutlined";
import AdminPanelIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import SupervisorIcon from "@mui/icons-material/SupervisorAccountOutlined";
import PersonIcon from "@mui/icons-material/PersonOutlineOutlined";
import { usersApi } from "@/lib/api";
import type { User } from "@/types";
import { formatDate } from "@/lib/format";
import { useTableSort, SortableCell } from "@/hooks/useTableSort";
import { TableRowSkeleton } from "@/components/Skeleton";

type UserSortKey = "name" | "phone_number" | "role" | "created_at";

const roleLabels: Record<string, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
};

type Tone = "violet" | "teal" | "amber" | "rose" | "sky";

const roleTones: Record<string, Tone> = {
  admin: "rose",
  head: "amber",
  manager: "violet",
};

const roleIcons: Record<string, React.ReactElement> = {
  admin: <AdminPanelIcon sx={{ fontSize: 14 }} />,
  head: <SupervisorIcon sx={{ fontSize: 14 }} />,
  manager: <PersonIcon sx={{ fontSize: 14 }} />,
};

type ToneStyle = { bg: string; ring: string; fg: string; avatarBg: string; avatarFg: string };

const lightTones: Record<Tone, ToneStyle> = {
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

const darkTones: Record<Tone, ToneStyle> = {
  violet: {
    bg: "linear-gradient(180deg, rgba(139,92,246,0.10) 0%, rgba(139,92,246,0.04) 100%)",
    ring: "rgba(139,92,246,0.30)",
    fg: "#C4B5FD",
    avatarBg: "#2B2560",
    avatarFg: "#A5A0FF",
  },
  teal: {
    bg: "linear-gradient(180deg, rgba(52,211,153,0.10) 0%, rgba(16,185,129,0.04) 100%)",
    ring: "rgba(52,211,153,0.30)",
    fg: "#6EE7B7",
    avatarBg: "#0F3B2E",
    avatarFg: "#6EE7B7",
  },
  amber: {
    bg: "linear-gradient(180deg, rgba(251,191,36,0.10) 0%, rgba(245,158,11,0.04) 100%)",
    ring: "rgba(251,191,36,0.30)",
    fg: "#FCD34D",
    avatarBg: "#3D2A0B",
    avatarFg: "#FCD34D",
  },
  rose: {
    bg: "linear-gradient(180deg, rgba(244,63,94,0.10) 0%, rgba(244,63,94,0.04) 100%)",
    ring: "rgba(244,63,94,0.30)",
    fg: "#FCA5A5",
    avatarBg: "#3F1717",
    avatarFg: "#FCA5A5",
  },
  sky: {
    bg: "linear-gradient(180deg, rgba(96,165,250,0.10) 0%, rgba(59,130,246,0.04) 100%)",
    ring: "rgba(96,165,250,0.30)",
    fg: "#93C5FD",
    avatarBg: "#0F2A4D",
    avatarFg: "#93C5FD",
  },
};

interface UserFormData {
  name: string;
  phone_number: string;
  role: string;
  password: string;
}

const emptyForm: UserFormData = { name: "", phone_number: "", role: "manager", password: "" };

export default function UsersPage() {
  const theme = useTheme();
  const tones = theme.palette.mode === "dark" ? darkTones : lightTones;
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("");

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form, setForm] = useState<UserFormData>(emptyForm);
  const [formError, setFormError] = useState("");

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await usersApi.list();
      setUsers(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const openCreate = () => {
    setEditingUser(null);
    setForm(emptyForm);
    setFormError("");
    setDialogOpen(true);
  };

  const openEdit = (user: User) => {
    setEditingUser(user);
    setForm({
      name: user.name,
      phone_number: user.phone_number || "",
      role: user.role || "manager",
      password: "",
    });
    setFormError("");
    setDialogOpen(true);
  };

  const handleClose = () => {
    setDialogOpen(false);
    setEditingUser(null);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      setFormError("Имя обязательно");
      return;
    }

    setSaving(true);
    setFormError("");

    try {
      const phone = form.phone_number.trim();
      if (phone && !/^\+\d{10,15}$/.test(phone)) {
        setFormError("Телефон должен быть в международном формате, например +79991234567");
        setSaving(false);
        return;
      }

      const payload: {
        name: string;
        phone_number?: string;
        role: string;
        password?: string;
      } = {
        name: form.name.trim(),
        phone_number: phone || undefined,
        role: form.role,
      };
      if (form.password.trim()) {
        payload.password = form.password;
      }

      if (editingUser) {
        await usersApi.update(editingUser.id, payload);
      } else {
        await usersApi.create(payload);
      }

      handleClose();
      loadUsers();
    } catch (e: unknown) {
      setFormError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Удалить пользователя «${user.name}»?`)) return;
    try {
      await usersApi.delete(user.id);
      setUsers((prev) => prev.filter((u) => u.id !== user.id));
    } catch (e: unknown) {
      alert(`Ошибка: ${e instanceof Error ? e.message : e}`);
    }
  };

  const filtered = users.filter((u) => {
    if (roleFilter && u.role !== roleFilter) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      return (
        u.name.toLowerCase().includes(q) ||
        (u.phone_number || "").toLowerCase().includes(q) ||
        (roleLabels[u.role || ""] || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  const roleCounts = users.reduce<Record<string, number>>((acc, u) => {
    const r = u.role || "manager";
    acc[r] = (acc[r] || 0) + 1;
    return acc;
  }, {});

  const userSort = useTableSort<User, UserSortKey>(filtered, {
    name: (u) => u.name,
    phone_number: (u) => u.phone_number,
    role: (u) => roleLabels[u.role || ""] || u.role,
    created_at: (u) => (u.created_at ? new Date(u.created_at) : null),
  });
  const sortedUsers = userSort.sorted;

  return (
    <Box className="fade-in">
      {/* Tonal stat row */}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
          gap: 1.5,
          mb: 2.5,
        }}
      >
        {(
          [
            { tone: "violet" as Tone, icon: <GroupsIcon />, label: "Всего", value: users.length },
            {
              tone: "rose" as Tone,
              icon: <AdminPanelIcon />,
              label: "Админы",
              value: roleCounts.admin || 0,
            },
            {
              tone: "amber" as Tone,
              icon: <SupervisorIcon />,
              label: "Руководители",
              value: roleCounts.head || 0,
            },
            {
              tone: "teal" as Tone,
              icon: <PersonIcon />,
              label: "Менеджеры",
              value: roleCounts.manager || 0,
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
              <CardContent sx={{ display: "flex", alignItems: "center", gap: 1.5, py: 2, "&:last-child": { pb: 2 } }}>
                <Avatar
                  sx={{ width: 38, height: 38, bgcolor: t.avatarBg, color: t.avatarFg }}
                >
                  {s.icon}
                </Avatar>
                <Box>
                  <Typography
                    sx={{ fontSize: 11, fontWeight: 600, color: t.fg, textTransform: "uppercase", letterSpacing: "0.06em" }}
                  >
                    {s.label}
                  </Typography>
                  <Typography sx={{ fontSize: 22, fontWeight: 700, color: t.fg, lineHeight: 1.1 }}>
                    {s.value}
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
            placeholder="Поиск по имени, телефону или роли"
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

          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Роль</InputLabel>
            <Select
              value={roleFilter}
              label="Роль"
              onChange={(e: SelectChangeEvent) => setRoleFilter(e.target.value)}
            >
              <MenuItem value="">Все роли</MenuItem>
              <MenuItem value="admin">Администратор</MenuItem>
              <MenuItem value="head">Руководитель</MenuItem>
              <MenuItem value="manager">Менеджер</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ flex: 1 }} />

          <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={loadUsers}>
            Обновить
          </Button>
          <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate}>
            Добавить
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
      )}

      <Card>
        {loading ? (
          <Box>
            {Array.from({ length: 6 }).map((_, i) => (
              <TableRowSkeleton key={i} cols={5} />
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
              <GroupsIcon sx={{ fontSize: 30, color: "primary.main" }} />
            </Box>
            <Typography sx={{ fontSize: 16, fontWeight: 600, color: "text.primary", mb: 0.5 }}>
              {search || roleFilter ? "Никого не нашли" : "Пользователей ещё нет"}
            </Typography>
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              {search || roleFilter
                ? "Попробуйте изменить поиск или снять фильтры"
                : "Нажмите «Добавить», чтобы создать первого пользователя"}
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <SortableCell sortKey="name" sort={userSort}>Имя</SortableCell>
                  <SortableCell sortKey="phone_number" sort={userSort}>Телефон</SortableCell>
                  <SortableCell sortKey="role" sort={userSort}>Роль</SortableCell>
                  <SortableCell sortKey="created_at" sort={userSort}>Создан</SortableCell>
                  <TableCell align="right" sx={{ width: 110 }}>Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedUsers.map((user) => {
                  const tone = tones[roleTones[user.role || "manager"] || "violet"];
                  return (
                    <TableRow key={user.id} hover>
                      <TableCell>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                          <Avatar
                            sx={{
                              width: 34,
                              height: 34,
                              fontSize: 13,
                              fontWeight: 700,
                              bgcolor: tone.avatarBg,
                              color: tone.avatarFg,
                            }}
                          >
                            {user.name[0]?.toUpperCase()}
                          </Avatar>
                          <Box>
                            <Typography sx={{ fontSize: 13.5, fontWeight: 600, color: "text.primary" }}>
                              {user.name}
                            </Typography>
                            <Typography sx={{ fontSize: 11.5, color: "text.disabled" }}>
                              ID #{user.id}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography sx={{ fontSize: 13, color: user.phone_number ? "text.primary" : "text.disabled", fontVariantNumeric: "tabular-nums" }}>
                          {user.phone_number || "—"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          icon={roleIcons[user.role || "manager"]}
                          label={roleLabels[user.role || ""] || user.role}
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
                          {formatDate(user.created_at)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Редактировать">
                          <IconButton
                            size="small"
                            onClick={() => openEdit(user)}
                            sx={{ color: "text.disabled", "&:hover": { color: "primary.main", bgcolor: "brand.violetTint" } }}
                          >
                            <EditIcon sx={{ fontSize: 18 }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Удалить">
                          <IconButton
                            size="small"
                            onClick={() => handleDelete(user)}
                            sx={{ color: "text.disabled", "&:hover": { color: "error.main", bgcolor: "error.light" } }}
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
          {filtered.length !== users.length ? ` из ${users.length}` : ""}
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontSize: 17, fontWeight: 700 }}>
          {editingUser ? `Редактировать: ${editingUser.name}` : "Новый пользователь"}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          {formError && <Alert severity="error">{formError}</Alert>}

          <TextField
            label="Имя"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
            required
            autoFocus
          />

          <TextField
            label="Телефон"
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
            fullWidth
            placeholder="+79991234567"
            helperText="Международный формат: +, затем код страны и номер (без пробелов)"
          />

          <TextField
            label={editingUser ? "Новый пароль (оставьте пустым, чтобы не менять)" : "Пароль"}
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            fullWidth
            autoComplete="new-password"
          />

          <FormControl fullWidth>
            <InputLabel>Роль</InputLabel>
            <Select
              value={form.role}
              label="Роль"
              onChange={(e: SelectChangeEvent) => setForm({ ...form, role: e.target.value })}
            >
              <MenuItem value="admin">Администратор</MenuItem>
              <MenuItem value="head">Руководитель</MenuItem>
              <MenuItem value="manager">Менеджер</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={saving}>
            Отмена
          </Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? <CircularProgress size={20} /> : editingUser ? "Сохранить" : "Создать"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
