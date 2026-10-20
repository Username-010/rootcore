export type SensorReading = { entity_id: string; name: string; value: number | null; unit: string | null; timestamp: string | null; metric: string; status: string };

/** Source-time plot. Unavailable samples and unit changes break the line. */
export function SensorChart({ points }: { points: SensorReading[] }) {
  if (!points.length) return <p className="py-8 text-muted-foreground">No recorded history. Home Assistant Recorder may not retain this entity yet.</p>;
  const valid = points.filter(p => p.value !== null && Number.isFinite(p.value) && p.timestamp && Number.isFinite(Date.parse(p.timestamp)));
  const values = valid.map(p => p.value as number);
  const times = valid.map(p => Date.parse(p.timestamp!));
  const low = Math.min(...values), high = Math.max(...values);
  const start = Math.min(...times), end = Math.max(...times);
  const x = (p: SensorReading) => 30 + (Date.parse(p.timestamp!) - start) / (end - start || 1) * 740;
  const y = (p: SensorReading) => 170 - ((p.value as number) - low) / (high - low || 1) * 130;
  const segments: SensorReading[][] = [];
  let segment: SensorReading[] = [];
  for (const p of points) {
    if (!valid.includes(p) || (segment.length && segment[0].unit !== p.unit)) {
      if (segment.length) segments.push(segment);
      segment = [];
    }
    if (valid.includes(p)) segment.push(p);
  }
  if (segment.length) segments.push(segment);
  return <div className="space-y-3">
    {valid.length ? <figure>
      <svg viewBox="0 0 800 210" role="img" aria-label="Recorded sensor values over source time" className="w-full rounded-xl bg-muted/30 text-primary">
        <line x1="30" x2="780" y1="175" y2="175" stroke="currentColor" opacity="0.2" />
        {segments.filter(s => s.length > 1).map((s, i) => <polyline key={i} fill="none" stroke="currentColor" strokeWidth="2" points={s.map(p => `${x(p)},${y(p)}`).join(" ")} />)}
        {valid.map((p, i) => <circle key={i} cx={x(p)} cy={y(p)} r="3" fill="currentColor"><title>{`${p.timestamp}: ${p.value} ${p.unit ?? ""}`}</title></circle>)}
        <text x="30" y="20" fill="currentColor" fontSize="12">{high} / {low} · source units below</text>
      </svg>
      <figcaption className="text-xs text-muted-foreground">{new Date(start).toLocaleString()} — {new Date(end).toLocaleString()}. Gaps are not zero. Lines connect recorded samples, not continuous measurements.</figcaption>
    </figure> : <p>No numeric readings in this window. Unknown or unavailable values are not zero.</p>}
    <details><summary className="cursor-pointer text-sm font-medium">Recorded values ({points.length})</summary>
      <div className="max-h-64 overflow-auto"><table className="w-full text-sm"><thead><tr><th className="text-left">Source timestamp</th><th className="text-left">Value</th><th className="text-left">State</th></tr></thead>
        <tbody>{points.map((p, i) => <tr key={i} className="border-t"><td>{p.timestamp ?? "Not provided"}</td><td>{p.value === null ? "—" : `${p.value} ${p.unit ?? ""}`}</td><td>{p.status}</td></tr>)}</tbody></table></div>
    </details>
  </div>;
}
