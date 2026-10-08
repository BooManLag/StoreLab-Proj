import { ColumnChart } from '../components/ColumnChart';
import { fmtInt, fmtPct, fmtPeso, pad2 } from '../lib/format';
import type { AnalyticsSummary, StoreGeometry } from '../api/storeTypes';

export function StoreAnalytics({ store, summary }: { store: StoreGeometry; summary: AnalyticsSummary }) {
  const k = summary.kpis;
  const [p0, p1] = store.constraints.peak_window;

  return (
    <details className="more" id="store-analytics">
      <summary>View analytics</summary>
      <div className="body">
        <div className="tiles">
          <Tile label="Shoppers" value={fmtInt(k.visitors)} hint={`${k.days} days`} />
          <Tile label="Purchases" value={fmtInt(k.transactions)} hint="POS baskets" />
          <Tile label="Bought something" value={fmtPct(k.conversion_rate)} hint="of shoppers" />
          <Tile label="Average basket" value={fmtPeso(k.avg_basket)} hint={`${k.items_per_basket.toFixed(1)} items`} />
          <Tile label="Checkout at peak" value={k.peak_checkout_occupancy.toFixed(2)} hint={`shoppers in line, ${k.peak_window}`} />
        </div>

        <div className="grid cols-2">
          <div className="card" id="store-hourly-card">
            <div className="card-head"><h3>Checkout crowding by hour</h3><span className="sub">average shoppers at checkout</span></div>
            <ColumnChart
              axisLabel="Average shoppers at checkout by hour"
              xEvery={2}
              valueFmt={(v) => v.toFixed(2)}
              rows={summary.hourly.map((r) => ({
                label: String(r.hour),
                value: r.checkout_occupancy,
                emphasis: r.hour >= p0 && r.hour < p1,
                tip: `${pad2(r.hour)}:00–${pad2(r.hour + 1)}:00 — ${r.checkout_occupancy.toFixed(2)} shoppers at checkout, ${r.transactions_per_day.toFixed(0)} purchases/hour`,
              }))}
              tableHeaders={['Hour', 'Shoppers at checkout', 'Purchases / hour']}
              tableRows={summary.hourly.map((r) => [`${pad2(r.hour)}:00`, r.checkout_occupancy.toFixed(2), r.transactions_per_day.toFixed(1)])}
            />
          </div>

          <div className="card">
            <div className="card-head"><h3>Aisle funnels</h3><span className="sub">visited → stopped 20s+ → bought</span></div>
            <div className="table-scroll">
              <table className="data">
                <thead><tr><th>Aisle</th><th className="n">Visited</th><th className="n">Stopped</th><th className="n">Bought</th><th className="n">Conversion</th></tr></thead>
                <tbody>
                  {Object.values(summary.zones).map((z) => (
                    <tr key={z.label}>
                      <td>{z.label}</td>
                      <td className="n">{fmtInt(z.visitors)}</td>
                      <td className="n">{fmtInt(z.engaged)}</td>
                      <td className="n">{fmtInt(z.purchases)}</td>
                      <td className="n">{fmtPct(z.zone_conversion)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h3>Shopper types</h3><span className="sub">grouped by the paths they take</span></div>
            <div className="table-scroll">
              <table className="data">
                <thead><tr><th>Type</th><th className="n">Share</th><th className="n">Buy</th><th>Typical path</th></tr></thead>
                <tbody>
                  {summary.clusters.map((c) => (
                    <tr key={c.name}>
                      <td>{c.name}</td>
                      <td className="n">{fmtPct(c.share, 0)}</td>
                      <td className="n">{fmtPct(c.conversion, 0)}</td>
                      <td className="small secondary">{c.top_paths[0]?.path ?? ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h3>Where shoppers go next</h3></div>
            <div className="table-scroll">
              <table className="data">
                <thead>
                  <tr><th>From \ To</th>{summary.transitions.labels.map((l) => <th key={l} className="n">{l}</th>)}</tr>
                </thead>
                <tbody>
                  {summary.transitions.labels.slice(0, 5).map((l, r) => (
                    <tr key={l}>
                      <th>{l}</th>
                      {summary.transitions.probabilities[r].map((p, c) => (
                        <td key={c} className="n">{p > 0 ? (p >= 0.3 ? <b>{fmtPct(p, 0)}</b> : fmtPct(p, 0)) : '·'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h3>Everything StoreLab noticed</h3></div>
          <ul className="insights">
            {summary.insights.map((i, idx) => (
              <li key={idx}>
                <div className="title">{i.title}</div>
                <div className="detail">{i.detail}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}

function Tile({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      <div className="hint">{hint}</div>
    </div>
  );
}
