import { createTheme, type Theme } from "@mui/material/styles";

declare module "@mui/material/styles" {
  interface Palette {
    brand: {
      violet: string;
      violetTint: string;
      teal: string;
      tealTint: string;
      amber: string;
      amberTint: string;
      rose: string;
      roseTint: string;
      sky: string;
      skyTint: string;
    };
    surface: {
      subtle: string;
      muted: string;
      sunken: string;
    };
    elevation: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
    };
  }
  interface PaletteOptions {
    brand?: Palette["brand"];
    surface?: Palette["surface"];
    elevation?: Palette["elevation"];
  }
}

export type ThemeMode = "light" | "dark";

interface Tokens {
  PRIMARY: string;
  PRIMARY_DARK: string;
  PRIMARY_LIGHT: string;
  PRIMARY_TINT: string;
  SUCCESS: string;
  SUCCESS_TINT: string;
  SUCCESS_ON_TINT: string;
  WARNING: string;
  WARNING_TINT: string;
  WARNING_ON_TINT: string;
  ERROR: string;
  ERROR_TINT: string;
  ERROR_ON_TINT: string;
  INFO: string;
  INFO_TINT: string;
  INFO_ON_TINT: string;
  BG_DEFAULT: string;
  BG_PAPER: string;
  BG_SUBTLE: string;
  BG_MUTED: string;
  BG_SUNKEN: string;
  TEXT_PRIMARY: string;
  TEXT_SECONDARY: string;
  TEXT_MUTED: string;
  DIVIDER: string;
  BORDER: string;
  BORDER_HOVER: string;
  SCROLLBAR: string;
  SCROLLBAR_HOVER: string;
  SHADOW_XS: string;
  SHADOW_SM: string;
  SHADOW_MD: string;
  SHADOW_LG: string;
  SHADOW_XL: string;
  TOOLTIP_BG: string;
  TOOLTIP_FG: string;
  GREY: Record<number, string>;
}

const lightTokens: Tokens = {
  PRIMARY: "#635BFF",
  PRIMARY_DARK: "#4F46E5",
  PRIMARY_LIGHT: "#8B85FF",
  PRIMARY_TINT: "#EEEDFE",

  SUCCESS: "#10B981",
  SUCCESS_TINT: "#D1FAE5",
  SUCCESS_ON_TINT: "#047857",
  WARNING: "#F59E0B",
  WARNING_TINT: "#FEF3C7",
  WARNING_ON_TINT: "#B45309",
  ERROR: "#EF4444",
  ERROR_TINT: "#FEE2E2",
  ERROR_ON_TINT: "#B91C1C",
  INFO: "#3B82F6",
  INFO_TINT: "#DBEAFE",
  INFO_ON_TINT: "#1D4ED8",

  BG_DEFAULT: "#FAFAF9",
  BG_PAPER: "#FFFFFF",
  BG_SUBTLE: "#F5F5F4",
  BG_MUTED: "#EFEFEE",
  BG_SUNKEN: "#F0EFEE",

  TEXT_PRIMARY: "#1C1917",
  TEXT_SECONDARY: "#57534E",
  TEXT_MUTED: "#A8A29E",
  DIVIDER: "#E7E5E4",
  BORDER: "#E7E5E4",
  BORDER_HOVER: "#D6D3D1",
  SCROLLBAR: "#D6D3D1",
  SCROLLBAR_HOVER: "#A8A29E",

  SHADOW_XS: "0 1px 2px 0 rgba(28,25,23,0.04)",
  SHADOW_SM: "0 1px 3px 0 rgba(28,25,23,0.06), 0 1px 2px -1px rgba(28,25,23,0.04)",
  SHADOW_MD: "0 4px 8px -2px rgba(28,25,23,0.06), 0 2px 4px -2px rgba(28,25,23,0.04)",
  SHADOW_LG: "0 12px 24px -6px rgba(28,25,23,0.08), 0 4px 8px -4px rgba(28,25,23,0.04)",
  SHADOW_XL: "0 24px 48px -12px rgba(28,25,23,0.12)",

  TOOLTIP_BG: "#1C1917",
  TOOLTIP_FG: "#FAFAF9",

  GREY: {
    50: "#FAFAF9",
    100: "#F5F5F4",
    200: "#E7E5E4",
    300: "#D6D3D1",
    400: "#A8A29E",
    500: "#78716C",
    600: "#57534E",
    700: "#44403C",
    800: "#292524",
    900: "#1C1917",
  },
};

