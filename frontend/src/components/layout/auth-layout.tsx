import { Leaf } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { THEME_META, useTheme } from "@/hooks/use-theme";

export function AuthLayout() {
  const { theme, cycleTheme, meta } = useTheme();
  const info = meta[theme] ?? THEME_META.system;

  return (
    <div className="min-h-dvh flex flex-col">
      <header className="flex items-center justify-between px-4 py-5 max-w-lg mx-auto w-full">
        <Link to="/" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
            <Leaf className="h-5 w-5" aria-hidden />
          </span>
          <span className="font-semibold tracking-tight">RootCore</span>
        </Link>
        <Button variant="outline" size="sm" className="rounded-full" onClick={cycleTheme}>
          {info.emoji} {info.label}
        </Button>
      </header>
      <main className="flex flex-1 items-start justify-center px-4 pb-16 pt-2">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
