import { useEffect, useRef, useState } from 'react';

export interface ColumnChartRow {
  label: string;
  value: number;
  /** false = de-emphasized (muted) bar — e.g. outside the window this chart is highlighting. */
  emphasis?: boolean;
  tip?: string;
}

export interface ColumnChartProps {
  rows: ColumnChartRow[];
  axisLabel: string;
  valueFmt?: (v: number) => string;
  /** Show an x-axis label every Nth bar, to avoid crowding. */
  xEvery?: number;
  tableHeaders?: string[];
  tableRows?: (string | number)[][];
}

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}

/** A bar: 4px rounded data-end, square baseline — the dataviz skill's mark spec for columns. */
function colPath(x: number, yTop: number, w: number, yBase: number, r: number): string {
  const rr = Math.max(0, Math.min(r, w / 2, yBase - yTop));
  return `M${x},${yBase}V${yTop + rr}Q${x},${yTop} ${x + rr},${yTop}H${x + w - rr}Q${x + w},${yTop} ${x + w},${yTop + rr}V${yBase}Z`;
}

/** Single-series vertical columns — magnitude over a categorical (hourly) axis, with a hover tooltip and a table fallback. */
export function ColumnChart({ rows, axisLabel, valueFmt = (v) => v.toFixed(2), xEvery = 1, tableHeaders, tableRows }: ColumnChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => {
      const w = Math.round(el.clientWidth);
      if (w > 0) setWidth(Math.max(260, w));
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const H = 200, m = { l: 36, r: 8, t: 10, b: 24 };
  const pw = width - m.l - m.r, ph = H - m.t - m.b;
  const max = niceMax(Math.max(...rows.map((r) => r.value), 0));
  const band = pw / rows.length;
  const bw = Math.min(24, band * 0.62);
  const ticks = 4;

  return (
    <div>
      <div ref={wrapRef} style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${width} ${H}`} role="img" aria-label={axisLabel} style={{ display: 'block', width: '100%', height: 'auto' }}>
          {Array.from({ length: ticks + 1 }, (_, i) => {
            const v = (max * i) / ticks;
            const y = m.t + ph - (v / max) * ph;
            return (
              <g key={i}>
                <line x1={m.l} x2={width - m.r} y1={y} y2={y} stroke="var(--color-grid)" strokeWidth={i === 0 ? 0 : 1} />
                {i === 0 && <line x1={m.l} x2={width - m.r} y1={y} y2={y} stroke="var(--color-axis)" />}
                <text x={m.l - 6} y={y + 3.5} textAnchor="end" fontSize={11} fill="var(--color-subtle)">{valueFmt(v)}</text>
              </g>
            );
          })}
          {rows.map((r, i) => {
            const x = m.l + i * band + (band - bw) / 2;
            const yTop = m.t + ph - (r.value / max) * ph;
            return (
              <g key={i}>
                <path d={colPath(x, yTop, bw, m.t + ph, 4)} fill={r.emphasis === false ? 'var(--color-axis)' : 'var(--color-insight)'} opacity={hover?.i === i ? 0.85 : 1} />
                {i % xEvery === 0 && <text x={x + bw / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--color-ink-muted)">{r.label}</text>}
                <rect
                  x={m.l + i * band} y={m.t} width={band} height={ph} fill="transparent" tabIndex={0}
                  aria-label={`${r.label}: ${valueFmt(r.value)}`}
                  onMouseMove={(e) => setHover({ i, x: e.clientX, y: e.clientY })}
                  onMouseLeave={() => setHover(null)}
                  onFocus={() => setHover({ i, x: 0, y: 0 })}
                  onBlur={() => setHover(null)}
                />
              </g>
            );
          })}
        </svg>
        {hover && (
          <div style={{
            position: 'fixed', left: hover.x + 14, top: hover.y + 14, zIndex: 100, pointerEvents: 'none',
            background: 'var(--color-ink)', color: 'var(--color-surface)', padding: '7px 10px',
            borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)', maxWidth: 240,
          }}>
            {rows[hover.i].tip ?? `${rows[hover.i].label}: ${valueFmt(rows[hover.i].value)}`}
          </div>
        )}
      </div>
      {tableHeaders && tableRows && (
        <details>
          <summary className="small secondary">View as table</summary>
          <div className="table-scroll">
            <table className="data">
              <thead><tr>{tableHeaders.map((h, i) => <th key={i} className={i ? 'n' : undefined}>{h}</th>)}</tr></thead>
              <tbody>{tableRows.map((row, i) => <tr key={i}>{row.map((c, j) => <td key={j} className={j ? 'n' : undefined}>{c}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
