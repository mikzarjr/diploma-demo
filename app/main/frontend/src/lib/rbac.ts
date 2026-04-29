export type Role = "admin" | "head" | "manager";

export interface RouteAccess {
  path: string;
  roles: Role[];
}

export const ROUTE_ACCESS: RouteAccess[] = [
  { path: "/", roles: ["admin", "head", "manager"] },
  { path: "/calls", roles: ["admin", "head", "manager"] },
  { path: "/upload", roles: ["admin", "head", "manager"] },
  { path: "/analytics", roles: ["admin", "head"] },
  { path: "/checks", roles: ["admin", "head"] },
  { path: "/users", roles: ["admin", "head"] },
  { path: "/integrations", roles: ["admin"] },
];

function normalizeRole(role: string | null | undefined): Role {
  if (role === "admin" || role === "head" || role === "manager") return role;
  return "manager";
}

export function canAccess(pathname: string, role: string | null | undefined): boolean {
  const r = normalizeRole(role);
  const match = ROUTE_ACCESS.find((item) => {
    if (item.path === "/") return pathname === "/";
    return pathname === item.path || pathname.startsWith(item.path + "/");
  });
  if (!match) return true;
  return match.roles.includes(r);
}

export function allowedRoutes(role: string | null | undefined): RouteAccess[] {
  const r = normalizeRole(role);
  return ROUTE_ACCESS.filter((item) => item.roles.includes(r));
}
