import type { User } from "@/types";

const USER_KEY = "ai_calls_user";

const isBrowser = () => typeof window !== "undefined";

export const authStorage = {
  getUser(): User | null {
    if (!isBrowser()) return null;
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },
  setUser(user: User) {
    if (!isBrowser()) return;
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
  clear() {
    if (!isBrowser()) return;
    localStorage.removeItem(USER_KEY);
  },
};
