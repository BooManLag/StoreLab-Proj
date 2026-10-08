import { forwardRef, useImperativeHandle, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { CAT_LABEL, fmtInt, fmtPct, fmtPeso, fmtSigned } from '../lib/format';
import { CvDemo } from '../components/CvDemo';
import './About.css';

export interface AboutHandle {
  open: () => void;
}

function fmtCalValue(metric: string, v: number): string {
  if (metric.includes('conversion')) return fmtPct(v);
  if (metric.includes('congestion')) return v.toFixed(2);
  if (metric.includes('₱')) return fmtPeso(v);
  return fmtInt(v);
}

export const About = forwardRef<AboutHandle>(function About(_props, ref) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const { data } = useApp();
  const { config, store, analytics } = data;
  const gemini = config.agent.mode !== 'offline';
  const m = analytics.model;
  const t = m.transition_model;
  const ck = m.checkout_model;

  useImperativeHandle(ref, () => ({
    open: () => dialogRef.current?.showModal(),
  }));

  return (
    <dialog ref={dialogRef} className="drawer" aria-labelledby="about-title">
      <div className="drawer-head">
        <h2 id="about-title">About the data &amp; how StoreLab works</h2>
        <span className="spacer" />
        <button type="button" className="btn ghost" aria-label="Close" onClick={() => dialogRef.current?.close()}>✕</button>
      </div>

      <section>
        <h3>Demo mode</h3>
        <p className="secondary">
          {store.name} is fictional. Its {fmtInt(config.history.journeys)} shopper journeys,{' '}
          {fmtInt(config.history.transactions)} POS baskets ({config.history.period}) and camera footage are synthetic.
        </p>
        <p className="secondary" style={{ marginTop: 8 }}>
          AI agent: {gemini
            ? <><b>Gemini</b> ({config.agent.model}) via {config.agent.mode === 'vertex-ai' ? 'Vertex AI' : 'the Gemini API'}.</>
            : <><b>offline planner</b> — {config.agent.reason}.</>}
        </p>
      </section>

      <section>
        <h3>How it works</h3>
        <ul className="plain">
          <li><b>Sense</b> — store cameras become anonymous paths (no faces, random IDs); POS baskets are linked by checkout time.</li>
          <li><b>Twin</b> — a behaviour model is fitted to those paths and baskets: where shoppers walk, stop and buy.</li>
          <li><b>Design</b> — the AI agent turns your goal into concrete store changes (structured, never free-form).</li>
          <li><b>Check</b> — every change is validated against budget, refrigeration, walkway width and the emergency exit.</li>
          <li><b>Simulate</b> — each option runs on {fmtInt(config.simulator.journeys_per_run)} simulated shopper journeys; the same shoppers see every option.</li>
          <li><b>Pilot</b> — the best option becomes a real-store test against control stores. Results feed back into the twin.</li>
        </ul>
      </section>

      <CvDemo store={store} />

      <section>
        <h3>How well the twin matches the store</h3>
        <div className="table-scroll">
          <table className="data">
            <thead><tr><th>Per week</th><th className="n">Observed</th><th className="n">Twin</th><th className="n">Gap</th></tr></thead>
            <tbody>
              {analytics.calibration.rows.map((r) => (
                <tr key={r.metric}>
                  <td>{r.metric}</td>
                  <td className="n">{fmtCalValue(r.metric, r.observed)}</td>
                  <td className="n">{fmtCalValue(r.metric, r.simulated)}</td>
                  <td className="n">{fmtSigned(r.error_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small secondary" style={{ marginTop: 8 }}>
          Walking cost {t.beta_dist_per_m.toFixed(3)}/m · categories bought together:{' '}
          {m.complements.map((pair) => pair.map((x) => CAT_LABEL[x] ?? x).join(' & ')).join(', ')} · checkout {ck.base_s.toFixed(0)} s + {ck.per_item_s.toFixed(1)} s per item.
          The extra counter time for a checkout-queue display ({ck.rack_dwell_s} s) is an assumption: the store has no such display to learn from.
        </p>
      </section>

      <section>
        <h3>Data</h3>
        <div className="row">
          {['journey_events', 'transactions', 'products', 'zones', 'stores'].map((x) => (
            <a key={x} className="chip" href={`/api/data/${x}.csv`} download>{x}.csv</a>
          ))}
        </div>
        <p className="small muted" style={{ marginTop: 8 }}>
          {fmtInt(analytics.summary.pos_join.matched)} of {fmtInt(analytics.summary.pos_join.transactions)} baskets linked to
          an anonymous journey by matching payment time to checkout exit. API docs: <a href="/docs" target="_blank" rel="noopener">/docs</a>.
        </p>
      </section>
    </dialog>
  );
});
