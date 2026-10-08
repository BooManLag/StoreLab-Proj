import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../../api/client';
import type { Candidate, LabDone, ObjectiveOverrides, ObjectiveSpec } from '../../api/labTypes';
import type { JourneyTrack, Layout, StoreGeometry, TracksResponse } from '../../api/storeTypes';
import { CAT_LABEL, fmtSigned } from '../../lib/format';
import { costText, impact, plainReason, risk } from '../../lib/present';
import { changedRoutes } from '../../lib/changedRoutes';
import { StoreMap } from '../../components/StoreMap';

const PRINCIPLE = 'StoreLab predictions are hypotheses for real-world testing, not guaranteed outcomes.';

export function Results({
  done, store, selectedId, onSelect, onNewGoal, onRerun, onLaunchPilot,
}: {
  done: LabDone;
  store: StoreGeometry;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onNewGoal: () => void;
  onRerun: (text: string, overrides: ObjectiveOverrides) => void;
  onLaunchPilot: (id: string) => void;
}) {
  const o = done.objective;
  const tol = o.max_congestion_increase_pct;
  const recId = done.recommendation?.candidate_id ?? null;
  const byId = Object.fromEntries(done.candidates.map((c) => [c.id, c]));
  const selId = selectedId && byId[selectedId]?.simulation && byId[selectedId].status !== 'rejected' ? selectedId : recId;
  const tested = done.candidates.filter((c) => c.simulation).length;
  const rejected = done.candidates.filter((c) => c.status === 'rejected');
  const goodOnes = done.candidates.filter((c) => c.simulation && c.status !== 'rejected');

  return (
    <div>
      <GoalBar objective={o} onRerun={(overrides) => onRerun(o.raw_text, overrides)} onNewGoal={onNewGoal} />

      {!selId ? (
        <div className="card" style={{ padding: 'var(--space-8)' }}>
          <div className="eyebrow">I tested {tested} option{tested === 1 ? '' : 's'}</div>
          <h1 style={{ margin: '6px 0 10px' }}>None fits your limits</h1>
          <p className="secondary">Every idea either broke a limit or didn't help. Try a bigger budget or a looser checkout limit above.</p>
        </div>
      ) : (
        <Hero
          candidate={byId[selId]}
          isRec={selId === recId}
          done={done}
          store={store}
          tol={tol}
          hasAlts={goodOnes.length > 1}
          onSelect={onSelect}
          onBackToRec={() => recId && onSelect(recId)}
          onLaunchPilot={() => onLaunchPilot(selId)}
        />
      )}

      {goodOnes.length > 1 && (
        <>
          <div className="section-title"><h2>Other options that work</h2></div>
          <div className="alts" id="exp-alts">
            {goodOnes.filter((c) => c.id !== selId).map((c) => (
              <AltCard key={c.id} candidate={c} isRec={c.id === recId} done={done} tol={tol} onPick={() => onSelect(c.id)} />
            ))}
          </div>
        </>
      )}

      {rejected.length > 0 && (
        <details className="more">
          <summary>{rejected.length} idea{rejected.length > 1 ? 's' : ''} rejected</summary>
          <div className="body card">
            <ul className="rejected-list">
              {rejected.map((c) => (
                <li key={c.id}>
                  <span className="x" aria-hidden="true">✕</span>
                  <div><b>{c.name}</b><div className="secondary small">{plainReason(c)}</div></div>
                </li>
              ))}
            </ul>
          </div>
        </details>
      )}

      <p className="principle">{PRINCIPLE}</p>
    </div>
  );
}

