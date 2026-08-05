import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/contexts/auth-context";

export function RequireAuth() {
  const { user, loading, initialized } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (initialized === false) {
    return <Navigate to="/setup" replace />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
