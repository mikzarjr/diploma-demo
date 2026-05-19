"use client";
export const dynamic = "force-dynamic";
import {Suspense, useEffect, useState} from "react";
import {useRouter, useSearchParams} from "next/navigation";
import {Alert, Box, Button, CircularProgress, TextField, Typography,} from "@mui/material";
import LoginIcon from "@mui/icons-material/LoginRounded";
import GraphicEqIcon from "@mui/icons-material/GraphicEq";
import BoltIcon from "@mui/icons-material/BoltOutlined";
import InsightsIcon from "@mui/icons-material/InsightsOutlined";
import VerifiedIcon from "@mui/icons-material/VerifiedOutlined";
import {useAuth} from "@/context/AuthContext";

// Sanitize ?next= param: only same-origin paths starting with /main/
// (no protocol, no //, no /main/login itself to avoid loops).
function safeNext(raw: string | null): string {
    if (!raw) return "/";
    if (!raw.startsWith("/main/")) return "/";
    if (raw.startsWith("/main/login")) return "/";
    if (raw.includes("//")) return "/";
    // Strip /main basePath — Next router uses paths without it.
    return raw.replace(/^\/main/, "") || "/";
}

function LoginPageInner() {
    const {user, login, loading} = useAuth();
    const router = useRouter();
    const searchParams = useSearchParams();
    const next = safeNext(searchParams.get("next"));
    const [phone, setPhone] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!loading && user) {
            router.replace(next);
        }
    }, [user, loading, router, next]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        const trimmed = phone.trim();
        if (!/^\+\d{10,15}$/.test(trimmed)) {
            setError("Телефон должен быть в международном формате, например +79991234567");
            return;
        }

        setSubmitting(true);
        try {
            await login(trimmed, password);
            router.push(next);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Ошибка входа");
        } finally {
            setSubmitting(false);
        }
    };

    const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        let v = e.target.value;
        const digits = v.replace(/\D/g, "");
        v = digits ? "+" + digits : "";
        setPhone(v);
    };

    const features = [
        {
            icon: <BoltIcon/>,
            title: "Автоматический анализ",
            desc: "Транскрипция и оценка звонков за минуты",
        },
        {
            icon: <InsightsIcon/>,
            title: "Метрики качества",
            desc: "Выявление сильных и слабых мест каждого менеджера",
        },
        {
            icon: <VerifiedIcon/>,
            title: "Конструктор проверок",
            desc: "Настраивайте правила оценки под свою воронку продаж",
        },
    ];

    return (
        <Box
            sx={{
                minHeight: "100vh",
                display: "grid",
                gridTemplateColumns: {xs: "1fr", md: "1.05fr 1fr"},
                bgcolor: "background.default",
            }}
        >
            <Box
                sx={{
                    display: {xs: "none", md: "flex"},
                    flexDirection: "column",
                    justifyContent: "space-between",
                    p: 6,
                    position: "relative",
                    overflow: "hidden",
                    background:
                        "linear-gradient(135deg, #635BFF 0%, #8B5CF6 40%, #A855F7 70%, #EC4899 100%)",
                    color: "#fff",
                }}
            >
                <Box
                    sx={{
                        position: "absolute",
                        top: "-20%",
                        right: "-15%",
                        width: 480,
                        height: 480,
                        borderRadius: "50%",
                        background: "radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 70%)",
                        pointerEvents: "none",
                    }}
                />
                <Box
                    sx={{
                        position: "absolute",
                        bottom: "-25%",
                        left: "-10%",
                        width: 380,
                        height: 380,
                        borderRadius: "50%",
                        background: "radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%)",
                        pointerEvents: "none",
                    }}
                />
                <Box
                    sx={{
                        position: "absolute",
                        inset: 0,
                        backgroundImage:
                            "radial-gradient(rgba(255,255,255,0.15) 1px, transparent 1px)",
                        backgroundSize: "24px 24px",
                        opacity: 0.25,
                        pointerEvents: "none",
                    }}
                />

                <Box sx={{position: "relative", display: "flex", alignItems: "center", gap: 1.5}}>
                    <Box
                        sx={{
                            width: 44,
                            height: 44,
                            borderRadius: 2.5,
                            bgcolor: "rgba(255,255,255,0.18)",
                            backdropFilter: "blur(8px)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            border: "1px solid rgba(255,255,255,0.25)",
                        }}
                    >
                        <GraphicEqIcon sx={{fontSize: 24}}/>
                    </Box>
                    <Box>
                        <Typography sx={{fontSize: 18, fontWeight: 700, letterSpacing: "-0.01em"}}>
                            AI Calls
                        </Typography>
                        <Typography sx={{fontSize: 12, opacity: 0.75}}>
                            Платформа аналитики
                        </Typography>
                    </Box>
                </Box>

                <Box sx={{position: "relative", maxWidth: 480}}>
                    <Typography
                        sx={{
                            fontSize: {md: 36, lg: 42},
                            fontWeight: 700,
                            letterSpacing: "-0.025em",
                            lineHeight: 1.1,
                            mb: 2,
                        }}
                    >
                        Превратите звонки
                        <br/>
                        в данные для роста
                    </Typography>
                    <Typography
                        sx={{
                            fontSize: 16,
                            opacity: 0.9,
                            lineHeight: 1.5,
                            mb: 4,
                        }}
                    >
                        Искусственный интеллект анализирует каждый разговор и подсказывает, как улучшить работу
                        вашей команды продаж.
                    </Typography>

                    <Box sx={{display: "flex", flexDirection: "column", gap: 2}}>
                        {features.map((f) => (
                            <Box
                                key={f.title}
                                sx={{
                                    display: "flex",
                                    alignItems: "flex-start",
                                    gap: 1.5,
                                    p: 1.5,
                                    borderRadius: 2,
                                    bgcolor: "rgba(255,255,255,0.08)",
                                    backdropFilter: "blur(8px)",
                                    border: "1px solid rgba(255,255,255,0.12)",
                                }}
                            >
                                <Box
                                    sx={{
                                        width: 36,
                                        height: 36,
                                        borderRadius: 2,
                                        bgcolor: "rgba(255,255,255,0.18)",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        flexShrink: 0,
                                    }}
                                >
                                    {f.icon}
                                </Box>
                                <Box>
                                    <Typography sx={{fontSize: 14, fontWeight: 600, mb: 0.25}}>
                                        {f.title}
                                    </Typography>
                                    <Typography sx={{fontSize: 12.5, opacity: 0.85, lineHeight: 1.4}}>
                                        {f.desc}
                                    </Typography>
                                </Box>
                            </Box>
                        ))}
                    </Box>
                </Box>

            </Box>

            <Box
                sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    p: {xs: 3, md: 5},
                }}
            >
                <Box sx={{width: "100%", maxWidth: 420}} className="fade-in-up">
                    <Box sx={{display: {xs: "flex", md: "none"}, alignItems: "center", gap: 1.25, mb: 4}}>
                        <Box
                            sx={{
                                width: 40,
                                height: 40,
                                borderRadius: 2,
                                background: "var(--gradient-primary)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "#fff",
                            }}
                        >
                            <GraphicEqIcon/>
                        </Box>
                        <Typography sx={{fontSize: 18, fontWeight: 700}}>AI Calls</Typography>
                    </Box>

                    <Typography
                        sx={{
                            fontSize: 11,
                            fontWeight: 600,
                            color: "primary.main",
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                            mb: 1,
                        }}
                    >
                        Вход в систему
                    </Typography>
                    <Typography
                        sx={{
                            fontSize: 28,
                            fontWeight: 700,
                            letterSpacing: "-0.02em",
                            mb: 1,
                            color: "text.primary",
                        }}
                    >
                        С возвращением 👋
                    </Typography>
                    <Typography
                        sx={{fontSize: 14, color: "text.secondary", mb: 4, lineHeight: 1.5}}
                    >
                        Войдите, чтобы продолжить анализировать звонки вашей команды
                    </Typography>

                    <Box
                        component="form"
                        onSubmit={handleSubmit}
                        sx={{display: "flex", flexDirection: "column", gap: 2}}
                    >
                        <TextField
                            label="Телефон"
                            placeholder="+79991234567"
                            value={phone}
                            onChange={handlePhoneChange}
                            autoComplete="username"
                            required
                            fullWidth
                            disabled={submitting}
                            slotProps={{htmlInput: {inputMode: "tel", maxLength: 16}}}
                        />
                        <TextField
                            label="Пароль"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete="current-password"
                            required
                            fullWidth
                            disabled={submitting}
                        />

                        {error && <Alert severity="error">{error}</Alert>}

                        <Button
                            type="submit"
                            variant="contained"
                            size="large"
                            startIcon={
                                submitting ? <CircularProgress size={18} color="inherit"/> : <LoginIcon/>
                            }
                            disabled={submitting || !phone || !password}
                            sx={{mt: 1, py: 1.25, fontSize: 15}}
                        >
                            {submitting ? "Вход..." : "Войти"}
                        </Button>
                    </Box>

                    <Typography
                        sx={{
                            fontSize: 12,
                            color: "text.disabled",
                            textAlign: "center",
                            mt: 4,
                        }}
                    >
                        Проблемы со входом? Обратитесь к администратору
                    </Typography>
                </Box>
            </Box>
        </Box>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={null}>
            <LoginPageInner/>
        </Suspense>
    );
}
