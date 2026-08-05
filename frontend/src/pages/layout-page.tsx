import {
  type DragEvent,
  type FormEvent,
  type MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { LayoutContainer, LayoutSite, LayoutSpace } from "@/lib/types";

type FlatSpace = LayoutSpace & {
  siteId: string;
  siteName: string;
};

type DragPayload =
  | { kind: "plant"; plantId: string; nickname: string }
  | { kind: "pot"; containerId: string };

const DEFAULT_POT = 56;
const SNAP = 24;

type ShapeKind = "circle" | "square" | "rect" | "triangle" | "line";

function normalizeShape(kind: string | null | undefined): ShapeKind {
  if (kind === "square" || kind === "bed") return "square";
  if (kind === "rect" || kind === "rectangle") return "rect";
  if (kind === "triangle") return "triangle";
  if (kind === "line") return "line";
  return "circle";
}

function shapeLabel(kind: string | null | undefined) {
  const s = normalizeShape(kind);
  return { circle: "Circle", square: "Square", rect: "Rectangle", triangle: "Triangle", line: "Line" }[
    s
  ];
}

export function LayoutPage() {
  const { activeHousehold } = useAuth();
  const navigate = useNavigate();
  const [sites, setSites] = useState<LayoutSite[]>([]);
  const [unassigned, setUnassigned] = useState<Array<{ id: string; nickname: string }>>([]);
  const [plantNames, setPlantNames] = useState<Record<string, string>>({});
  const [plantEmojis, setPlantEmojis] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedSpaceId, setSelectedSpaceId] = useState("");
  const [selectedPotId, setSelectedPotId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newAreaName, setNewAreaName] = useState("");
  const [lengthM, setLengthM] = useState("8");
  const [widthM, setWidthM] = useState("5");
  const [mode, setMode] = useState<"select" | "add-pot" | "freehand">("select");
  const [drawShape, setDrawShape] = useState<ShapeKind>("circle");
  const [snapOn, setSnapOn] = useState(true);
  const [freehandPts, setFreehandPts] = useState<number[][]>([]);
  const freehandRef = useRef<number[][]>([]);
  const drawingRef = useRef(false);
  const mapRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [hoverPotId, setHoverPotId] = useState<string | null>(null);
  const [selectedPlantId, setSelectedPlantId] = useState<string | null>(null);
  /** Live drag preview positions (optimistic) */
  const [livePos, setLivePos] = useState<Record<string, { x: number; y: number }>>({});
  const livePosRef = useRef<Record<string, { x: number; y: number }>>({});
  const pointerDrag = useRef<null | {
    kind: "pot" | "plant";
    id: string;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  }>(null);

  const load = useCallback(async () => {
    if (!activeHousehold) return;
    setError(null);
    try {
      const [s, u, p] = await Promise.all([
        api.listSites(activeHousehold.id),
        api.unassignedPlants(activeHousehold.id),
        api.listPlants(activeHousehold.id, { limit: 100 }),
      ]);
      setSites(s);
      setUnassigned(u);
      const map: Record<string, string> = {};
      const em: Record<string, string> = {};
      for (const plant of p.items) {
        map[plant.id] = plant.nickname;
        const e =
          plant.emoji ||
          (typeof plant.custom_attributes?.emoji === "string"
            ? plant.custom_attributes.emoji
            : null);
        if (e) em[plant.id] = e;
      }
      setPlantNames(map);
      setPlantEmojis(em);
      setLivePos({});
      setSelectedSpaceId((prev) => {
        if (prev && s.some((site) => site.spaces.some((sp) => sp.id === prev))) return prev;
        return s[0]?.spaces[0]?.id ?? "";
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to load layout");
    }
  }, [activeHousehold]);

  useEffect(() => {
    void load();
  }, [load]);

  const spaces: FlatSpace[] = useMemo(
    () =>
      sites.flatMap((site) =>
        site.spaces.map((sp) => ({
          ...sp,
          siteId: site.id,
          siteName: site.name,
        })),
      ),
    [sites],
  );

  const active = spaces.find((s) => s.id === selectedSpaceId) ?? null;

  const potPlantMap = useMemo(() => {
    const m = new Map<string, string[]>();
    if (!active) return m;
    for (const pl of active.placements) {
      if (!pl.container_id) continue;
      const list = m.get(pl.container_id) ?? [];
      list.push(pl.plant_id);
      m.set(pl.container_id, list);
    }
    return m;
  }, [active]);

  const freePlacements = useMemo(
    () => (active ? active.placements.filter((p) => !p.container_id) : []),
    [active],
  );

  // Every plant currently on this map (in pots or free)
  const placedHere = useMemo(() => {
    if (!active) return [] as Array<{ plantId: string; potName: string | null }>;
    const potNames = new Map(active.containers.map((c) => [c.id, c.name]));
    return active.placements.map((pl) => ({
      plantId: pl.plant_id,
      potName: pl.container_id ? potNames.get(pl.container_id) ?? "Pot" : null,
    }));
  }, [active]);

  const selectedPot = active?.containers.find((c) => c.id === selectedPotId) ?? null;
  const selectedPotPlants = selectedPotId ? potPlantMap.get(selectedPotId) ?? [] : [];
  const hoverPot = active?.containers.find((c) => c.id === hoverPotId) ?? null;
  const hoverPlants = hoverPotId ? potPlantMap.get(hoverPotId) ?? [] : [];

  if (!activeHousehold) {
    return (
      <Card>
        <CardContent className="py-10 text-center space-y-3">
          <p className="font-medium">No household selected</p>
          <Button asChild>
            <Link to="/household">Households</Link>
          </Button>
        </CardContent>
      </Card>
    );
  }

  async function addSite(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData(e.currentTarget);
      const name = String(form.get("name") || "Home").trim() || "Home";
      const L = Number(lengthM) || 8;
      const W = Number(widthM) || 5;
      const site = await api.createSite(activeHousehold.id, name, {
        default_room: "Garden",
        default_kind: "garden",
        length_m: L,
        width_m: W,
      });
      if (site.space_id) setSelectedSpaceId(site.space_id);
      e.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create home");
    } finally {
      setBusy(false);
    }
  }

  async function addArea(siteId: string) {
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    try {
      const name = newAreaName.trim() || "New garden bed";
      const space = await api.createSpace(activeHousehold.id, siteId, name, {
        kind: "garden",
        length_m: Number(lengthM) || 6,
        width_m: Number(widthM) || 4,
      });
      setSelectedSpaceId(space.id);
      setNewAreaName("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create area");
    } finally {
      setBusy(false);
    }
  }

  async function removeArea(spaceId: string, name: string) {
    if (!activeHousehold) return;
    if (
      !confirm(
        `Delete room/area “${name}”? Pots on this map are removed. Plants stay in your collection (unassigned from the map).`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.deleteSpace(activeHousehold.id, spaceId);
      if (selectedSpaceId === spaceId) setSelectedSpaceId("");
      setSelectedPotId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete area");
    } finally {
      setBusy(false);
    }
  }

  async function removeSite(siteId: string, name: string) {
    if (!activeHousehold) return;
    if (
      !confirm(
        `Delete entire map “${name}” and all its rooms? Plants stay in your collection.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.deleteSite(activeHousehold.id, siteId);
      setSelectedSpaceId("");
      setSelectedPotId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not delete map");
    } finally {
      setBusy(false);
    }
  }

  async function saveDimensions() {
    if (!activeHousehold || !active) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateSpace(activeHousehold.id, active.id, {
        length_m: Number(lengthM) || null,
        width_m: Number(widthM) || null,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save dimensions");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (active?.length_m) setLengthM(String(active.length_m));
    if (active?.width_m) setWidthM(String(active.width_m));
  }, [active?.id, active?.length_m, active?.width_m]);

  function snap(v: number) {
    if (!snapOn) return v;
    return Math.round(v / SNAP) * SNAP;
  }

  function mapCoords(e: { clientX: number; clientY: number }): { x: number; y: number } | null {
    const el = mapRef.current;
    if (!el || !active) return null;
    const rect = el.getBoundingClientRect();
    const scaleX = active.canvas_width / rect.width;
    const scaleY = active.canvas_height / rect.height;
    let x = Math.max(0, Math.min(active.canvas_width - 24, (e.clientX - rect.left) * scaleX));
    let y = Math.max(0, Math.min(active.canvas_height - 24, (e.clientY - rect.top) * scaleY));
    x = snap(x);
    y = snap(y);
    return { x, y };
  }

  async function onMapClick(e: ReactMouseEvent) {
    if (!activeHousehold || !active || mode !== "add-pot") return;
    const coords = mapCoords(e);
    if (!coords) return;
    setBusy(true);
    setError(null);
    try {
      const n = active.containers.length + 1;
      const w =
        drawShape === "rect" ? DEFAULT_POT * 1.6 : drawShape === "line" ? DEFAULT_POT * 1.8 : DEFAULT_POT;
      const h =
        drawShape === "rect" ? DEFAULT_POT * 0.9 : drawShape === "line" ? 14 : DEFAULT_POT;
      const pot = await api.createContainer(activeHousehold.id, active.id, {
        name:
          drawShape === "line"
            ? `Line ${n}`
            : drawShape === "triangle"
              ? `Bed ${n}`
              : drawShape === "rect"
                ? `Plot ${n}`
                : `Pot ${n}`,
        kind: drawShape,
        x: coords.x,
        y: coords.y,
        width: w,
        height: h,
      });
      setSelectedPotId(pot.id);
      setMode("select");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not add pot");
    } finally {
      setBusy(false);
    }
  }

  function onFreehandDown(e: ReactMouseEvent) {
    if (mode !== "freehand" || !active) return;
    e.preventDefault();
    drawingRef.current = true;
    const coords = mapCoords(e);
    if (coords) {
      freehandRef.current = [[coords.x, coords.y]];
      setFreehandPts([[coords.x, coords.y]]);
    }
  }

  function onFreehandMove(e: ReactMouseEvent) {
    if (mode !== "freehand" || !drawingRef.current) return;
    const coords = mapCoords(e);
    if (!coords) return;
    const prev = freehandRef.current;
    if (prev.length === 0) {
      freehandRef.current = [[coords.x, coords.y]];
      setFreehandPts([[coords.x, coords.y]]);
      return;
    }
    const last = prev[prev.length - 1];
    const dist = Math.hypot(coords.x - last[0], coords.y - last[1]);
    if (dist < (snapOn ? SNAP * 0.4 : 8)) return;
    freehandRef.current = [...prev, [coords.x, coords.y]];
    setFreehandPts(freehandRef.current);
  }

  async function onFreehandUp() {
    if (mode !== "freehand" || !drawingRef.current) return;
    drawingRef.current = false;
    const pts = freehandRef.current;
    if (!activeHousehold || !active || pts.length < 3) {
      freehandRef.current = [];
      setFreehandPts([]);
      return;
    }
    const path = [...pts, pts[0]];
    setBusy(true);
    setError(null);
    try {
      const n = active.containers.length + 1;
      const pot = await api.createContainer(activeHousehold.id, active.id, {
        name: `Custom bed ${n}`,
        kind: "polygon",
        path_json: path,
      });
      setSelectedPotId(pot.id);
      freehandRef.current = [];
      setFreehandPts([]);
      setMode("select");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save freehand bed");
      freehandRef.current = [];
      setFreehandPts([]);
    } finally {
      setBusy(false);
    }
  }

  async function movePot(containerId: string, x: number, y: number) {
    if (!activeHousehold || !active) return;
    const key = "pot:" + containerId;
    livePosRef.current = { ...livePosRef.current, [key]: { x, y } };
    setLivePos(livePosRef.current);
    try {
      await api.updateContainer(activeHousehold.id, containerId, { x, y });
      const plants = potPlantMap.get(containerId) ?? [];
      await Promise.all(
        plants.map((pid) =>
          api.putPlacement(activeHousehold.id, pid, {
            space_id: active.id,
            container_id: containerId,
            x,
            y,
          }),
        ),
      );
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not move pot");
      const n = { ...livePosRef.current };
      delete n[key];
      livePosRef.current = n;
      setLivePos(n);
    }
  }

  function startPointerMove(
    kind: "pot" | "plant",
    id: string,
    origX: number,
    origY: number,
    e: ReactMouseEvent,
  ) {
    if (mode !== "select") return;
    e.preventDefault();
    e.stopPropagation();
    pointerDrag.current = {
      kind,
      id,
      startX: e.clientX,
      startY: e.clientY,
      origX,
      origY,
    };
    if (kind === "pot") setSelectedPotId(id);
    else setSelectedPlantId(id);
  }

  function onMapPointerMove(e: ReactMouseEvent) {
    if (mode === "freehand") {
      onFreehandMove(e);
      return;
    }
    const d = pointerDrag.current;
    if (!d || !active || !mapRef.current) return;
    const rect = mapRef.current.getBoundingClientRect();
    const scaleX = active.canvas_width / rect.width;
    const scaleY = active.canvas_height / rect.height;
    let nx = d.origX + (e.clientX - d.startX) * scaleX;
    let ny = d.origY + (e.clientY - d.startY) * scaleY;
    nx = Math.max(0, Math.min(active.canvas_width - 20, snap(nx)));
    ny = Math.max(0, Math.min(active.canvas_height - 20, snap(ny)));
    const key = d.kind + ":" + d.id;
    livePosRef.current = { ...livePosRef.current, [key]: { x: nx, y: ny } };
    setLivePos(livePosRef.current);
  }

  async function onMapPointerUp() {
    if (mode === "freehand") {
      await onFreehandUp();
      return;
    }
    const d = pointerDrag.current;
    pointerDrag.current = null;
    if (!d || !activeHousehold || !active) return;
    const key = d.kind + ":" + d.id;
    const pos = livePosRef.current[key];
    if (!pos) return;
    if (Math.hypot(pos.x - d.origX, pos.y - d.origY) < 4) {
      const n = { ...livePosRef.current };
      delete n[key];
      livePosRef.current = n;
      setLivePos(n);
      return;
    }
    if (d.kind === "pot") await movePot(d.id, pos.x, pos.y);
    else {
      try {
        await api.putPlacement(activeHousehold.id, d.id, {
          space_id: active.id,
          container_id: null,
          x: pos.x,
          y: pos.y,
        });
        await load();
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : "Could not move plant");
        const n = { ...livePosRef.current };
        delete n[key];
        livePosRef.current = n;
        setLivePos(n);
      }
    }
  }

  function potDisplayPos(pot: LayoutContainer) {
    const live = livePos["pot:" + pot.id];
    return { x: live?.x ?? pot.x, y: live?.y ?? pot.y };
  }

  async function resizePot(containerId: string, size: number, shape?: ShapeKind) {
    if (!activeHousehold) return;
    const s = Math.max(28, Math.min(200, size));
    const sh = shape ?? normalizeShape(selectedPot?.kind);
    try {
      const width = sh === "rect" || sh === "line" ? Math.round(s * 1.7) : s;
      const height = sh === "line" ? 14 : sh === "rect" ? Math.round(s * 0.85) : s;
      await api.updateContainer(activeHousehold.id, containerId, { width, height });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not resize");
    }
  }

  async function setPotShape(containerId: string, shape: ShapeKind) {
    if (!activeHousehold) return;
    try {
      const base = Math.round(Number(selectedPot?.width ?? selectedPot?.height ?? DEFAULT_POT));
      const width = shape === "rect" || shape === "line" ? Math.round(base * 1.7) : base;
      const height = shape === "line" ? 14 : shape === "rect" ? Math.round(base * 0.85) : base;
      await api.updateContainer(activeHousehold.id, containerId, {
        kind: shape,
        width,
        height,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not change shape");
    }
  }

  async function copyPot(containerId: string) {
    if (!activeHousehold) return;
    setBusy(true);
    try {
      const c = await api.copyContainer(activeHousehold.id, containerId);
      setSelectedPotId(c.id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not copy pot");
    } finally {
      setBusy(false);
    }
  }

  async function assignPlantToPot(plantId: string, containerId: string) {
    if (!activeHousehold || !active) return;
    setBusy(true);
    try {
      await api.putPlacement(activeHousehold.id, plantId, {
        space_id: active.id,
        container_id: containerId,
      });
      setSelectedPotId(containerId);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not place plant");
    } finally {
      setBusy(false);
    }
  }

  async function placeFreePlant(plantId: string, x: number, y: number) {
    if (!activeHousehold || !active) return;
    setBusy(true);
    try {
      await api.putPlacement(activeHousehold.id, plantId, {
        space_id: active.id,
        container_id: null,
        x,
        y,
      });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not place plant");
    } finally {
      setBusy(false);
    }
  }

  async function unassignPlant(plantId: string) {
    if (!activeHousehold) return;
    setBusy(true);
    setError(null);
    try {
      await api.removePlacement(activeHousehold.id, plantId);
      if (selectedPlantId === plantId) setSelectedPlantId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not remove from map");
    } finally {
      setBusy(false);
    }
  }

  async function removePot(containerId: string) {
    if (!activeHousehold) return;
    const pot = active?.containers.find((c) => c.id === containerId);
    const label = pot?.name || "this pot/bed";
    if (
      !confirm(
        `Remove “${label}”? Plants stay on the map (no longer in this pot). Freehand beds are deleted permanently.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.deleteContainer(activeHousehold.id, containerId);
      if (selectedPotId === containerId) setSelectedPotId(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not remove pot");
    } finally {
      setBusy(false);
    }
  }

  function onDragStart(e: DragEvent, payload: DragPayload) {
    e.dataTransfer.setData("application/plantpilot", JSON.stringify(payload));
    e.dataTransfer.effectAllowed = "move";
  }

  async function onMapDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (!activeHousehold || !active) return;
    const raw = e.dataTransfer.getData("application/plantpilot");
    if (!raw) return;
    const payload = JSON.parse(raw) as DragPayload;
    const coords = mapCoords(e);
    if (!coords) return;

    const hit = active.containers.find((c) => {
      const w = c.width ?? DEFAULT_POT;
      const h = c.height ?? DEFAULT_POT;
      return coords.x >= c.x && coords.x <= c.x + w && coords.y >= c.y && coords.y <= c.y + h;
    });

    if (payload.kind === "plant") {
      if (hit) await assignPlantToPot(payload.plantId, hit.id);
      else await placeFreePlant(payload.plantId, coords.x, coords.y);
    } else if (payload.kind === "pot") {
      await movePot(payload.containerId, coords.x, coords.y);
    }
  }

  const dimLabel =
    active?.length_m && active?.width_m
      ? `${active.length_m} m × ${active.width_m} m`
      : "size not set";

  const potSize = selectedPot
    ? Math.round(Number(selectedPot.width ?? selectedPot.height ?? DEFAULT_POT))
    : DEFAULT_POT;

  return (
    <div className="space-y-5">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Garden map</h1>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Hover pots for names · click to edit size/shape · drag plants into pots (several per pot).
        </p>
      </header>

      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {sites.length === 0 ? (
        <Card className="max-w-lg">
          <CardHeader>
            <CardTitle>Create your first garden map</CardTitle>
            <CardDescription>
              Name your home and set bed dimensions in metres.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={(e) => void addSite(e)}>
              <div className="space-y-1.5">
                <Label htmlFor="home">Home name</Label>
                <Input id="home" name="name" placeholder="Home" defaultValue="Home" required />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="len">Length (m)</Label>
                  <Input
                    id="len"
                    type="number"
                    min={0.5}
                    step={0.5}
                    value={lengthM}
                    onChange={(e) => setLengthM(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="wid">Width (m)</Label>
                  <Input
                    id="wid"
                    type="number"
                    min={0.5}
                    step={0.5}
                    value={widthM}
                    onChange={(e) => setWidthM(e.target.value)}
                  />
                </div>
              </div>
              <Button type="submit" disabled={busy} className="rounded-xl w-full">
                {busy ? "Creating…" : "Create garden map"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[220px_1fr_240px]">
          <div className="space-y-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Areas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {sites.map((site) => (
                  <div key={site.id} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground truncate">
                        {site.name}
                      </p>
                      <button
                        type="button"
                        className="text-[10px] text-destructive hover:underline shrink-0"
                        disabled={busy}
                        title="Delete this map and all rooms"
                        onClick={() => void removeSite(site.id, site.name)}
                      >
                        Delete map
                      </button>
                    </div>
                    <ul className="space-y-1">
                      {site.spaces.map((sp) => (
                        <li key={sp.id} className="flex items-stretch gap-0.5">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedSpaceId(sp.id);
                              setSelectedPotId(null);
                            }}
                            className={
                              "flex min-w-0 flex-1 items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm " +
                              (selectedSpaceId === sp.id
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted/60 hover:bg-muted")
                            }
                          >
                            <span className="truncate font-medium">
                              {sp.kind === "garden" ? "🌿 " : "🏠 "}
                              {sp.name}
                            </span>
                            <span className="text-xs opacity-80">{sp.containers.length}</span>
                          </button>
                          <button
                            type="button"
                            className={
                              "shrink-0 rounded-lg px-1.5 text-xs " +
                              (selectedSpaceId === sp.id
                                ? "text-primary-foreground/90 hover:bg-primary-foreground/15"
                                : "text-destructive hover:bg-destructive/10")
                            }
                            disabled={busy}
                            title={`Delete “${sp.name}”`}
                            aria-label={`Delete ${sp.name}`}
                            onClick={() => void removeArea(sp.id, sp.name)}
                          >
                            ✕
                          </button>
                        </li>
                      ))}
                    </ul>
                    <div className="flex gap-1 pt-1">
                      <Input
                        value={newAreaName}
                        onChange={(e) => setNewAreaName(e.target.value)}
                        placeholder="New room / bed"
                        className="h-8 text-xs"
                      />
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-8 shrink-0"
                        disabled={busy}
                        onClick={() => void addArea(site.id)}
                      >
                        Add
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Dimensions</CardTitle>
                <CardDescription className="text-xs">{dimLabel}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs">Length m</Label>
                    <Input
                      type="number"
                      min={0.5}
                      step={0.5}
                      value={lengthM}
                      onChange={(e) => setLengthM(e.target.value)}
                      className="h-8"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Width m</Label>
                    <Input
                      type="number"
                      min={0.5}
                      step={0.5}
                      value={widthM}
                      onChange={(e) => setWidthM(e.target.value)}
                      className="h-8"
                    />
                  </div>
                </div>
                <Button
                  size="sm"
                  className="w-full rounded-xl"
                  disabled={busy || !active}
                  onClick={() => void saveDimensions()}
                >
                  Apply size
                </Button>
              </CardContent>
            </Card>
          </div>

          <Card className="min-h-[28rem] overflow-hidden">
            <CardHeader className="pb-2 flex-row items-center justify-between space-y-0 gap-2">
              <div>
                <CardTitle className="text-base">
                  {active ? `${active.siteName} · ${active.name}` : "Select an area"}
                </CardTitle>
                <CardDescription className="text-xs">
                  {mode === "add-pot"
                    ? `Click map to place a ${shapeLabel(drawShape).toLowerCase()}`
                    : "Hover for names · click shape to edit · click plant name to open"}
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-1 shrink-0">
                <Button
                  size="sm"
                  variant={snapOn ? "default" : "outline"}
                  className="rounded-xl h-8 text-xs"
                  onClick={() => setSnapOn((v) => !v)}
                  title="Snap to grid when placing/moving"
                >
                  {snapOn ? "Snap on" : "Snap off"}
                </Button>
                <Button
                  size="sm"
                  variant={mode === "add-pot" ? "default" : "outline"}
                  className="rounded-xl h-8"
                  disabled={!active || busy}
                  onClick={() => {
                    setMode((m) => (m === "add-pot" ? "select" : "add-pot"));
                    setFreehandPts([]);
                  }}
                >
                  {mode === "add-pot" ? "Cancel" : "+ Shape"}
                </Button>
                <Button
                  size="sm"
                  variant={mode === "freehand" ? "default" : "outline"}
                  className="rounded-xl h-8"
                  disabled={!active || busy}
                  onClick={() => {
                    setMode((m) => (m === "freehand" ? "select" : "freehand"));
                    setFreehandPts([]);
                  }}
                  title="Draw L-shaped, U-shaped, or any custom bed freehand"
                >
                  {mode === "freehand" ? "Cancel draw" : "✎ Freehand"}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {mode === "add-pot" && (
                <div className="flex flex-wrap gap-1">
                  {(
                    [
                      ["circle", "● Circle"],
                      ["square", "■ Square"],
                      ["rect", "▭ Rect"],
                      ["triangle", "▲ Triangle"],
                      ["line", "— Line"],
                    ] as const
                  ).map(([k, label]) => (
                    <Button
                      key={k}
                      size="sm"
                      variant={drawShape === k ? "default" : "outline"}
                      className="h-7 rounded-lg text-xs"
                      onClick={() => setDrawShape(k)}
                    >
                      {label}
                    </Button>
                  ))}
                </div>
              )}
              {mode === "freehand" && (
                <p className="text-xs text-muted-foreground">
                  Hold and drag to draw any outline (L, U, freeform). Release to create a bed.
                </p>
              )}
              {!active ? (
                <p className="text-sm text-muted-foreground">Create or select an area.</p>
              ) : (
                <div
                  ref={mapRef}
                  className={
                    "relative mx-auto overflow-hidden rounded-xl border-2 " +
                    (mode === "add-pot" || mode === "freehand"
                      ? "cursor-crosshair border-primary"
                      : "border-primary/40") +
                    (dragOver ? " ring-2 ring-primary/50" : "")
                  }
                  style={{
                    width: "100%",
                    maxWidth: 720,
                    aspectRatio: `${active.canvas_width} / ${active.canvas_height}`,
                    // Soft soil / path tone — sits better with UI chrome
                    backgroundColor: "oklch(0.93 0.02 95)",
                    backgroundImage: [
                      "radial-gradient(ellipse 90% 70% at 50% 45%, oklch(0.9 0.035 130 / 0.55), transparent 65%)",
                      "linear-gradient(165deg, oklch(0.94 0.02 100), oklch(0.88 0.03 120))",
                      "repeating-linear-gradient(0deg,transparent,transparent 23px,oklch(0.55 0.02 100 / 0.07) 24px)",
                      "repeating-linear-gradient(90deg,transparent,transparent 23px,oklch(0.55 0.02 100 / 0.07) 24px)",
                    ].join(","),
                    boxShadow:
                      "inset 0 0 0 2px oklch(0.75 0.03 100 / 0.5), 0 8px 28px oklch(0.35 0.03 100 / 0.1)",
                  }}
                  onClick={(e) => void onMapClick(e)}
                  onMouseDown={(e) => {
                    if (mode === "freehand") onFreehandDown(e);
                  }}
                  onMouseMove={onMapPointerMove}
                  onMouseUp={() => void onMapPointerUp()}
                  onMouseLeave={() => {
                    if (drawingRef.current || pointerDrag.current) void onMapPointerUp();
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => void onMapDrop(e)}
                >
                  {active.length_m && active.width_m && (
                    <>
                      <span className="pointer-events-none absolute left-1/2 top-1 z-20 -translate-x-1/2 rounded bg-background/85 px-1.5 py-0.5 text-[10px] font-medium tabular-nums shadow-sm">
                        {active.length_m} m
                      </span>
                      <span className="pointer-events-none absolute left-1 top-1/2 z-20 -translate-y-1/2 -rotate-90 origin-left rounded bg-background/85 px-1.5 py-0.5 text-[10px] font-medium tabular-nums shadow-sm">
                        {active.width_m} m
                      </span>
                    </>
                  )}

                  {freehandPts.length > 1 && (
                    <svg
                      className="pointer-events-none absolute inset-0 z-[8] h-full w-full"
                      viewBox={`0 0 ${active.canvas_width} ${active.canvas_height}`}
                      preserveAspectRatio="none"
                    >
                      <polyline
                        points={freehandPts.map((p) => p.join(",")).join(" ")}
                        fill="color-mix(in oklch, var(--color-primary) 20%, transparent)"
                        stroke="var(--color-primary)"
                        strokeWidth={3}
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                    </svg>
                  )}

                  <svg
                    className="absolute inset-0 z-[6] h-full w-full"
                    viewBox={`0 0 ${active.canvas_width} ${active.canvas_height}`}
                    preserveAspectRatio="none"
                  >
                    {active.containers
                      .filter((c) => c.path_json && c.path_json.length >= 3)
                      .map((c) => (
                        <polygon
                          key={"poly-" + c.id}
                          points={c.path_json!.map((p) => p.join(",")).join(" ")}
                          fill={
                            selectedPotId === c.id
                              ? "color-mix(in oklch, var(--color-primary) 40%, transparent)"
                              : "color-mix(in oklch, var(--color-primary) 22%, transparent)"
                          }
                          stroke="var(--color-primary)"
                          strokeWidth={selectedPotId === c.id ? 3 : 2}
                          className="cursor-pointer"
                          style={{ pointerEvents: "auto" }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedPotId(c.id);
                          }}
                          onMouseEnter={() => setHoverPotId(c.id)}
                          onMouseLeave={() => setHoverPotId(null)}
                        />
                      ))}
                  </svg>

                  {active.containers.map((pot) => {
                    const pos = potDisplayPos(pot);
                    const potDraw = { ...pot, x: pos.x, y: pos.y };
                    return (
                      <PotMarker
                        key={pot.id}
                        pot={potDraw}
                        plantIds={potPlantMap.get(pot.id) ?? []}
                        plantNames={plantNames}
                        plantEmojis={plantEmojis}
                        selected={selectedPotId === pot.id}
                        hovered={hoverPotId === pot.id}
                        canvasW={active.canvas_width}
                        canvasH={active.canvas_height}
                        onSelect={() => setSelectedPotId(pot.id)}
                        onHover={(on) => setHoverPotId(on ? pot.id : null)}
                        onPointerDown={(e) =>
                          startPointerMove("pot", pot.id, pot.x, pot.y, e)
                        }
                        onDragStart={(e) =>
                          onDragStart(e, { kind: "pot", containerId: pot.id })
                        }
                      />
                    );
                  })}

                  {/* Hover floating card — clamped so it never falls off the edge */}
                  {hoverPot && hoverPotId && (
                    <div
                      className="pointer-events-none absolute z-30 w-[10.5rem] rounded-lg border border-border bg-card/95 px-2.5 py-2 text-xs shadow-lg backdrop-blur-sm"
                      style={{
                        left: `${Math.min(
                          72,
                          Math.max(
                            4,
                            ((hoverPot.x + (hoverPot.width ?? DEFAULT_POT) / 2) /
                              active.canvas_width) *
                              100 -
                              12,
                          ),
                        )}%`,
                        top: `${Math.min(
                          72,
                          Math.max(
                            4,
                            ((hoverPot.y + (hoverPot.height ?? DEFAULT_POT)) /
                              active.canvas_height) *
                              100 +
                              1,
                          ),
                        )}%`,
                      }}
                    >
                      <p className="font-semibold leading-tight truncate">{hoverPot.name}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {shapeLabel(hoverPot.kind)} · {Math.round(hoverPot.width ?? DEFAULT_POT)}px
                      </p>
                      {hoverPlants.length === 0 ? (
                        <p className="mt-1 text-muted-foreground">Empty</p>
                      ) : (
                        <ul className="mt-1 space-y-0.5">
                          {hoverPlants.slice(0, 5).map((pid) => (
                            <li key={pid} className="truncate">
                              🌱 {plantNames[pid] || "Plant"}
                            </li>
                          ))}
                          {hoverPlants.length > 5 && (
                            <li className="text-muted-foreground">
                              +{hoverPlants.length - 5} more
                            </li>
                          )}
                        </ul>
                      )}
                    </div>
                  )}

                  {freePlacements.map((pl) => {
                    const sel = selectedPlantId === pl.plant_id;
                    const live = livePos["plant:" + pl.plant_id];
                    const px = live?.x ?? pl.x;
                    const py = live?.y ?? pl.y;
                    return (
                      <div
                        key={pl.id}
                        draggable
                        onDragStart={(e) =>
                          onDragStart(e, {
                            kind: "plant",
                            plantId: pl.plant_id,
                            nickname: plantNames[pl.plant_id] || "Plant",
                          })
                        }
                        onMouseDown={(e) => {
                          startPointerMove("plant", pl.plant_id, pl.x, pl.y, e);
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedPlantId(pl.plant_id);
                          setSelectedPotId(null);
                        }}
                        onDoubleClick={(e) => {
                          e.stopPropagation();
                          navigate("/plants/" + pl.plant_id);
                        }}
                        className={
                          "absolute z-[5] group flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 cursor-grab flex-col items-center justify-center rounded-2xl border-2 bg-card/95 text-base shadow-md active:cursor-grabbing " +
                          (sel
                            ? "border-primary ring-2 ring-primary/40 z-20"
                            : "border-emerald-800/25 hover:border-primary/50")
                        }
                        style={{
                          left: `${(px / active.canvas_width) * 100}%`,
                          top: `${(py / active.canvas_height) * 100}%`,
                        }}
                      >
                        {plantEmojis[pl.plant_id] || "🌱"}
                        <span className="pointer-events-none absolute -bottom-6 left-1/2 z-20 hidden -translate-x-1/2 whitespace-nowrap rounded bg-card px-1.5 py-0.5 text-[10px] font-medium shadow group-hover:block">
                          {plantNames[pl.plant_id]}
                        </span>
                        {sel && (
                          <button
                            type="button"
                            title="Remove from map"
                            className="absolute -right-1 -top-1 z-30 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-[10px] font-bold text-destructive-foreground shadow"
                            onClick={(e) => {
                              e.stopPropagation();
                              void unassignPlant(pl.plant_id);
                            }}
                          >
                            ×
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="space-y-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">In this garden</CardTitle>
                <CardDescription className="text-xs">
                  Remove a plant from the map anytime — it returns to Unassigned.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {placedHere.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No plants on this map yet.</p>
                ) : (
                  <ul className="max-h-44 space-y-1 overflow-auto">
                    {placedHere.map(({ plantId, potName }) => (
                      <li
                        key={plantId}
                        className={
                          "flex items-center justify-between gap-1 rounded-lg border px-2 py-1.5 text-sm " +
                          (selectedPlantId === plantId
                            ? "border-primary bg-primary/5"
                            : "border-border bg-card")
                        }
                      >
                        <button
                          type="button"
                          className="min-w-0 flex-1 text-left"
                          onClick={() => {
                            setSelectedPlantId(plantId);
                            setSelectedPotId(null);
                          }}
                        >
                          <span className="block truncate font-medium">
                            {plantNames[plantId] || "Plant"}
                          </span>
                          <span className="block text-[10px] text-muted-foreground">
                            {potName ? `in ${potName}` : "on map (no pot)"}
                          </span>
                        </button>
                        <div className="flex shrink-0 items-center gap-1">
                          <Link
                            to={"/plants/" + plantId}
                            className="text-[10px] text-primary hover:underline"
                          >
                            open
                          </Link>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 rounded-lg px-2 text-xs text-destructive"
                            disabled={busy}
                            title="Remove from garden"
                            onClick={() => void unassignPlant(plantId)}
                          >
                            Remove
                          </Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Unassigned</CardTitle>
                <CardDescription className="text-xs">
                  Not on any map yet. Drag onto a pot or the garden.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {unassigned.length === 0 ? (
                  <p className="text-xs text-muted-foreground">All plants are placed.</p>
                ) : (
                  <ul className="max-h-40 space-y-1 overflow-auto">
                    {unassigned.map((p) => (
                      <li key={p.id}>
                        <div
                          draggable={!busy}
                          onDragStart={(e) =>
                            onDragStart(e, {
                              kind: "plant",
                              plantId: p.id,
                              nickname: p.nickname,
                            })
                          }
                          className="cursor-grab rounded-lg border border-border bg-card px-2 py-1.5 text-sm active:cursor-grabbing"
                        >
                          {p.nickname}
                          {selectedPot && (
                            <button
                              type="button"
                              className="ml-2 text-[10px] text-primary underline"
                              onClick={() => void assignPlantToPot(p.id, selectedPot.id)}
                            >
                              → pot
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            {active && active.containers.length > 0 && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Pots &amp; beds</CardTitle>
                  <CardDescription className="text-xs">
                    Click a freehand shape on the map or a row below. Remove deletes the bed.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 max-h-48 overflow-y-auto">
                    {active.containers.map((c) => {
                      const n = potPlantMap.get(c.id)?.length ?? 0;
                      const poly = Boolean(c.path_json && c.path_json.length >= 3);
                      return (
                        <li
                          key={c.id}
                          className={
                            "flex items-center gap-1 rounded-lg border px-2 py-1.5 text-sm " +
                            (selectedPotId === c.id
                              ? "border-primary bg-primary/10"
                              : "border-border")
                          }
                        >
                          <button
                            type="button"
                            className="min-w-0 flex-1 text-left truncate"
                            onClick={() => setSelectedPotId(c.id)}
                          >
                            {poly ? "✎ " : ""}
                            {c.name}
                            <span className="text-xs text-muted-foreground">
                              {" "}
                              · {n} plant{n === 1 ? "" : "s"}
                            </span>
                          </button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 shrink-0 rounded-lg px-2 text-xs text-destructive"
                            disabled={busy}
                            onClick={() => void removePot(c.id)}
                          >
                            Remove
                          </Button>
                        </li>
                      );
                    })}
                  </ul>
                </CardContent>
              </Card>
            )}

            {selectedPot && (
              <Card className="border-primary/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Selected pot</CardTitle>
                  <CardDescription className="text-xs">
                    {selectedPot.path_json && selectedPot.path_json.length >= 3
                      ? "Freehand bed"
                      : shapeLabel(selectedPot.kind)}{" "}
                    · {selectedPotPlants.length} plant
                    {selectedPotPlants.length === 1 ? "" : "s"}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <Label className="text-xs">Name</Label>
                    <Input
                      className="h-8 text-sm"
                      defaultValue={selectedPot.name}
                      key={selectedPot.id + "-name"}
                      onBlur={(e) => {
                        const v = e.target.value.trim();
                        if (v && v !== selectedPot.name && activeHousehold) {
                          void api
                            .updateContainer(activeHousehold.id, selectedPot.id, { name: v })
                            .then(load);
                        }
                      }}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Pot / bed emoji</Label>
                    <div className="flex flex-wrap gap-1">
                      {["🪴", "🪣", "📦", "🪨", "🪵", "🌾", "🏞️", "🌳", "▢", "●"].map((em) => (
                        <button
                          key={em}
                          type="button"
                          className={
                            "h-8 w-8 rounded-lg border text-sm " +
                            (selectedPot.emoji === em
                              ? "border-primary bg-primary/10"
                              : "border-border hover:bg-muted")
                          }
                          onClick={() => {
                            if (!activeHousehold) return;
                            void api
                              .updateContainer(activeHousehold.id, selectedPot.id, {
                                emoji: em,
                              })
                              .then(load);
                          }}
                        >
                          {em}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="h-8 px-2 rounded-lg border border-border text-[10px] text-muted-foreground"
                        onClick={() => {
                          if (!activeHousehold) return;
                          void api
                            .updateContainer(activeHousehold.id, selectedPot.id, {
                              emoji: "",
                            })
                            .then(load);
                        }}
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  {!(selectedPot.path_json && selectedPot.path_json.length >= 3) && (
                    <>
                      <div className="space-y-1">
                        <Label className="text-xs">Shape</Label>
                        <div className="grid grid-cols-2 gap-1">
                          {(
                            [
                              ["circle", "● Circle"],
                              ["square", "■ Square"],
                              ["rect", "▭ Rect"],
                              ["triangle", "▲ Triangle"],
                              ["line", "— Line"],
                            ] as const
                          ).map(([k, label]) => (
                            <Button
                              key={k}
                              size="sm"
                              variant={
                                normalizeShape(selectedPot.kind) === k ? "default" : "outline"
                              }
                              className="rounded-xl h-8 text-xs"
                              onClick={() => void setPotShape(selectedPot.id, k)}
                            >
                              {label}
                            </Button>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-1">
                        <Label className="text-xs">Size ({potSize}px)</Label>
                        <input
                          type="range"
                          min={32}
                          max={160}
                          step={4}
                          value={potSize}
                          className="w-full accent-primary"
                          onChange={(e) => void resizePot(selectedPot.id, Number(e.target.value))}
                        />
                        <div className="flex justify-between text-[10px] text-muted-foreground">
                          <span>Small</span>
                          <span>Big plant / bed</span>
                        </div>
                      </div>
                    </>
                  )}

                  {selectedPotPlants.length === 0 ? (
                    <p className="text-xs text-muted-foreground">Drop plants here from Unassigned.</p>
                  ) : (
                    <ul className="space-y-1">
                      {selectedPotPlants.map((pid) => (
                        <li
                          key={pid}
                          className="flex items-center justify-between gap-1 rounded-lg bg-muted/50 px-2 py-1 text-sm"
                        >
                          <Link
                            to={"/plants/" + pid}
                            className="truncate font-medium text-primary hover:underline"
                            title="Open plant"
                          >
                            {plantNames[pid] || "Plant"} →
                          </Link>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 rounded-lg px-2 text-xs text-destructive"
                            disabled={busy}
                            onClick={() => void unassignPlant(pid)}
                          >
                            Remove
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}

                  <div className="flex flex-col gap-1.5">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="w-full rounded-xl"
                      disabled={busy}
                      onClick={() => void copyPot(selectedPot.id)}
                    >
                      Copy pot
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full rounded-xl text-destructive"
                      onClick={() => void removePot(selectedPot.id)}
                    >
                      Remove pot
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function PotMarker({
  pot,
  plantIds,
  plantNames,
  plantEmojis,
  selected,
  hovered,
  canvasW,
  canvasH,
  onSelect,
  onHover,
  onDragStart,
  onPointerDown,
}: {
  pot: LayoutContainer;
  plantIds: string[];
  plantNames: Record<string, string>;
  plantEmojis: Record<string, string>;
  selected: boolean;
  hovered: boolean;
  canvasW: number;
  canvasH: number;
  onSelect: () => void;
  onHover: (on: boolean) => void;
  onDragStart: (e: DragEvent) => void;
  onPointerDown: (e: ReactMouseEvent) => void;
}) {
  const w = pot.width ?? DEFAULT_POT;
  const h = pot.height ?? DEFAULT_POT;
  const shape = normalizeShape(pot.kind);
  const isPoly = Boolean(pot.path_json && pot.path_json.length >= 3);
  const label =
    plantIds.length === 0
      ? pot.name
      : plantIds.length === 1
        ? plantNames[plantIds[0]] || pot.name
        : `${pot.name} (${plantIds.length})`;

  const icon =
    pot.emoji ||
    (plantIds.length === 1 && plantEmojis[plantIds[0]]) ||
    (shape === "triangle"
      ? "▲"
      : shape === "line"
        ? "—"
        : shape === "rect"
          ? "▭"
          : shape === "square"
            ? "▣"
            : isPoly
              ? "✎"
              : "🪴");

  // Freehand polygons: center handle (outline drawn as clickable SVG)
  if (isPoly) {
    const cx = pot.x + w / 2;
    const cy = pot.y + h / 2;
    return (
      <button
        type="button"
        draggable
        onDragStart={onDragStart}
        onMouseDown={onPointerDown}
        onMouseEnter={() => onHover(true)}
        onMouseLeave={() => onHover(false)}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        className={
          "absolute z-10 flex h-11 min-w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 bg-card/95 px-2 text-base font-bold shadow-md cursor-grab active:cursor-grabbing " +
          (selected ? "border-primary ring-2 ring-primary/40 scale-110" : "border-emerald-800/30")
        }
        style={{
          left: `${(cx / canvasW) * 100}%`,
          top: `${(cy / canvasH) * 100}%`,
        }}
        aria-label={label + " — drag to move"}
        title="Drag to move · click to select"
      >
        {icon}
      </button>
    );
  }

  const radius =
    shape === "circle"
      ? "9999px"
      : shape === "square"
        ? "10px"
        : shape === "rect"
          ? "8px"
          : shape === "line"
            ? "3px"
            : "0";

  return (
    <button
      type="button"
      draggable
      onDragStart={onDragStart}
      onMouseDown={onPointerDown}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      className={
        "absolute z-10 flex flex-col items-center justify-center border-2 bg-card/95 text-center shadow-md cursor-grab active:cursor-grabbing " +
        (selected
          ? "border-primary ring-2 ring-primary/40 scale-105 z-20"
          : hovered
            ? "border-primary/60 shadow-lg"
            : "border-stone-400/50 hover:border-primary/45")
      }
      style={{
        left: `${(pot.x / canvasW) * 100}%`,
        top: `${(pot.y / canvasH) * 100}%`,
        width: `${(w / canvasW) * 100}%`,
        height: `${(h / canvasH) * 100}%`,
        minWidth: shape === "line" ? 40 : 32,
        minHeight: shape === "line" ? 10 : 32,
        borderRadius: radius,
        clipPath: shape === "triangle" ? "polygon(50% 0%, 0% 100%, 100% 100%)" : undefined,
      }}
      aria-label={label}
      title="Drag to move"
    >
      <span className="text-base leading-none">{icon}</span>
      {shape !== "line" && plantIds.length > 0 && (
        <span className="max-w-full truncate px-0.5 text-[9px] font-semibold leading-tight text-muted-foreground">
          {plantIds.length === 1
            ? (plantNames[plantIds[0]] || "").slice(0, 8)
            : plantIds.length}
        </span>
      )}
    </button>
  );
}
