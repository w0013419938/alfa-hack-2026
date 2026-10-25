/** Кто вошёл в систему. Токен хранится в localStorage, данные пользователя берутся из GET /auth/me. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useState, type ReactNode } from "react";

import { api, call, tokenStore, type Schemas } from "../api/client";

type User = Schemas["UserOut"];

type AuthState = {
  user: User | null;
  isLoading: boolean;
  login: (login: string, password: string) => Promise<User>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [hasToken, setHasToken] = useState(Boolean(tokenStore.get()));

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => call(api.GET("/api/v1/auth/me")),
    enabled: hasToken,
    retry: false,
    staleTime: Infinity,
  });

  async function login(login: string, password: string): Promise<User> {
    const result = await call(api.POST("/api/v1/auth/login", { body: { login, password } }));
    tokenStore.set(result.access_token);
    queryClient.clear(); // данные прошлого пользователя не должны мелькнуть у нового
    queryClient.setQueryData(["me"], result.user);
    setHasToken(true);
    return result.user;
  }

  function logout() {
    tokenStore.clear();
    queryClient.clear();
    setHasToken(false);
  }

  const user = hasToken ? (me.data ?? null) : null;
  return (
    <AuthContext.Provider value={{ user, isLoading: hasToken && me.isLoading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth нужно вызывать внутри AuthProvider");
  return value;
}
