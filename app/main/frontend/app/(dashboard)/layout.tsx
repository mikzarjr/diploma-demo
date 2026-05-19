"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Box } from "@mui/material";
import Sidebar from "@/components/Layout/Sidebar";
import { useAuth } from "@/context/AuthContext";
import { canAccess } from "@/lib/rbac";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname() || "/";

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!canAccess(pathname, user.role)) {
      router.replace("/");
    }
  }, [user, loading, pathname, router]);

  if (loading || !user) return null;
  if (!canAccess(pathname, user.role)) return null;

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minWidth: 0,
          pt: { xs: 2.5, md: 3.5 },
          px: { xs: 2.5, md: 4 },
          pb: 5,
          bgcolor: "background.default",
          minHeight: "100vh",
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