function GoalBar({ objective: o, onRerun, onNewGoal }: { objective: ObjectiveSpec; onRerun: (overrides: ObjectiveOverrides) => void; onNewGoal: () => void }) {
  const [category, setCategory] = useState<ObjectiveOverrides['target_category'] | ''>(o.target_category as ObjectiveOverrides['target_category'] ?? '');
  const [uplift, setUplift] = useState(o.target_uplift_pct ?? '');
  const [budget, setBudget] = useState(Math.round(o.budget_php));
  const [congestion, setCongestion] = useState(o.max_congestion_increase_pct);
  const [dirty, setDirty] = useState(false);
  const cats = Object.keys(CAT_LABEL);

  return (
    <form
      className="goal-bar"
      onChange={() => setDirty(true)}
      onSubmit={(e) => {
        e.preventDefault();
        if (!(budget > 0)) return;
        const overrides: ObjectiveOverrides = {};
        if (budget !== Math.round(o.budget_php)) overrides.budget_php = budget;
        if (congestion !== o.max_congestion_increase_pct) overrides.max_congestion_increase_pct = congestion;
        const upliftNum = uplift === '' ? 0 : Number(uplift);
        if (upliftNum !== (o.target_uplift_pct ?? 0)) overrides.target_uplift_pct = upliftNum;
        if (category && category !== o.target_category) overrides.target_category = category;
        onRerun(overrides);
        setDirty(false);
      }}
    >
      <span className="goal-text">Goal</span>
      <label className="edit-chip">
        Grow
        <select value={category} onChange={(e) => setCategory(e.target.value as ObjectiveOverrides['target_category'])} aria-label="Category">
          {cats.map((c) => <option key={c} value={c}>{CAT_LABEL[c]}</option>)}
          {!o.target_category && <option value="">whole store</option>}
        </select>
      </label>
      <label className="edit-chip">
        by +<input type="number" min={0} max={500} step={1} value={uplift} placeholder="any" aria-label="Target increase percent" onChange={(e) => setUplift(e.target.value === '' ? '' : Number(e.target.value))} />%
      </label>
      <label className="edit-chip">
        Budget ₱<input type="number" min={1000} step={1000} value={budget} aria-label="Budget in pesos" onChange={(e) => setBudget(Number(e.target.value))} />
      </label>
      <label className="edit-chip">
        Checkout queue ≤ +<input type="number" min={0} max={100} step={1} value={congestion} aria-label="Checkout congestion limit percent" onChange={(e) => setCongestion(Number(e.target.value))} />%
      </label>
      <span className="edit-chip" style={{ paddingRight: 12 }}>
        Keep in place <b>{o.fixed_categories.length ? o.fixed_categories.map((c) => CAT_LABEL[c]).join(', ') : 'Coolers'}</b>
      </span>
      {dirty && <button type="submit" className="btn primary">Update results</button>}
      <span className="spacer" />
      <button type="button" className="btn ghost" onClick={onNewGoal}>New goal</button>
    </form>
  );
}

function RiskTag({ r }: { r: ReturnType<typeof risk> }) {
  return <span className={`tag ${r.cls}`}><span className="ico" aria-hidden="true">{r.icon}</span>{r.text}</span>;
}

interface TracksFor { layout: Layout; data: TracksResponse }

/** Fetches real simulated shopper tracks for the baseline and a candidate layout, cached per layout for the session. */
function useRouteTracks(store: StoreGeometry, layout: Layout | null) {
  const cache = useRef(new Map<string, Promise<TracksResponse>>());
  const [baselineFor, setBaselineFor] = useState<TracksFor | null>(null);
  const [candidateFor, setCandidateFor] = useState<TracksFor | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tracksFor = (l: Layout): Promise<TracksResponse> => {
      const key = JSON.stringify([l.category_slot, l.displays]);
      let p = cache.current.get(key);
      if (!p) {
        p = api.POST('/api/tracks', { body: { category_slot: l.category_slot, displays: l.displays } }).then((res) => {
          if (res.error) throw new Error('tracks request failed');
          return res.data as TracksResponse;
        });
        p.catch(() => cache.current.delete(key));
        cache.current.set(key, p);
      }
      return p;
    };

    tracksFor(store.baseline_layout).then((data) => { if (!cancelled) setBaselineFor({ layout: store.baseline_layout, data }); }).catch(() => {});
    if (layout) tracksFor(layout).then((data) => { if (!cancelled) setCandidateFor({ layout, data }); }).catch(() => {});
    return () => { cancelled = true; };
  }, [store, layout]);

  // Ignore a result left over from a layout we've since moved on from — the consumer sees "still loading", not stale data.
  const baseline = baselineFor?.layout === store.baseline_layout ? baselineFor.data : null;
  const candidate = layout && candidateFor?.layout === layout ? candidateFor.data : null;

  const changed = useMemo(
    () => (baseline && candidate ? changedRoutes(baseline.tracks, candidate.tracks) : new Set<JourneyTrack['id']>()),
    [baseline, candidate],
  );

  return { baseline, candidate, changed };
}

