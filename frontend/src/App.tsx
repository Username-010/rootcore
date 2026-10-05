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
import { WeekRoundPage } from "@/pages/week-round-page";
import { GardenWatchPage } from "@/pages/garden-watch-page";
import { DueCanPage } from "@/pages/due-can-page";
import { LabelsPage } from "@/pages/labels-page";
import { AwayPage } from "@/pages/away-page";
import { ShopPage } from "@/pages/shop-page";
import { CuttingsPage } from "@/pages/cuttings-page";
import { RepotPage } from "@/pages/repot-page";
import { FeedPage } from "@/pages/feed-page";
import { PrunePage } from "@/pages/prune-page";
import { MistPage } from "@/pages/mist-page";
import { DustPage } from "@/pages/dust-page";
import { RotatePage } from "@/pages/rotate-page";
import { PestPage } from "@/pages/pest-page";
import { StakePage } from "@/pages/stake-page";
import { HarvestPage } from "@/pages/harvest-page";
import { LightPage } from "@/pages/light-page";
import { FrostPage } from "@/pages/frost-page";
import { GroomPage } from "@/pages/groom-page";
import { FlushPage } from "@/pages/flush-page";
import { SplitPage } from "@/pages/split-page";
import { SowPage } from "@/pages/sow-page";
import { HardenPage } from "@/pages/harden-page";
import { MulchPage } from "@/pages/mulch-page";
import { TopdressPage } from "@/pages/topdress-page";
import { BottomPage } from "@/pages/bottom-page";

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
              <Route path="/round" element={<WeekRoundPage />} />
              <Route path="/watch" element={<GardenWatchPage />} />
              <Route path="/due" element={<DueCanPage />} />
              <Route path="/labels" element={<LabelsPage />} />
              <Route path="/away" element={<AwayPage />} />
              <Route path="/shop" element={<ShopPage />} />
              <Route path="/cuttings" element={<CuttingsPage />} />
              <Route path="/repot" element={<RepotPage />} />
              <Route path="/feed" element={<FeedPage />} />
              <Route path="/prune" element={<PrunePage />} />
              <Route path="/mist" element={<MistPage />} />
              <Route path="/dust" element={<DustPage />} />
              <Route path="/rotate" element={<RotatePage />} />
              <Route path="/pest" element={<PestPage />} />
              <Route path="/stake" element={<StakePage />} />
              <Route path="/harvest" element={<HarvestPage />} />
              <Route path="/light" element={<LightPage />} />
              <Route path="/frost" element={<FrostPage />} />
              <Route path="/groom" element={<GroomPage />} />
              <Route path="/flush" element={<FlushPage />} />
              <Route path="/split" element={<SplitPage />} />
              <Route path="/sow" element={<SowPage />} />
              <Route path="/harden" element={<HardenPage />} />
              <Route path="/mulch" element={<MulchPage />} />
              <Route path="/topdress" element={<TopdressPage />} />
              <Route path="/bottom" element={<BottomPage />} />
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