const darkTokens: Tokens = {
  PRIMARY: "#8B85FF",
  PRIMARY_DARK: "#A5A0FF",
  PRIMARY_LIGHT: "#A5A0FF",
  PRIMARY_TINT: "#2B2560",

  SUCCESS: "#34D399",
  SUCCESS_TINT: "#0F3B2E",
  SUCCESS_ON_TINT: "#6EE7B7",
  WARNING: "#FBBF24",
  WARNING_TINT: "#3D2A0B",
  WARNING_ON_TINT: "#FCD34D",
  ERROR: "#F87171",
  ERROR_TINT: "#3F1717",
  ERROR_ON_TINT: "#FCA5A5",
  INFO: "#60A5FA",
  INFO_TINT: "#0F2A4D",
  INFO_ON_TINT: "#93C5FD",

  BG_DEFAULT: "#0B0B0E",
  BG_PAPER: "#131317",
  BG_SUBTLE: "#1A1A1F",
  BG_MUTED: "#22222A",
  BG_SUNKEN: "#0F0F13",

  TEXT_PRIMARY: "#F4F4F2",
  TEXT_SECONDARY: "#A8A29E",
  TEXT_MUTED: "#78716C",
  DIVIDER: "#2A2A31",
  BORDER: "#2A2A31",
  BORDER_HOVER: "#3B3B43",
  SCROLLBAR: "#3B3B43",
  SCROLLBAR_HOVER: "#57534E",

  SHADOW_XS: "0 1px 2px 0 rgba(0,0,0,0.5)",
  SHADOW_SM: "0 1px 3px 0 rgba(0,0,0,0.55), 0 1px 2px -1px rgba(0,0,0,0.4)",
  SHADOW_MD: "0 4px 10px -2px rgba(0,0,0,0.55), 0 2px 4px -2px rgba(0,0,0,0.4)",
  SHADOW_LG: "0 14px 28px -6px rgba(0,0,0,0.6), 0 4px 10px -4px rgba(0,0,0,0.45)",
  SHADOW_XL: "0 28px 56px -12px rgba(0,0,0,0.7)",

  TOOLTIP_BG: "#F5F5F4",
  TOOLTIP_FG: "#1C1917",

  GREY: {
    50: "#1C1917",
    100: "#292524",
    200: "#44403C",
    300: "#57534E",
    400: "#78716C",
    500: "#A8A29E",
    600: "#D6D3D1",
    700: "#E7E5E4",
    800: "#F5F5F4",
    900: "#FAFAF9",
  },
};

