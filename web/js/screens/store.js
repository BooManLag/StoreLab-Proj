// Store — the map is the hero; StoreLab points at one opportunity, one friction and one pattern.
import { renderFloor, heatThresholds } from '../floorplan.js';
import { barList, columnChart } from '../charts.js';
import { CAT_LABEL, CAT_SINGULAR, clock, esc, fmtInt, fmtPct, fmtPeso, pad2 } from '../util.js';

const KIND_LABEL = { opportunity: 'Opportunity', friction: 'Friction', pattern: 'Pattern' };
const DEFAULT_GOAL = "Increase snack sales by 10%. Budget ₱30k. Don't worsen checkout congestion.";

export function mountStore(root, ctx) {
  const { store, analytics, sample } = ctx.state;
  const s = analytics.summary;
  const k = s.kpis;
  const briefing = s.briefing;
  let layer = 'highlights';
  let active = 0;
  let selectedCat = null;

  root.innerHTML = `
    <div class="store-head">
      <div>
        <div class="eyebrow">Last 7 days · ${fmtInt(k.visitors)} shoppers · ${fmtInt(k.transactions)} purchases</div>
        <h1 id="store-title">${esc(store.name.replace(/\s*\(.*\)\s*/, ''))}</h1>
      </div>
      <span class="spacer"></span>
      <button type="button" class="btn primary big" id="store-find">Find experiments →</button>
    </div>
    <div class="store-grid">
      <div class="card map-card">
        <div class="map-toolbar">
          <div class="seg" role="group" aria-label="Map view">
            <button type="button" data-layer="highlights" aria-pressed="true">Highlights</button>
            <button type="button" data-layer="traffic" aria-pressed="false">Traffic</button>
            <button type="button" data-layer="heat" aria-pressed="false">Heatmap</button>
          </div>
          <span class="spacer"></span>
          <button type="button" class="btn ghost" id="store-play">Pause</button>
          <span class="clock" id="store-clock">17:00</span>
        </div>
        <div id="store-floor"></div>
        <div class="map-foot legend" id="store-legend"></div>
      </div>
      <div class="stack" aria-label="What StoreLab sees">
        <div class="eyebrow">What StoreLab sees</div>
        ${briefing.map((b, i) => `
          <article class="callout ${b.kind}" data-i="${i}" tabindex="0">
            <span class="num-badge" aria-hidden="true">${i + 1}</span>
            <div>
              <div class="kind">${KIND_LABEL[b.kind]}</div>
              <div class="t">${esc(b.title)}</div>
              <div class="d">${esc(b.detail)}</div>
              <button type="button" class="btn ${b.action.type === 'goal' ? 'primary' : ''}" data-act="${i}">${esc(b.action.label)} →</button>
            </div>
          </article>`).join('')}
        <div class="card zone-panel" id="zone-panel" hidden></div>
      </div>
    </div>

    <details class="more" id="store-analytics">
      <summary>View analytics</summary>
      <div class="body stack">
        <div class="tiles">
          ${tile('Shoppers', fmtInt(k.visitors), `${k.days} days`)}
          ${tile('Purchases', fmtInt(k.transactions), 'POS baskets')}
          ${tile('Bought something', fmtPct(k.conversion_rate), 'of shoppers')}
          ${tile('Average basket', fmtPeso(k.avg_basket), `${k.items_per_basket.toFixed(1)} items`)}
          ${tile('Checkout at peak', k.peak_checkout_occupancy.toFixed(2), `shoppers in line, ${esc(k.peak_window)}`)}
        </div>
        <div class="grid cols-2">
          <div class="card" id="store-hourly-card">
            <div class="card-head"><h3>Checkout crowding by hour</h3><span class="sub">average shoppers at checkout</span></div>
            <div id="store-hourly"></div>
          </div>
          <div class="card">
            <div class="card-head"><h3>Aisle funnels</h3><span class="sub">visited → stopped 20 s+ → bought</span></div>
            <div class="table-scroll">${funnelTable(s.zones)}</div>
          </div>
          <div class="card">
            <div class="card-head"><h3>Shopper types</h3><span class="sub">grouped by the paths they take</span></div>
            <div class="table-scroll">${clustersTable(s.clusters)}</div>
          </div>
          <div class="card">
            <div class="card-head"><h3>Where shoppers go next</h3></div>
            <div class="table-scroll">${transitionsTable(s.transitions)}</div>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><h3>Everything StoreLab noticed</h3></div>
          <ul class="insights">${s.insights.map((i) => `<li><div class="t">${esc(i.title)}</div><div class="d">${esc(i.detail)}</div></li>`).join('')}</ul>
        </div>
      </div>
    </details>`;

  const $ = (q) => root.querySelector(q);
  const floor = renderFloor($('#store-floor'), store, { onZoneClick: selectZone, title: 'Store map' });
  const thresholds = heatThresholds(analytics.heatmap);
  const clockEl = $('#store-clock');
  const particles = floor.particles(sample.tracks, {
    speed: 30, window: sample.window_s, onTick: (t) => { clockEl.textContent = clock(sample.start + t); },
  });
  const callouts = [...root.querySelectorAll('.callout')];

  function applyLayer() {
    root.querySelectorAll('[data-layer]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.layer === layer)));
    floor.setHeat(layer === 'heat' ? analytics.heatmap : null, thresholds);
    if (layer === 'highlights') {
      floor.pins(briefing.map((b, i) => ({
        n: i + 1, zone: b.zones[b.zones.length - 1] === 'checkout' ? 'checkout' : b.zones[0], kind: b.kind, label: b.title,
        onClick: () => activate(i, true), onHover: (on) => callouts[i].classList.toggle('hot', on),
      })));
      activate(active, false);
    } else {
      floor.pins([]);
      floor.highlight([], '');
      callouts.forEach((c) => c.classList.remove('hot'));
    }
    $('#store-legend').innerHTML = layer === 'heat'
      ? `<span class="heat-scale">Less <span class="bar">${[0, 1, 2, 3, 4, 5, 6].map((i) => `<span style="background:var(--heat-${i})"></span>`).join('')}</span> More</span>
         <span class="muted">time shoppers spend in each spot</span>`
      : `<span class="key"><span class="sw" style="background:var(--particle-buyer)"></span>Buys something</span>
         <span class="key"><span class="sw" style="background:var(--particle-browser)"></span>Leaves without buying</span>
         <span class="muted">Replay of real (anonymous) evening traffic, 30× speed</span>`;
  }

  function activate(i, scroll) {
    active = i;
    const b = briefing[i];
    callouts.forEach((c, j) => c.classList.toggle('hot', j === i));
    floor.highlight(b.zones, b.kind);
    if (scroll) callouts[i].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  callouts.forEach((c, i) => {
    c.addEventListener('mouseenter', () => { if (layer === 'highlights') activate(i, false); });
    c.addEventListener('focus', () => { if (layer === 'highlights') activate(i, false); });
  });
  root.querySelectorAll('[data-act]').forEach((b) => b.addEventListener('click', (e) => {
    e.stopPropagation();
    const act = briefing[Number(b.dataset.act)].action;
    if (act.type === 'goal') ctx.prefillGoal(act.goal);
    else openAnalytics(act.target);
  }));
  root.querySelectorAll('[data-layer]').forEach((b) => b.addEventListener('click', () => {
    layer = b.dataset.layer;
    applyLayer();
  }));
  const playBtn = $('#store-play');
  playBtn.addEventListener('click', () => { playBtn.textContent = particles.toggle() ? 'Pause' : 'Play'; });
  $('#store-find').addEventListener('click', () => {
    const opp = briefing.find((b) => b.kind === 'opportunity');
    ctx.prefillGoal(opp ? opp.action.goal : DEFAULT_GOAL);
  });

  function openAnalytics(target) {
    const d = $('#store-analytics');
    d.open = true;
    (target === 'hourly' ? $('#store-hourly-card') : d).scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ---------------------------------------------------------------- aisle panel
  function selectZone(cat) {
    selectedCat = cat;
    floor.setSelected(cat);
    const z = s.zones[cat];
    const zones = Object.values(s.zones);
    const rank = [...zones].sort((a, b) => b.visitors - a.visitors).findIndex((x) => x.category === cat);
    const convs = zones.map((x) => x.zone_conversion).sort((a, b) => a - b);
    const median = convs[Math.floor(convs.length / 2)];
    const tags = [];
    tags.push(rank < 2 ? '<span class="tag info">High traffic</span>' : '<span class="tag neutral">Quieter aisle</span>');
    tags.push(z.zone_conversion <= median ? '<span class="tag info">Low conversion</span>' : '<span class="tag neutral">Converts well</span>');
    const link = s.sequence_effects.find((e) => e.to === cat && e.ratio >= 1.5);
    if (link) tags.push(`<span class="tag info">Strong ${esc(CAT_LABEL[link.from])} affinity</span>`);
    const panel = $('#zone-panel');
    panel.hidden = false;
    panel.innerHTML = `
      <div class="row"><h3 style="font-size:19px">${esc(z.label)}</h3><span class="spacer"></span>
        <button type="button" class="btn ghost" id="zone-close" aria-label="Close aisle details">✕</button></div>
      <div class="tags">${tags.join('')}</div>
      <p class="secondary">${fmtPct(z.traffic_share, 0)} of shoppers visit · ${fmtPct(z.zone_conversion, 0)} of them buy ·
        ${link ? `${fmtPct(link.conversion_after_from, 0)} buy when they come from ${esc(CAT_LABEL[link.from])}` : `${fmtPeso(z.revenue)} in 7 days`}</p>
      <details class="inline" style="margin-top:10px"><summary>See evidence</summary>
        <div id="zone-funnel"></div>
        <dl class="kv" style="margin-top:8px">
          <dt>Average time in aisle</dt><dd>${z.avg_dwell_s.toFixed(0)} s</dd>
          <dt>In ${fmtPct(z.attachment_rate, 0)} of all baskets</dt><dd>${fmtInt(z.category_buyers)} baskets</dd>
          <dt>Revenue (7 days)</dt><dd>${fmtPeso(z.revenue)}</dd>
        </dl>
      </details>
      <button type="button" class="btn primary" id="zone-improve" style="margin-top:12px">Improve ${esc(z.label)} →</button>`;
    barList(panel.querySelector('#zone-funnel'), [
      { label: 'Visited', value: z.visitors, display: fmtInt(z.visitors) },
      { label: 'Stopped 20 s+', value: z.engaged, display: fmtInt(z.engaged) },
      { label: 'Bought', value: z.purchases, display: fmtInt(z.purchases) },
    ]);
    panel.querySelector('#zone-close').addEventListener('click', () => { panel.hidden = true; floor.setSelected(null); selectedCat = null; });
    panel.querySelector('#zone-improve').addEventListener('click', () =>
      ctx.prefillGoal(`Increase ${CAT_SINGULAR[cat]} sales by 10%. Budget ₱30k. Don't worsen checkout congestion.`));
    panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  const [p0, p1] = store.constraints.peak_window;
  columnChart($('#store-hourly'), s.hourly.map((r) => ({
    label: String(r.hour), value: r.checkout_occupancy, emphasis: r.hour >= p0 && r.hour < p1,
    tip: `<b>${pad2(r.hour)}:00–${pad2(r.hour + 1)}:00</b><br>${r.checkout_occupancy.toFixed(2)} shoppers at checkout<br>${r.transactions_per_day.toFixed(0)} purchases/hour`,
  })), {
    valueFmt: (v) => v.toFixed(2), axisLabel: 'Average shoppers at checkout by hour', xEvery: 2,
    table: { headers: ['Hour', 'Shoppers at checkout', 'Purchases / hour'],
      rows: s.hourly.map((r) => [`${pad2(r.hour)}:00`, r.checkout_occupancy.toFixed(2), r.transactions_per_day.toFixed(1)]) },
  });

  applyLayer();
  return {
    onShow() { particles.start(); playBtn.textContent = 'Pause'; },
    onHide() { particles.stop(); },
    selectedCat: () => selectedCat,
  };
}

function tile(label, value, hint) {
  return `<div class="tile"><div class="label">${esc(label)}</div><div class="value">${value}</div><div class="hint">${hint}</div></div>`;
}

function funnelTable(zones) {
  return `<table class="data"><thead><tr><th>Aisle</th><th class="n">Visited</th><th class="n">Stopped</th><th class="n">Bought</th><th class="n">Conversion</th></tr></thead><tbody>
    ${Object.values(zones).map((z) => `<tr><td>${esc(z.label)}</td><td class="n">${fmtInt(z.visitors)}</td><td class="n">${fmtInt(z.engaged)}</td>
      <td class="n">${fmtInt(z.purchases)}</td><td class="n">${fmtPct(z.zone_conversion)}</td></tr>`).join('')}</tbody></table>`;
}

function clustersTable(clusters) {
  return `<table class="data"><thead><tr><th>Type</th><th class="n">Share</th><th class="n">Buy</th><th>Typical path</th></tr></thead><tbody>
    ${clusters.map((c) => `<tr><td>${esc(c.name)}</td><td class="n">${fmtPct(c.share, 0)}</td><td class="n">${fmtPct(c.conversion, 0)}</td>
      <td class="small secondary">${esc(c.top_paths[0]?.path || '')}</td></tr>`).join('')}</tbody></table>`;
}

function transitionsTable(T) {
  const head = T.labels.map((l) => `<th class="n">${esc(l)}</th>`).join('');
  const rows = T.labels.slice(0, 5).map((l, r) => `<tr><th>${esc(l)}</th>${T.probabilities[r].map((p) =>
    `<td class="n">${p > 0 ? (p >= 0.3 ? `<b>${fmtPct(p, 0)}</b>` : fmtPct(p, 0)) : '·'}</td>`).join('')}</tr>`).join('');
  return `<table class="data"><thead><tr><th>From \\ To</th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
}
