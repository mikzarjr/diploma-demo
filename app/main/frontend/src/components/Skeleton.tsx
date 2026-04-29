"use client";

import { Box, Card, CardContent, Skeleton as MuiSkeleton } from "@mui/material";

export function Shimmer({
  width,
  height = 16,
  radius = 6,
  sx = {},
}: {
  width?: number | string;
  height?: number | string;
  radius?: number;
  sx?: Record<string, unknown>;
}) {
  return (
    <MuiSkeleton
      variant="rectangular"
      animation="wave"
      width={width}
      height={height}
      sx={{
        borderRadius: `${radius}px`,
        bgcolor: "surface.muted",
        ...sx,
      }}
    />
  );
}

export function StatCardsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", md: `repeat(${count}, 1fr)` },
        gap: 2.5,
        mb: 3,
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <Card key={i} sx={{ height: "100%" }}>
          <CardContent sx={{ p: 2.5 }}>
            <Box
              sx={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                mb: 2,
              }}
            >
              <Shimmer width={110} height={12} />
              <Shimmer width={36} height={36} radius={8} />
            </Box>
            <Shimmer width={80} height={28} sx={{ mb: 1 }} />
            <Shimmer width={140} height={12} />
          </CardContent>
        </Card>
      ))}
    </Box>
  );
}

export function TableRowSkeleton({ cols = 5 }: { cols?: number }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 2,
        alignItems: "center",
        py: 1.75,
        px: 2,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      {Array.from({ length: cols }).map((_, i) => (
        <Shimmer key={i} width={i === 0 ? 60 : "80%"} height={14} />
      ))}
    </Box>
  );
}

export function TableSkeleton({
  rows = 6,
  cols = 5,
  withHeader = true,
}: {
  rows?: number;
  cols?: number;
  withHeader?: boolean;
}) {
  return (
    <Card>
      {withHeader && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gap: 2,
            py: 1.5,
            px: 2,
            bgcolor: "surface.subtle",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          {Array.from({ length: cols }).map((_, i) => (
            <Shimmer key={i} width={70} height={10} />
          ))}
        </Box>
      )}
      {Array.from({ length: rows }).map((_, i) => (
        <TableRowSkeleton key={i} cols={cols} />
      ))}
    </Card>
  );
}

export function DetailCardSkeleton({ height = 200 }: { height?: number }) {
  return (
    <Card>
      <CardContent>
        <Shimmer width={160} height={16} sx={{ mb: 2 }} />
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.25 }}>
          <Shimmer width="100%" height={height * 0.2} />
          <Shimmer width="90%" height={height * 0.2} />
          <Shimmer width="95%" height={height * 0.2} />
          <Shimmer width="70%" height={height * 0.2} />
        </Box>
      </CardContent>
    </Card>
  );
}

export function CallDetailSkeleton() {
  return (
    <Box className="fade-in">
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          mb: 3,
        }}
      >
        <Shimmer width={40} height={40} radius={10} />
        <Box sx={{ flex: 1 }}>
          <Shimmer width={60} height={10} sx={{ mb: 0.5 }} />
          <Shimmer width={220} height={22} />
        </Box>
        <Shimmer width={100} height={24} radius={12} />
        <Shimmer width={180} height={32} radius={8} />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", md: "repeat(5, 1fr)" },
          gap: 2,
          mb: 2.5,
        }}
      >
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i}>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", gap: 1.5, alignItems: "center" }}>
                <Shimmer width={36} height={36} radius={8} />
                <Box sx={{ flex: 1 }}>
                  <Shimmer width={50} height={10} sx={{ mb: 0.5 }} />
                  <Shimmer width={70} height={14} />
                </Box>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "7fr 5fr" },
          gap: 2.5,
        }}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          <Card>
            <CardContent sx={{ py: 2.5 }}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <Shimmer width={48} height={48} radius={24} />
                <Shimmer width="100%" height={8} radius={4} />
              </Box>
            </CardContent>
          </Card>
          <DetailCardSkeleton height={240} />
        </Box>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          <DetailCardSkeleton height={160} />
          <DetailCardSkeleton height={200} />
        </Box>
      </Box>
    </Box>
  );
}
