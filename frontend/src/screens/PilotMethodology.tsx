import type { PilotPlan, PilotStoreRow } from '../api/labTypes';
import { fmtPeso, fmtSigned } from '../lib/format';
import { rangeText } from '../lib/present';

function StoreRow({ s }: { s: PilotStoreRow }) {
  return <li><span>{s.store_id} · {s.name}</span><span className="muted">{s.weekly_visitors.toLocaleString('en-US')}/wk</span></li>;
}

export function PilotMethodology({ plan, risks }: { plan: PilotPlan; risks: string[] | null }) {
  const e = plan.expected;
  return (
    <details className="more" id="pilot-method">
      <summary>Methodology &amp; test details</summary>
      <div className="body">
        <div className="grid cols-2">
          <div className="card">
            <h3 style={{ marginBottom: 10 }}>What the simulation expects</h3>
            <dl className="kv">
              <dt>{plan.primary_kpi}</dt>
              <dd>{fmtSigned(e.primary_pct)} <span className="muted">(likely {rangeText(e.primary_ci_pct[0], e.primary_ci_pct[1])})</span></dd>
              <dt>Checkout queue</dt>
              <dd>{fmtSigned(e.congestion_pct)} <span className="muted">(likely {rangeText(e.congestion_ci_pct[0], e.congestion_ci_pct[1])})</span></dd>
              <dt>Store revenue</dt>
              <dd>{fmtSigned(e.revenue_pct)}</dd>
              <dt>Install cost</dt>
              <dd>{fmtPeso(plan.cost_per_store_php)} per store · {fmtPeso(plan.total_install_cost_php)} total</dd>
            </dl>
          </div>
          <div className="card">
            <h3 style={{ marginBottom: 10 }}>Test design</h3>
            <dl className="kv">
              <dt>Smallest effect it can detect</dt><dd>{plan.power.minimum_detectable_effect_pct.toFixed(1)}%</dd>
              <dt>Confidence</dt><dd>{Math.round(plan.power.power * 100)}% power, α {plan.power.alpha}</dd>
              <dt>Baseline before the change</dt><dd>{plan.pre_period_days} days</dd>
            </dl>
            {plan.power.underpowered && (
              <p className="small" style={{ marginTop: 8, color: 'var(--color-amber-text)' }}>▲ {plan.power.note ?? ''}</p>
            )}
            <h3 style={{ margin: '14px 0 8px' }}>Test stores</h3>
            <ul className="store-list">{plan.test_stores.map((s) => <StoreRow key={s.store_id} s={s} />)}</ul>
            <h3 style={{ margin: '12px 0 8px' }}>Control stores</h3>
            <ul className="store-list">{plan.control_stores.map((s) => <StoreRow key={s.store_id} s={s} />)}</ul>
            <h3 style={{ margin: '14px 0 8px' }}>Guardrails</h3>
            <ul className="plain small">{plan.guardrails.map((g, i) => <li key={i}>{g}</li>)}</ul>
            {risks && (
              <>
                <h3 style={{ margin: '14px 0 8px' }}>Risks</h3>
                <ul className="plain small">{risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
              </>
            )}
          </div>
        </div>
      </div>
    </details>
  );
}
