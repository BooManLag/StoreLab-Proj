import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import type { Candidate, LabDone, PilotPlan, PilotRecord } from '../api/labTypes';
import { useApp } from '../context/AppContext';
import { loadSession, saveSession } from '../lib/storage';
import { download } from '../lib/download';
import { pilotToMarkdown } from '../lib/pilotExport';
import { PilotMethodology } from './PilotMethodology';
import './Pilot.css';

interface Selection {
  run: LabDone;
  c: Candidate;
  isRec: boolean;
}

export function Pilot() {
  const { data, lastRun, selectedId } = useApp();

  const sel = useMemo<Selection | null>(() => {
    if (!lastRun) return null;
    const id = selectedId || lastRun.recommendation?.candidate_id;
    const c = lastRun.candidates.find((x) => x.id === id && x.simulation && x.status !== 'rejected');
    return c ? { run: lastRun, c, isRec: id === lastRun.recommendation?.candidate_id } : null;
  }, [lastRun, selectedId]);

  if (!sel) {
    return (
      <div className="empty">
        <h1>Nothing to test yet</h1>
        <p>Find an experiment first. The one you pick becomes a real-store pilot here.</p>
        <p style={{ marginTop: 18 }}><a className="btn primary big" href="#experiments">Find experiments →</a></p>
      </div>
    );
  }
  return <PilotLoaded key={`${sel.run.run_id}:${sel.c.id}`} sel={sel} storeName={data.store.name} />;
}

function PilotLoaded({ sel, storeName }: { sel: Selection; storeName: string }) {
  const { run, c, isRec } = sel;
  const o = run.objective;
  const title = isRec && run.recommendation ? run.recommendation.explanation.title : c.name;
  const launchedKey = `storelab:pilot:${run.run_id}:${c.id}`;

  const [plan, setPlan] = useState<PilotPlan | null>(isRec ? (run.plan as PilotPlan | null) : null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [launched, setLaunched] = useState<PilotRecord | null>(() => loadSession(launchedKey));
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (plan) return;
    let cancelled = false;
    (async () => {
      // candidate is a bare `dict` server-side (storelab/main.py PilotPlanRequest) — no real schema to match.
      const res = await api.POST('/api/pilot/plan', { body: { objective: o, candidate: c as unknown as Record<string, unknown> } });
      if (cancelled) return;
      if (res.error) setPlanError('Could not build the pilot plan.');
      else setPlan(res.data as PilotPlan);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (planError) return <div className="error-box">{planError}</div>;
  if (!plan) return <div className="empty"><span className="spinner" /></div>;

  const cond = (
    <>
      {plan.primary_kpi}: up {o.target_uplift_pct ? <>at least <b>{o.target_uplift_pct}%</b> </> : ''}
      versus the control stores, while the checkout queue stays within <b>+{o.max_congestion_increase_pct}%</b>.
    </>
  );

  const doExportMd = () => download(`storelab-pilot-${run.run_id}-${c.id}.md`, pilotToMarkdown(run, plan, title, isRec), 'text/markdown');
  const doExportJson = () => {
    download(`storelab-pilot-${run.run_id}-${c.id}.json`, JSON.stringify({ objective: o, experiment: c, plan }, null, 2), 'application/json');
    setMenuOpen(false);
  };

  const launch = async () => {
    setLaunching(true);
    setLaunchError(null);
    // plan is a bare `dict` server-side (storelab/main.py PilotRequest) — no real schema to match.
    const res = await api.POST('/api/pilots', { body: { plan: plan as unknown as Record<string, unknown>, objective: o.raw_text } });
    if (res.error) {
      setLaunching(false);
      setLaunchError('Could not schedule the pilot. Please try again.');
      return;
    }
    const rec = res.data as PilotRecord;
    saveSession(launchedKey, rec);
    setLaunched(rec);
  };

  return (
    <div className="pilot">
      <div className="pilot-head">
        <div className="eyebrow">{launched ? 'Pilot scheduled' : 'Ready to test'}</div>
        <h1>{title}</h1>
        <div className="what">{plan.changes.join(' · ')}</div>
      </div>

      {launched ? (
        <div className="launched" role="status">
          <div className="check" aria-hidden="true">✓</div>
          <h2>Pilot {launched.pilot_id} is scheduled</h2>
          <p className="secondary" style={{ marginTop: 6 }}>
            {plan.test_stores.length} test stores · {plan.control_stores.length} control stores · {plan.duration_days} days
          </p>
          <ol>{plan.schedule.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <div className="row" style={{ justifyContent: 'center', marginTop: 18 }}>
            <button type="button" className="btn" onClick={doExportMd}>Export plan</button>
            <a className="btn primary" href="#store">Back to {storeName.replace(/\s*\(.*\)\s*/, '')}</a>
          </div>
        </div>
      ) : (
        <>
          <div className="pilot-facts">
            <div className="fact">
              <div className="big">{plan.test_stores.length}</div><div className="lbl">test stores</div>
              <div className="sub">{plan.test_stores.map((s) => s.store_id).join(' · ')}</div>
            </div>
            <div className="fact">
              <div className="big">{plan.control_stores.length}</div><div className="lbl">control stores</div>
              <div className="sub">{plan.control_stores.map((s) => s.store_id).join(' · ')}</div>
            </div>
            <div className="fact">
              <div className="big">{plan.duration_days}</div><div className="lbl">days</div>
              <div className="sub">after a {plan.pre_period_days}-day baseline</div>
            </div>
          </div>
          <div className="success-cond"><div className="eyebrow">It's a success if</div>{cond}</div>
          <div className="launch-row">
            <button type="button" className="btn go huge" onClick={launch} disabled={launching}>
              {launching ? <><span className="spinner" /> Scheduling…</> : 'Launch pilot'}
            </button>
            <div className="row">
              <button
                type="button" className="btn ghost"
                onClick={() => { const d = document.getElementById('pilot-method') as HTMLDetailsElement | null; if (d) { d.open = true; d.scrollIntoView({ behavior: 'smooth' }); } }}
              >
                View methodology
              </button>
              <button type="button" className="btn ghost" onClick={doExportMd}>Export plan</button>
              <span className="menu">
                <button type="button" className="btn ghost" aria-haspopup="menu" aria-expanded={menuOpen} onClick={() => setMenuOpen((v) => !v)}>More ▾</button>
                {menuOpen && (
                  <div className="menu-list" role="menu">
                    <button type="button" role="menuitem" onClick={doExportJson}>Download as JSON (for developers)</button>
                  </div>
                )}
              </span>
            </div>
            {launchError && <div className="error-box">{launchError}</div>}
          </div>
        </>
      )}

      <PilotMethodology plan={plan} risks={isRec && run.recommendation ? run.recommendation.explanation.risks : null} />
    </div>
  );
}
