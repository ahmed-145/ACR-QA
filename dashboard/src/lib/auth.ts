import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  user: { email: string; role: string } | null;
  setToken: (token: string, user: AuthState["user"]) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      setToken: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      isAuthenticated: () => !!get().token,
    }),
    { name: "acrqa_auth" }
  )
);

export async function loginApi(email: string, password: string) {
  const res = await fetch("/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  return res.json() as Promise<{ access_token: string; user: AuthState["user"] }>;
}

export function authHeader(): Record<string, string> {
  const token = useAuth.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
