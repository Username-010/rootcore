import { useMemo } from "react";

import { useAmbient } from "@/hooks/use-ambient";

const EMOJIS = ["🦋", "🐝", "🦋", "🐝", "🌸", "🍃", "🦋", "🌼", "🐝", "🍃", "🌺", "🦋"];

/** Soft decorative ambient graphics — mountains, zen garden, bees & butterflies. */
export function AmbientFx({ intensity }: { intensity?: number } = {}) {
  const ambient = useAmbient();
  // Prefer explicit prop; otherwise live level from shared hook (0 = none)
  const level = intensity !== undefined ? intensity : ambient.level;

  const flyers = useMemo(() => {
    // 0 → none; 1 → 1; 100 → ~28 critters
    const count = level <= 0 ? 0 : Math.max(1, Math.round((level / 100) * 28));
    const items: Array<{
      id: number;
      emoji: string;
      top: number;
      left: number;
      size: number;
      duration: number;
      delay: number;
      opacity: number;
    }> = [];
    for (let i = 0; i < count; i++) {
      // Deterministic spread so React doesn't reshuffle every render
      const seed = (i + 1) * 17.13 + level * 0.31;
      const top = 8 + ((seed * 37) % 70);
      const left = -12 - ((seed * 11) % 18);
      const size = 0.75 + ((seed * 3) % 50) / 100;
      // Higher intensity → slightly faster flights
      const baseDur = 42 - (level / 100) * 18;
      const duration = baseDur + ((seed * 5) % 14);
      const delay = -((seed * 9) % duration);
      const opacity = 0.28 + (level / 100) * 0.4 + ((i % 5) * 0.04);
      items.push({
        id: i,
        emoji: EMOJIS[i % EMOJIS.length],
        top,
        left,
        size,
        duration,
        delay,
        opacity: Math.min(0.85, opacity),
      });
    }
    return items;
  }, [level]);

  // Subtle scenery always when level > 0 (or when master on with low intensity)
  if (level <= 0) return null;

  const sceneryOpacity = 0.06 + (level / 100) * 0.1;

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden
    >
      <div
        className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-t from-primary/8 via-primary/3 to-transparent"
        style={{ opacity: 0.5 + level / 200 }}
      />
      <div className="absolute -left-10 bottom-8 h-24 w-48 rounded-[100%] bg-muted/40 blur-2xl" />
      <div className="absolute right-0 bottom-12 h-32 w-56 rounded-[100%] bg-primary/10 blur-3xl" />
      <div className="absolute left-1/3 top-24 h-40 w-40 rounded-full bg-primary/5 blur-3xl" />

      <svg
        className="absolute bottom-0 left-0 w-full h-36 text-foreground"
        style={{ opacity: sceneryOpacity }}
        viewBox="0 0 1200 140"
        preserveAspectRatio="none"
      >
        <path
          fill="currentColor"
          d="M0 140 L0 95 L100 55 L200 90 L320 30 L450 85 L580 25 L700 80 L820 20 L940 75 L1060 40 L1200 85 L1200 140 Z"
        />
        <path
          fill="currentColor"
          opacity="0.55"
          d="M0 140 L0 110 L140 70 L260 105 L400 55 L540 100 L680 60 L820 95 L980 50 L1120 90 L1200 75 L1200 140 Z"
        />
      </svg>

      <svg
        className="absolute bottom-2 right-4 w-48 h-24 text-foreground hidden sm:block"
        style={{ opacity: sceneryOpacity * 0.9 }}
        viewBox="0 0 200 100"
      >
        <ellipse cx="100" cy="70" rx="70" ry="22" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <ellipse cx="100" cy="70" rx="50" ry="14" fill="none" stroke="currentColor" strokeWidth="1" />
        <ellipse cx="100" cy="70" rx="30" ry="8" fill="none" stroke="currentColor" strokeWidth="1" />
        <circle cx="100" cy="68" r="6" fill="currentColor" opacity="0.4" />
        <circle cx="70" cy="78" r="4" fill="currentColor" opacity="0.3" />
        <circle cx="128" cy="76" r="3.5" fill="currentColor" opacity="0.3" />
      </svg>

      {flyers.map((f) => (
        <span
          key={f.id}
          className="pp-fly"
          style={{
            top: `${f.top}%`,
            left: `${f.left}%`,
            fontSize: `${f.size}rem`,
            opacity: f.opacity,
            animationDuration: `${f.duration}s`,
            animationDelay: `${f.delay}s`,
          }}
        >
          {f.emoji}
        </span>
      ))}
    </div>
  );
}

export function FlowerLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12" role="status">
      <div className="pp-loader-row">
        <span className="pp-bloom">🌱</span>
        <span className="pp-bloom">🌿</span>
        <span className="pp-bloom">🌸</span>
        <span className="pp-bloom">🌺</span>
        <span className="pp-bloom">🌼</span>
      </div>
      <p className="text-sm text-muted-foreground animate-pulse">{label}</p>
    </div>
  );
}
