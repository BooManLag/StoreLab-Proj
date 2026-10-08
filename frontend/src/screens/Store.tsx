import { useMemo, useRef, useState } from 'react';
import type { BriefingItem } from '../api/storeTypes';
import type { HighlightKind, PinSpec } from '../three/StoreScene';
import { StoreMap, type StoreMapHandle } from '../components/StoreMap';
import { StoreAnalytics } from './StoreAnalytics';
import { useApp } from '../context/AppContext';
import { fmtInt, fmtPct, clock as clockText } from '../lib/format';
import './Store.css';

const KIND_LABEL: Record<BriefingItem['kind'], string> = { opportunity: 'Opportunity', friction: 'Friction', pattern: 'Pattern' };
const DEFAULT_GOAL = "Increase snack sales by 10%. Budget ₱30k. Don't worsen checkout congestion.";

type Layer = 'highlights' | 'traffic' | 'heat';

export function Store() {
  const { data, requestExperiment } = useApp();
  const { store, analytics, sample } = data;
  const k = analytics.summary.kpis;
  const briefing = analytics.summary.briefing;

  const [layer, setLayer] = useState<Layer>('highlights');
  const [active, setActive] = useState(0);
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [playing, setPlaying] = useState(() => !window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [hotIndex, setHotIndex] = useState<number | null>(null);
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  const mapRef = useRef<StoreMapHandle>(null);
  const clockRef = useRef<HTMLSpanElement>(null);
  const onTick = (t: number) => { if (clockRef.current) clockRef.current.textContent = clockText(sample.start + t); };

  const activeIdx = hotIndex ?? active;

  const highlight = useMemo<{ ids: string[]; kind: HighlightKind }>(() => {
    if (layer !== 'highlights' || !briefing[activeIdx]) return { ids: [], kind: '' };
    return { ids: briefing[activeIdx].zones, kind: briefing[activeIdx].kind };
  }, [layer, activeIdx, briefing]);

  const pins = useMemo<PinSpec[]>(() => {
    if (layer !== 'highlights') return [];
    return briefing.map((b, i) => ({
      id: String(i),
      n: i + 1,
      kind: b.kind,
      label: b.title,
      zone: b.zones[b.zones.length - 1] === 'checkout' ? 'checkout' : b.zones[0],
      onClick: () => setActive(i),
      onHover: (hovering) => setHotIndex(hovering ? i : null),
    }));
  }, [layer, briefing]);

  const heatGrid = layer === 'heat' ? analytics.heatmap : null;

  const zone = selectedCat ? analytics.summary.zones[selectedCat] : null;
  const zoneTags = useMemo(() => {
    if (!zone || !selectedCat) return null;
    const zones = Object.values(analytics.summary.zones);
    const rank = [...zones].sort((a, b) => b.visitors - a.visitors).findIndex((x) => x.category === selectedCat);
    const convs = zones.map((x) => x.zone_conversion).sort((a, b) => a - b);
    const median = convs[Math.floor(convs.length / 2)];
    const link = analytics.summary.sequence_effects.find((e) => e.to === selectedCat && e.ratio >= 1.5);
    return { rank, median, link };
  }, [zone, selectedCat, analytics.summary]);

  const findExperiments = () => {
    const opp = briefing.find((b) => b.kind === 'opportunity');
    requestExperiment(opp ? opp.action.goal ?? DEFAULT_GOAL : DEFAULT_GOAL);
  };

  const runAction = (action: BriefingItem['action']) => {
    if (action.type === 'goal' && action.goal) { requestExperiment(action.goal); return; }
    const details = document.getElementById('store-analytics') as HTMLDetailsElement | null;
    if (!details) return;
    details.open = true;
    (action.target === 'hourly' ? document.getElementById('store-hourly-card') : details)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div>
      <div className="store-head">
        <div>
          <div className="eyebrow">Last {k.days} days · {fmtInt(k.visitors)} shoppers · {fmtInt(k.transactions)} purchases</div>
          <h1>{store.name.replace(/\s*\(.*\)\s*/, '')}</h1>
        </div>
        <span className="spacer" />
        <button type="button" className="btn primary" onClick={findExperiments}>Find experiments →</button>
      </div>

      <div className="store-grid">
        <div className="card map-card">
          <div className="map-toolbar">
            <div className="seg" role="group" aria-label="Map view">
              {(['highlights', 'traffic', 'heat'] as Layer[]).map((l) => (
                <button key={l} type="button" aria-pressed={layer === l} onClick={() => setLayer(l)}>
                  {l === 'highlights' ? 'Highlights' : l === 'traffic' ? 'Traffic' : 'Heatmap'}
                </button>
              ))}
            </div>
            <span className="spacer" />
            {layer === 'traffic' && (
              <button type="button" className="btn ghost" onClick={() => setPlaying(mapRef.current?.toggleParticles() ?? false)}>
                {playing ? 'Pause' : 'Play'}
              </button>
            )}
            {layer === 'traffic' && <span className="clock" ref={clockRef}>17:00</span>}
          </div>

          <div className="map-canvas">
            <StoreMap
              ref={mapRef}
              store={store}
              selectedCat={selectedCat}
              onZoneClick={setSelectedCat}
              heatGrid={heatGrid}
              onCellHover={(info) => setTooltip(info ? { text: `${fmtInt(info.value)} ${analytics.heatmap_units}`, x: info.clientX, y: info.clientY } : null)}
              highlight={highlight}
              pins={pins}
              tracks={sample.tracks}
              tracksWindowS={sample.window_s}
              onTick={onTick}
            />
          </div>

          <div className="map-foot legend">
            {layer === 'heat' ? (
              <>
                <span className="heat-scale">Less <span className="bar">{[0, 1, 2, 3, 4, 5, 6].map((i) => <span key={i} style={{ background: `var(--color-heat-${i})` }} />)}</span> More</span>
                <span className="muted">time shoppers spend in each spot</span>
              </>
            ) : layer === 'traffic' ? (
              <>
                <span className="key"><span className="sw" style={{ background: 'var(--color-particle-buyer)' }} />Buys something</span>
                <span className="key"><span className="sw" style={{ background: 'var(--color-particle-browser)' }} />Leaves without buying</span>
                <span className="muted">Replay of real (anonymous) evening traffic, 30× speed</span>
              </>
            ) : (
              <span className="muted">Drag to orbit, scroll to zoom. Click an aisle for details.</span>
            )}
          </div>
        </div>

        <div className="stack" aria-label="What StoreLab sees">
          <div className="eyebrow">What StoreLab sees</div>
          {briefing.map((b, i) => (
            <article
              key={i}
              className={`callout ${b.kind}${i === activeIdx && layer === 'highlights' ? ' hot' : ''}`}
              tabIndex={0}
              onMouseEnter={() => layer === 'highlights' && setActive(i)}
              onFocus={() => layer === 'highlights' && setActive(i)}
            >
              <span className="num-badge" aria-hidden="true">{i + 1}</span>
              <div>
                <div className="kind">{KIND_LABEL[b.kind]}</div>
                <div className="title">{b.title}</div>
                <div className="detail">{b.detail}</div>
                <button type="button" className={`btn ${b.action.type === 'goal' ? 'primary' : ''}`} onClick={(e) => { e.stopPropagation(); runAction(b.action); }}>
                  {b.action.label} →
                </button>
              </div>
            </article>
          ))}

          {zone && selectedCat && zoneTags && (
            <div className="card zone-panel">
              <div className="row">
                <h3>{zone.label}</h3>
                <span className="spacer" />
                <button type="button" className="btn ghost" aria-label="Close aisle details" onClick={() => setSelectedCat(null)}>✕</button>
              </div>
              <div className="tags">
                <span className={`tag ${zoneTags.rank < 2 ? 'info' : 'neutral'}`}>{zoneTags.rank < 2 ? 'High traffic' : 'Quieter aisle'}</span>
                <span className={`tag ${zone.zone_conversion <= zoneTags.median ? 'info' : 'neutral'}`}>{zone.zone_conversion <= zoneTags.median ? 'Low conversion' : 'Converts well'}</span>
                {zoneTags.link && <span className="tag info">Strong affinity</span>}
              </div>
              <p className="secondary">
                {fmtPct(zone.traffic_share, 0)} of shoppers visit · {fmtPct(zone.zone_conversion, 0)} of them buy ·
                {' '}average {zone.avg_dwell_s.toFixed(0)}s in the aisle
              </p>
              <button
                type="button" className="btn primary" style={{ marginTop: 'var(--space-3)' }}
                onClick={() => requestExperiment(`Increase ${zone.category} sales by 10%. Budget ₱30,000. Don't worsen checkout congestion.`)}
              >
                Improve {zone.label} →
              </button>
            </div>
          )}
        </div>
      </div>

      <StoreAnalytics store={store} summary={analytics.summary} />

      {tooltip && (
        <div style={{
          position: 'fixed', left: tooltip.x + 14, top: tooltip.y + 14, zIndex: 100, pointerEvents: 'none',
          background: 'var(--color-ink)', color: 'var(--color-surface)', padding: '7px 10px',
          borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)',
        }}>
          {tooltip.text}
        </div>
      )}
    </div>
  );
}
