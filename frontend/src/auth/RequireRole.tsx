/** Пускает на маршрут только пользователя нужной роли. Остальных отправляет на вход или в «свой» кабинет. */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { LoadingState } from "../components/States";
import { useAuth } from "./AuthContext";

export function homePathFor(role: string | undefined): string {
  return role === "employee" ? "/bank" : "/client";
}

export function RequireRole({ role, children }: { role: "client" | "employee"; children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingState text="Проверяем вход…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== role) return <Navigate to={homePathFor(user.role)} replace />;
  return <>{children}</>;
}
