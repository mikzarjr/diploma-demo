"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { authApi } from "@/lib/api";
import { authStorage } from "@/lib/auth-storage";
import type { User } from "@/types";

interface AuthContextType {
  user: User | null;
  login: (phoneNumber: string, password: string) => Promise<User>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {
    throw new Error("AuthContext not initialized");
  },
  logout: () => {},
  loading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = authStorage.getUser();
    const access = authStorage.getAccess();
    if (stored && access) {
      setUser(stored);
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (phoneNumber: string, password: string) => {
    const res = await authApi.login(phoneNumber, password);
    authStorage.setTokens(res.access_token, res.refresh_token);
    authStorage.setUser(res.user);
    setUser(res.user);
    return res.user;
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

export function isHeadOrAdmin(user: User | null): boolean {
  return user?.role === "admin" || user?.role === "head";
}
