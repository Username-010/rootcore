import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { AuthLayout } from "@/components/layout/auth-layout";
import { RequireAuth } from "@/components/require-auth";
import { AuthProvider } from "@/contexts/auth-context";
import { CalendarPage } from "@/pages/calendar-page";
import { CatalogPage } from "@/pages/catalog-page";
import { DashboardPage } from "@/pages/dashboard-page";
import { HouseholdPage } from "@/pages/household-page";
import { InvitePage } from "@/pages/invite-page";
import { LayoutPage } from "@/pages/layout-page";
import { LoginPage } from "@/pages/login-page";
import { PlantDetailPage } from "@/pages/plant-detail-page";
import { PlantFormPage } from "@/pages/plant-form-page";
import { PlantsPage } from "@/pages/plants-page";
import { RegisterPage } from "@/pages/register-page";
import { SettingsPage } from "@/pages/settings-page";
import { SetupPage } from "@/pages/setup-page";
import { StatsPage } from "@/pages/stats-page";
import { TasksPage } from "@/pages/tasks-page";
import { TimelinePage } from "@/pages/timeline-page";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/setup" element={<SetupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/invite/:token" element={<InvitePage />} />
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/plants" element={<PlantsPage />} />
              <Route path="/catalog" element={<CatalogPage />} />
              <Route path="/plants/new" element={<PlantFormPage />} />
              <Route path="/plants/:plantId" element={<PlantDetailPage />} />
              <Route path="/plants/:plantId/edit" element={<PlantFormPage />} />
              <Route path="/tasks" element={<TasksPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/layout" element={<LayoutPage />} />
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/stats" element={<StatsPage />} />
              <Route path="/household" element={<HouseholdPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