export function buildTheme(mode: ThemeMode): Theme {
  const t = mode === "dark" ? darkTokens : lightTokens;

  return createTheme({
    palette: {
      mode,
      primary: {
        main: t.PRIMARY,
        light: t.PRIMARY_LIGHT,
        dark: t.PRIMARY_DARK,
        contrastText: "#FFFFFF",
      },
      secondary: {
        main: "#0EA5E9",
        light: "#38BDF8",
        dark: "#0284C7",
        contrastText: "#FFFFFF",
      },
      success: {
        main: t.SUCCESS,
        light: "#34D399",
        dark: "#059669",
        contrastText: "#FFFFFF",
      },
      warning: {
        main: t.WARNING,
        light: "#FBBF24",
        dark: "#D97706",
        contrastText: "#FFFFFF",
      },
      error: {
        main: t.ERROR,
        light: "#F87171",
        dark: "#DC2626",
        contrastText: "#FFFFFF",
      },
      info: {
        main: t.INFO,
        light: "#60A5FA",
        dark: "#2563EB",
        contrastText: "#FFFFFF",
      },
      background: {
        default: t.BG_DEFAULT,
        paper: t.BG_PAPER,
      },
      text: {
        primary: t.TEXT_PRIMARY,
        secondary: t.TEXT_SECONDARY,
        disabled: t.TEXT_MUTED,
      },
      divider: t.DIVIDER,
      grey: t.GREY,
      brand: {
        violet: t.PRIMARY,
        violetTint: t.PRIMARY_TINT,
        teal: t.SUCCESS,
        tealTint: t.SUCCESS_TINT,
        amber: t.WARNING,
        amberTint: t.WARNING_TINT,
        rose: t.ERROR,
        roseTint: t.ERROR_TINT,
        sky: t.INFO,
        skyTint: t.INFO_TINT,
      },
      surface: {
        subtle: t.BG_SUBTLE,
        muted: t.BG_MUTED,
        sunken: t.BG_SUNKEN,
      },
      elevation: {
        xs: t.SHADOW_XS,
        sm: t.SHADOW_SM,
        md: t.SHADOW_MD,
        lg: t.SHADOW_LG,
        xl: t.SHADOW_XL,
      },
    },
    typography: {
      fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
      fontSize: 14,
      fontWeightRegular: 400,
      fontWeightMedium: 500,
      fontWeightBold: 600,
      h1: { fontSize: "2.5rem", fontWeight: 700, letterSpacing: "-0.025em", lineHeight: 1.15 },
      h2: { fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.2 },
      h3: { fontSize: "1.625rem", fontWeight: 700, letterSpacing: "-0.015em", lineHeight: 1.25 },
      h4: { fontSize: "1.375rem", fontWeight: 700, letterSpacing: "-0.01em", lineHeight: 1.3 },
      h5: { fontSize: "1.125rem", fontWeight: 600, letterSpacing: "-0.005em", lineHeight: 1.4 },
      h6: { fontSize: "1rem", fontWeight: 600, lineHeight: 1.5 },
      subtitle1: { fontSize: "0.9375rem", fontWeight: 500, lineHeight: 1.5 },
      subtitle2: { fontSize: "0.8125rem", fontWeight: 500, lineHeight: 1.5 },
      body1: { fontSize: "0.9375rem", lineHeight: 1.55 },
      body2: { fontSize: "0.875rem", lineHeight: 1.5 },
      caption: { fontSize: "0.75rem", lineHeight: 1.4, color: t.TEXT_SECONDARY },
      overline: {
        fontSize: "0.6875rem",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        lineHeight: 1.4,
      },
      button: { textTransform: "none", fontWeight: 600, letterSpacing: 0 },
    },
    shape: { borderRadius: 10 },
    shadows: [
      "none",
      t.SHADOW_XS,
      t.SHADOW_SM,
      t.SHADOW_SM,
      t.SHADOW_MD,
      t.SHADOW_MD,
      t.SHADOW_MD,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_LG,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
      t.SHADOW_XL,
    ],
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: t.BG_DEFAULT,
            color: t.TEXT_PRIMARY,
            WebkitFontSmoothing: "antialiased",
            MozOsxFontSmoothing: "grayscale",
          },
          "*::-webkit-scrollbar": { width: 10, height: 10 },
          "*::-webkit-scrollbar-track": { background: "transparent" },
          "*::-webkit-scrollbar-thumb": {
            background: t.SCROLLBAR,
            borderRadius: 8,
            border: "2px solid transparent",
            backgroundClip: "padding-box",
          },
          "*::-webkit-scrollbar-thumb:hover": {
            background: t.SCROLLBAR_HOVER,
            backgroundClip: "padding-box",
            border: "2px solid transparent",
          },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            borderRadius: 8,
            padding: "8px 16px",
            transition: "all 0.15s ease",
          },
          sizeSmall: { padding: "6px 12px", fontSize: "0.8125rem" },
          sizeLarge: { padding: "10px 20px", fontSize: "0.9375rem" },
          contained: {
            boxShadow: "none",
            "&:hover": { boxShadow: t.SHADOW_SM, transform: "translateY(-1px)" },
            "&:active": { transform: "translateY(0)" },
          },
          // @ts-expect-error MUI v9 doesn't type classname-style overrides but runtime supports them
          containedPrimary: {
            background: `linear-gradient(180deg, ${t.PRIMARY_LIGHT} 0%, ${t.PRIMARY} 100%)`,
            "&:hover": {
              background: `linear-gradient(180deg, ${t.PRIMARY} 0%, ${t.PRIMARY_DARK} 100%)`,
            },
          },
          outlined: {
            borderColor: t.BORDER,
            color: t.TEXT_PRIMARY,
            "&:hover": {
              borderColor: t.BORDER_HOVER,
              backgroundColor: t.BG_SUBTLE,
            },
          },
          text: {
            color: t.TEXT_SECONDARY,
            "&:hover": { backgroundColor: t.BG_SUBTLE, color: t.TEXT_PRIMARY },
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            transition: "all 0.15s ease",
            "&:hover": { backgroundColor: t.BG_SUBTLE },
          },
        },
      },
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            borderRadius: 14,
            border: `1px solid ${t.BORDER}`,
            backgroundColor: t.BG_PAPER,
            boxShadow: t.SHADOW_XS,
            transition: "box-shadow 0.2s ease, transform 0.2s ease",
          },
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: { padding: 24, "&:last-child": { paddingBottom: 24 } },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: "none" },
          rounded: { borderRadius: 12 },
          outlined: { borderColor: t.BORDER },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            fontWeight: 500,
            fontSize: "0.75rem",
            height: 24,
            letterSpacing: "0.005em",
          },
          sizeSmall: { height: 22, fontSize: "0.7rem" },
          colorPrimary: { backgroundColor: t.PRIMARY_TINT, color: t.PRIMARY_DARK },
          colorSuccess: { backgroundColor: t.SUCCESS_TINT, color: t.SUCCESS_ON_TINT },
          colorWarning: { backgroundColor: t.WARNING_TINT, color: t.WARNING_ON_TINT },
          colorError: { backgroundColor: t.ERROR_TINT, color: t.ERROR_ON_TINT },
          colorInfo: { backgroundColor: t.INFO_TINT, color: t.INFO_ON_TINT },
          colorDefault: { backgroundColor: t.BG_SUBTLE, color: t.TEXT_SECONDARY },
        },
      },
      MuiTextField: { defaultProps: { variant: "outlined" } },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            backgroundColor: t.BG_PAPER,
            transition: "border-color 0.15s ease, box-shadow 0.15s ease",
            "& fieldset": { borderColor: t.BORDER },
            "&:hover fieldset": { borderColor: t.BORDER_HOVER },
            "&.Mui-focused fieldset": { borderColor: t.PRIMARY, borderWidth: 1.5 },
            "&.Mui-focused": { boxShadow: `0 0 0 4px ${t.PRIMARY_TINT}` },
          },
          input: { padding: "10px 14px", fontSize: "0.9375rem" },
          // @ts-expect-error MUI v9 doesn't type classname-style overrides but runtime supports them
          inputSizeSmall: { padding: "8px 12px", fontSize: "0.875rem" },
        },
      },
      MuiInputLabel: {
        styleOverrides: {
          root: {
            fontSize: "0.9375rem",
            color: t.TEXT_SECONDARY,
            "&.Mui-focused": { color: t.PRIMARY_DARK },
          },
        },
      },
      MuiTable: { styleOverrides: { root: { borderCollapse: "separate", borderSpacing: 0 } } },
      MuiTableHead: {
        styleOverrides: {
          root: {
            backgroundColor: t.BG_SUBTLE,
            "& .MuiTableCell-root": {
              color: t.TEXT_SECONDARY,
              fontWeight: 600,
              fontSize: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              borderBottom: `1px solid ${t.BORDER}`,
              padding: "10px 16px",
            },
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            borderBottom: `1px solid ${t.BORDER}`,
            padding: "14px 16px",
            fontSize: "0.875rem",
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            transition: "background-color 0.12s ease",
            "&:last-child .MuiTableCell-root": { borderBottom: "none" },
            "&.MuiTableRow-hover:hover": { backgroundColor: t.BG_SUBTLE },
          },
        },
      },
      MuiDivider: { styleOverrides: { root: { borderColor: t.DIVIDER } } },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            transition: "background-color 0.12s ease, color 0.12s ease",
          },
        },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: {
            backgroundColor: t.TOOLTIP_BG,
            color: t.TOOLTIP_FG,
            fontSize: "0.75rem",
            fontWeight: 500,
            borderRadius: 6,
            padding: "6px 10px",
            boxShadow: t.SHADOW_MD,
          },
          arrow: { color: t.TOOLTIP_BG },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            padding: "10px 14px",
            fontSize: "0.875rem",
            alignItems: "center",
          },
          // @ts-expect-error MUI v9 doesn't type classname-style overrides but runtime supports them
          standardSuccess: {
            backgroundColor: t.SUCCESS_TINT,
            color: t.SUCCESS_ON_TINT,
            "& .MuiAlert-icon": { color: t.SUCCESS },
          },
          standardError: {
            backgroundColor: t.ERROR_TINT,
            color: t.ERROR_ON_TINT,
            "& .MuiAlert-icon": { color: t.ERROR },
          },
          standardWarning: {
            backgroundColor: t.WARNING_TINT,
            color: t.WARNING_ON_TINT,
            "& .MuiAlert-icon": { color: t.WARNING },
          },
          standardInfo: {
            backgroundColor: t.INFO_TINT,
            color: t.INFO_ON_TINT,
            "& .MuiAlert-icon": { color: t.INFO },
          },
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: { borderRadius: 999, backgroundColor: t.BG_MUTED, height: 6 },
          bar: { borderRadius: 999 },
        },
      },
      MuiSelect: { styleOverrides: { icon: { color: t.TEXT_SECONDARY } } },
      MuiMenu: {
        styleOverrides: {
          paper: {
            borderRadius: 10,
            border: `1px solid ${t.BORDER}`,
            boxShadow: t.SHADOW_LG,
          },
        },
      },
      MuiMenuItem: {
        styleOverrides: {
          root: {
            fontSize: "0.875rem",
            borderRadius: 6,
            margin: "2px 4px",
            minHeight: 36,
            "&:hover": { backgroundColor: t.BG_SUBTLE },
            "&.Mui-selected": {
              backgroundColor: t.PRIMARY_TINT,
              color: t.PRIMARY_DARK,
              "&:hover": { backgroundColor: t.PRIMARY_TINT },
            },
          },
        },
      },
      MuiAvatar: {
        styleOverrides: { root: { fontSize: "0.875rem", fontWeight: 600 } },
      },
      MuiAppBar: {
        defaultProps: { elevation: 0, color: "default" },
        styleOverrides: {
          root: {
            backgroundColor: t.BG_DEFAULT,
            color: t.TEXT_PRIMARY,
            borderBottom: `1px solid ${t.BORDER}`,
          },
        },
      },
      MuiToolbar: { styleOverrides: { root: { minHeight: 64 } } },
      MuiCircularProgress: { styleOverrides: { root: { color: t.PRIMARY } } },
    },
  });
}

const theme = buildTheme("light");
export default theme;
