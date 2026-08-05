import {
  BarChart3,
  BookOpen,
  CalendarDays,
  ChevronDown,
  History,
  Home,
  LayoutGrid,
  Leaf,
  ListTodo,
  LogOut,
  Settings,
  Sprout,
  Users,
} from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { AmbientFx } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useAmbient } from "@/hooks/use-ambient";
import { THEME_META, useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

export function AppShell() {
  const { user, households, activeHousehold, setActiveHousehold, logout } = useAuth();
  const { theme, cycleTheme, meta } = useTheme();
  const { level: ambientLevel } = useAmbient();
  const themeInfo = meta[theme] ?? THEME_META.system;

  return (
    <div className="min-h-dvh flex flex-col relative">
      {ambientLevel > 0 && <AmbientFx intensity={ambientLevel} />}
      <header className="border-b border-border/80 bg-card/90 backdrop-blur-md sticky top-0 z-20 shadow-sm shadow-primary/5">
        {/* Row 1: brand + household + actions */}
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25">
              <Leaf className="h-5 w-5" aria-hidden />
            </span>
            <span className="font-semibold tracking-tight hidden sm:inline">PlantPilot</span>
          </Link>

          {households.length > 0 && (
            <div className="flex items-center gap-1 min-w-0">
              <label className="relative min-w-0 max-w-[10rem] sm:max-w-[13rem]">
                <span className="sr-only">Active home</span>
                <select
                  className="h-8 w-full appearance-none rounded-full border border-border/80 bg-background/90 pl-3 pr-7 text-sm font-medium truncate"
                  value={activeHousehold?.id ?? ""}
                  onChange={(e) => {
                    const h = households.find((x) => x.id === e.target.value);
                    if (h) setActiveHousehold(h);
                  }}
                  title="Switch home"
                >
                  {households.map((h) => (
                    <option key={h.id} value={h.id}>
                      {h.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              </label>
              <Link
                to="/household"
                className="hidden sm:inline text-xs text-primary hover:underline shrink-0 px-1"
                title="Add, rename, or manage homes"
              >
                Manage
              </Link>
            </div>
          )}

          <div className="ml-auto flex items-center gap-1 shrink-0">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full h-8 px-2.5 gap-1"
              onClick={cycleTheme}
              aria-label={`Theme: ${themeInfo.label}`}
              title={`Theme: ${themeInfo.label}`}
            >
              <span className="text-sm leading-none">{themeInfo.emoji}</span>
              <span className="hidden md:inline text-xs max-w-[5rem] truncate">{themeInfo.label}</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full h-8 w-8"
              onClick={() => void logout()}
              aria-label="Log out"
              title={user ? `Log out (${user.display_name})` : "Log out"}
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Row 2: primary nav — full width, no overlap with household */}
        <nav
          className="hidden md:flex border-t border-border/60 mx-auto max-w-6xl px-2 py-1 gap-0.5 overflow-x-auto"
          aria-label="Main"
        >
          <ShellNav to="/" icon={Home} label="Today" end />
          <ShellNav to="/plants" icon={Sprout} label="Plants" />
          <ShellNav to="/catalog" icon={BookOpen} label="Catalog" />
          <ShellNav to="/layout" icon={LayoutGrid} label="Map" />
          <ShellNav to="/calendar" icon={CalendarDays} label="Calendar" />
          <ShellNav to="/tasks" icon={ListTodo} label="Tasks" />
          <ShellNav to="/stats" icon={BarChart3} label="Stats" />
          <ShellNav to="/timeline" icon={History} label="History" />
          <ShellNav to="/household" icon={Users} label="Homes" />
          <ShellNav to="/settings" icon={Settings} label="Settings" />
        </nav>

        {/* Mobile nav */}
        <nav
          className="md:hidden flex border-t border-border/80 px-1 py-1 gap-0.5 justify-around overflow-x-auto"
          aria-label="Mobile"
        >
          <ShellNav to="/" icon={Home} label="Today" end mobile />
          <ShellNav to="/plants" icon={Sprout} label="Plants" mobile />
          <ShellNav to="/catalog" icon={BookOpen} label="Catalog" mobile />
          <ShellNav to="/layout" icon={LayoutGrid} label="Map" mobile />
          <ShellNav to="/settings" icon={Settings} label="More" mobile />
        </nav>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-8">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-border/60 py-4 text-center text-xs text-muted-foreground">
        PlantPilot · self-hosted · AGPL-3.0
      </footer>
    </div>
  );
}

function ShellNav({
  to,
  icon: Icon,
  label,
  end,
  mobile,
}: {
  to: string;
  icon: typeof Home;
  label: string;
  end?: boolean;
  mobile?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          "inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-sm font-medium transition-colors whitespace-nowrap shrink-0",
          mobile && "flex-col gap-0.5 px-2.5 py-1.5 text-[11px] min-w-[3.25rem]",
          isActive
            ? "bg-primary/12 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {label}
    </NavLink>
  );
}
