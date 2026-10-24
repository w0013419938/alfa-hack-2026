/** Маршруты. Клиент и сотрудник разведены: каждый видит только свой раздел. */
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { homePathFor, RequireRole } from "./auth/RequireRole";
import { Layout } from "./components/Layout";
import { LoadingState } from "./components/States";
import { BankApplicationPage } from "./pages/bank/BankApplicationPage";
import { QueuePage } from "./pages/bank/QueuePage";
import { StatsPage } from "./pages/bank/StatsPage";
import { ApplicationFormPage } from "./pages/client/ApplicationFormPage";
import { ApplicationPage } from "./pages/client/ApplicationPage";
import { HomePage } from "./pages/client/HomePage";
import { ProductsPage } from "./pages/client/ProductsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";

function RootRedirect() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <LoadingState />;
  return <Navigate to={user ? homePathFor(user.role) : "/login"} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<RootRedirect />} />
      <Route
        element={
          <RequireRole role="client">
            <Layout />
          </RequireRole>
        }
      >
        <Route path="/client" element={<HomePage />} />
        <Route path="/client/products" element={<ProductsPage />} />
        <Route path="/client/apply" element={<ApplicationFormPage />} />
        <Route path="/client/applications/:id/edit" element={<ApplicationFormPage />} />
        <Route path="/client/applications/:id" element={<ApplicationPage />} />
      </Route>
      <Route
        element={
          <RequireRole role="employee">
            <Layout />
          </RequireRole>
        }
      >
        <Route path="/bank" element={<QueuePage />} />
        <Route path="/bank/applications/:id" element={<BankApplicationPage />} />
        <Route path="/bank/stats" element={<StatsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
