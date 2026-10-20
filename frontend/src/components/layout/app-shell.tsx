import {
  Search,
  Radio,
  BarChart3,
  BookOpen,
  CalendarDays,
  ChevronDown,
  AlarmClock,
  Droplets,
  History,
  Home,
  LayoutGrid,
  Leaf,
  ListTodo,
  LogOut,
  Settings,
  Snowflake,
  Sprout,
  Flower2,
  Beaker,
  Scissors,
  CloudFog,
  Brush,
  RotateCw,
  Bug,
  Milestone,
  Wheat,
  Sun,
  CloudSnow,
  CloudRain,
  Split,
  Bean,
  Wind,
  Layers,
  CircleDot,
  Bath,
  Fan,
  Waves,
  Tag,
  Luggage,
  ShoppingBag,
  Users,
} from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { AmbientFx } from "@/components/ambient-fx";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { useAmbient } from "@/hooks/use-ambient";
import { THEME_META, useTheme } from "@/hooks/use-theme";
import { cn } from "@/lib/utils";

const PRIMARY = [
  { to: "/", icon: Home, label: "Today", end: true },
  { to: "/finder", icon: Search, label: "Find care" },
  { to: "/plants", icon: Sprout, label: "Plants" },
  { to: "/tasks", icon: ListTodo, label: "Tasks" },
] as const;

export const TOOL_GROUPS = [
  {
    title: "Care",
    items: [
      { to: "/round", icon: Droplets, label: "Round" },
      { to: "/sensors", icon: Radio, label: "Sensors" },
      { to: "/watch", icon: Snowflake, label: "Watch" },
      { to: "/due", icon: AlarmClock, label: "Due" },
    ],
  },
  {
    title: "Jobs",
    items: [
      { to: "/mist", icon: CloudFog, label: "Mist" },
      { to: "/dust", icon: Brush, label: "Dust" },
      { to: "/rotate", icon: RotateCw, label: "Rotate" },
      { to: "/prune", icon: Scissors, label: "Prune" },
      { to: "/groom", icon: Leaf, label: "Groom" },
      { to: "/pest", icon: Bug, label: "Pest" },
      { to: "/flush", icon: CloudRain, label: "Flush" },
      { to: "/light", icon: Sun, label: "Light" },
      { to: "/frost", icon: CloudSnow, label: "Frost" },
      { to: "/humidity", icon: Waves, label: "Humidity" },
      { to: "/air", icon: Fan, label: "Air" },
      { to: "/bottom", icon: Bath, label: "Bottom" },
    ],
  },
  {
    title: "Grow",
    items: [
      { to: "/feed", icon: Beaker, label: "Feed" },
      { to: "/repot", icon: Flower2, label: "Repot" },
      { to: "/cuttings", icon: Sprout, label: "Cuttings" },
      { to: "/sow", icon: Bean, label: "Sow" },
      { to: "/split", icon: Split, label: "Split" },
      { to: "/harden", icon: Wind, label: "Harden" },
      { to: "/stake", icon: Milestone, label: "Stake" },
      { to: "/harvest", icon: Wheat, label: "Harvest" },
      { to: "/mulch", icon: Layers, label: "Mulch" },
      { to: "/topdress", icon: CircleDot, label: "Topdress" },
    ],
  },
  {
    title: "Home",
    items: [
      { to: "/labels", icon: Tag, label: "Labels" },
      { to: "/away", icon: Luggage, label: "Away" },
      { to: "/shop", icon: ShoppingBag, label: "Shop" },
      { to: "/catalog", icon: BookOpen, label: "Catalog" },
      { to: "/layout", icon: LayoutGrid, label: "Map" },
      { to: "/calendar", icon: CalendarDays, label: "Calendar" },
      { to: "/stats", icon: BarChart3, label: "Stats" },
      { to: "/timeline", icon: History, label: "History" },
      { to: "/household", icon: Users, label: "Homes" },
      { to: "/settings", icon: Settings, label: "Settings" },
    ],
  },
] as const;

export function AppShell() {
  const { user, households, activeHousehold, setActiveHousehold, logout } = useAuth();
  const { theme, cycleTheme, meta } = useTheme();
  const { level: ambientLevel } = useAmbient();
  const themeInfo = meta[theme] ?? THEME_META.system;

  return (
    <div className="min-h-dvh flex flex-col relative">
      {ambientLevel > 0 && <AmbientFx intensity={ambientLevel} />}
      <header className="border-b border-border/80 bg-card/90 backdrop-blur-md sticky top-0 z-20 shadow-sm shadow-primary/5">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-primary/25">
              <Leaf className="h-5 w-5" aria-hidden />
            </span>
            <span className="font-semibold tracking-tight hidden sm:inline">RootCore</span>
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

        <nav
          className="hidden md:flex border-t border-border/60 mx-auto max-w-6xl px-2 py-1 gap-0.5 items-center"
          aria-label="Main"
        >
          {PRIMARY.map((item) => (
            <ShellNav key={item.to} {...item} />
          ))}
          <ToolMenu className="relative" />
        </nav>

        <nav
          className="relative md:hidden grid grid-cols-5 items-start border-t border-border/80 px-1 py-1"
          aria-label="Mobile"
        >
          {PRIMARY.map((item) => (
            <ShellNav key={item.to} {...item} mobile />
          ))}
          <ToolMenu className="contents" overlay />
        </nav>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-8">
        <Outlet />
      </main>

      <footer className="relative z-10 border-t border-border/60 py-4 text-center text-xs text-muted-foreground">
        RootCore · self-hosted · AGPL-3.0
      </footer>
    </div>
  );
}

function ToolMenu({ className, overlay }: { className?: string; overlay?: boolean }) {
  return (
    <details
      className={cn("group", className)}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest("a")) event.currentTarget.open = false;
      }}
    >
      <summary
        aria-label="More tools and pages"
        className={cn(
          "flex cursor-pointer list-none items-center gap-1 rounded-xl px-2.5 py-1.5 text-sm font-medium text-muted-foreground hover:bg-muted [&::-webkit-details-marker]:hidden",
          overlay && "min-h-11 flex-col gap-0.5 text-[11px] px-2",
        )}
      >
        <ChevronDown className="h-4 w-4 group-open:rotate-180" aria-hidden />
        More
      </summary>
      <div
        className={cn(
          "z-30 border border-border bg-card p-3 shadow-lg",
          overlay
            ? "absolute inset-x-0 top-full max-h-[70dvh] overflow-y-auto border-x-0 border-t-0"
            : "absolute right-0 top-full mt-1 w-[min(36rem,calc(100vw-2rem))] max-h-[70dvh] overflow-y-auto rounded-2xl",
        )}
      >
        <p className="mb-2 text-xs font-semibold text-muted-foreground">More tools and pages</p>
        <div className="grid gap-3 sm:grid-cols-2">
          {TOOL_GROUPS.map((group) => (
            <section key={group.title}>
              <h2 className="mb-1 px-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {group.title}
              </h2>
              <div className="grid grid-cols-2 gap-1">
                {group.items.map((item) => (
                  <ShellNav key={item.to} {...item} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </details>
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