function Hero({
  candidate: c, isRec, done, store, tol, hasAlts, onBackToRec, onLaunchPilot,
}: {
  candidate: Candidate; isRec: boolean; done: LabDone; store: StoreGeometry; tol: number; hasAlts: boolean;
  onSelect: (id: string | null) => void; onBackToRec: () => void; onLaunchPilot: () => void;
}) {
  const x = isRec ? done.recommendation?.explanation : null;
  const title = isRec && x ? x.title : c.name;
  const why = isRec && x ? x.why : c.hypothesis;
  const im = impact(c);
  const rk = risk(c, tol);
  const cong = c.simulation!.deltas.congestion;
  const tested = done.candidates.filter((cand) => cand.simulation).length;
  const [showCandidate, setShowCandidate] = useState(false);
  const { baseline, candidate, changed } = useRouteTracks(store, c.layout ?? null);

  return (
    <>
      <div className="result-head">
        <div>
          <div className="eyebrow">I tested {tested} option{tested === 1 ? '' : 's'}{isRec ? ' · this is the best bet' : ''}</div>
          <h1 style={{ marginTop: 6 }}>{title}</h1>
        </div>
      </div>
      <article className={`hero${isRec ? '' : ' alt'}`}>
        <div className="hero-top">
          {isRec ? <span className="tag good"><span className="ico">★</span>Recommended</span> : <span className="tag neutral">Alternative you picked</span>}
          {!isRec && done.recommendation && <button type="button" className="link-btn" onClick={onBackToRec}>Back to the recommendation</button>}
          <span className="spacer" />
        </div>
        {c.layout && (
          <div className="hero-map">
            <div className="seg" role="group" aria-label="Map view">
              <button type="button" aria-pressed={!showCandidate} onClick={() => setShowCandidate(false)}>Your store today</button>
              <button type="button" aria-pressed={showCandidate} onClick={() => setShowCandidate(true)}>With this change</button>
            </div>
            <div className="hero-map-canvas">
              <StoreMap
                store={store}
                layout={showCandidate ? c.layout : null}
                tracks={(showCandidate ? candidate?.tracks : baseline?.tracks) ?? []}
                tracksWindowS={(showCandidate ? candidate?.window_s : baseline?.window_s) ?? 0}
                changed={showCandidate ? changed : undefined}
              />
            </div>
            <p className="small muted" style={{ marginTop: 'var(--space-2)' }}>
              {showCandidate
                ? (candidate ? <>{changed.size} of {candidate.tracks.length} shoppers re-routed — colored dots are the ones affected.</> : 'Loading the simulated shoppers…')
                : <>The store as it is today — toggle to see the change.</>}
            </p>
          </div>
        )}
        <div className="impact">
          <div>
            <div className="label">{im?.label}</div>
            <div className="value">{im ? fmtSigned(im.point) : '–'}</div>
            <div className="hint">likely {im?.range}{done.recommendation?.target_pct && isRec ? ` · goal +${done.recommendation.target_pct}%` : ''}</div>
          </div>
          <div>
            <div className="label">Checkout queue</div>
            <div className="value">{fmtSigned(cong.relative_pct)}</div>
            <div className="hint"><RiskTag r={rk} /> <span>limit +{tol}%</span></div>
          </div>
          <div>
            <div className="label">Cost</div>
            <div className="value">{costText(c)}</div>
            <div className="hint">one-time, per store</div>
          </div>
        </div>
        <div className="why">
          <div>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Why this works</div>
            <p>{why}</p>
            {rk.cls === 'risk' && <p className="small" style={{ marginTop: 6, color: 'var(--color-amber-text)' }}>{rk.detail}</p>}
          </div>
          <div className="actions">
            <button type="button" className="btn go big" onClick={onLaunchPilot}>Launch pilot →</button>
            {hasAlts && <a className="btn big" href="#exp-alts">Try another</a>}
          </div>
        </div>
        <p className="principle">{PRINCIPLE}</p>
      </article>
    </>
  );
}

function AltCard({ candidate: c, isRec, done, tol, onPick }: { candidate: Candidate; isRec: boolean; done: LabDone; tol: number; onPick: () => void }) {
  const im = impact(c);
  return (
    <article className="card alt">
      <div className="row">{isRec && <span className="tag good"><span className="ico">★</span>Recommended</span>}</div>
      <div className="alt-name">{isRec && done.recommendation ? done.recommendation.explanation.title : c.name}</div>
      <div className="stats">
        <span>Impact<b>{im?.range}</b></span>
        <span>Cost<b>{costText(c)}</b></span>
        <span>Risk<b><RiskTag r={risk(c, tol)} /></b></span>
      </div>
      <p className="secondary small">{c.hypothesis}</p>
      <div><button type="button" className="btn" onClick={onPick}>View this option</button></div>
    </article>
  );
}
