// Pilot — "Ready to test": the chosen change as a real-store A/B test, launched in one click.
import { postJSON } from '../api.js';
import { renderFloor } from '../floorplan.js';
import { pointText, rangeText } from '../present.js';
import { esc, fmtInt, fmtPeso, loadSession, saveSession } from '../util.js';

export function mountPilot(root, ctx) {
  const { state } = ctx;
  const plans = new Map();
  let token = 0;

  function selected() {
    const run = state.lastRun;
    if (!run) return null;
    const id = state.selectedId || run.recommendation?.candidate_id;
    const c = run.candidates.find((x) => x.id === id && x.simulation && x.status !== 'rejected');
    return c ? { run, c, isRec: id === run.recommendation?.candidate_id } : null;
  }

  async function planFor(sel) {
    const key = `${sel.run.run_id}:${sel.c.id}`;
    if (sel.isRec && sel.run.plan) return sel.run.plan;
    if (!plans.has(key)) {
      plans.set(key, postJSON('api/pilot/plan', { objective: sel.run.objective, candidate: sel.c })
        .catch((e) => { plans.delete(key); throw e; }));
    }
    return plans.get(key);
  }

  function empty() {
    root.innerHTML = `<div class="empty"><h1 id="pilot-title">Nothing to test yet</h1>
      <p>Find an experiment first. The one you pick becomes a real-store pilot here.</p>
      <p style="margin-top:18px"><a class="btn primary big" href="#experiments">Find experiments →</a></p></div>`;
  }

  async function render() {
    const sel = selected();
    if (!sel) { empty(); return; }
    const my = ++token;
    root.innerHTML = `<div class="empty"><span class="spinner"></span></div>`;
    let plan;
    try {
      plan = await planFor(sel);
    } catch (err) {
      root.innerHTML = `<div class="error-box">Could not build the pilot plan: ${esc(err.message)}</div>`;
      return;
    }
    if (my !== token) return;
    const { run, c, isRec } = sel;
    const o = run.objective;
    const title = isRec ? run.recommendation.explanation.title : c.name;
    const launchedKey = `storelab:pilot:${run.run_id}:${c.id}`;
    const launched = loadSession(launchedKey);
    const e = plan.expected;
    const cond = `${esc(plan.primary_kpi)}: up ${o.target_uplift_pct ? `at least <b>${o.target_uplift_pct}%</b>` : ''} versus the control stores,
      while the checkout queue stays within <b>+${o.max_congestion_increase_pct}%</b>.`;

    root.innerHTML = `
      <div class="pilot">
        <div class="pilot-head">
          <div class="eyebrow">${launched ? 'Pilot scheduled' : 'Ready to test'}</div>
          <h1 id="pilot-title">${esc(title)}</h1>
          <div class="what">${plan.changes.map(esc).join(' · ')}</div>
        </div>
        <div id="pilot-body"></div>
        <details class="more" id="pilot-method"><summary>Methodology & test details</summary><div class="body">
          <div class="grid cols-2">
            <div class="card">
              <h3 style="margin-bottom:10px">What the simulation expects</h3>
              <dl class="kv">
                <dt>${esc(plan.primary_kpi)}</dt><dd>${pointText(e.primary_pct)} <span class="muted">(likely ${rangeText(e.primary_ci_pct[0], e.primary_ci_pct[1])})</span></dd>
                <dt>Checkout queue</dt><dd>${pointText(e.congestion_pct)} <span class="muted">(likely ${rangeText(e.congestion_ci_pct[0], e.congestion_ci_pct[1])})</span></dd>
                <dt>Store revenue</dt><dd>${pointText(e.revenue_pct)}</dd>
                <dt>Install cost</dt><dd>${fmtPeso(plan.cost_per_store_php)} per store · ${fmtPeso(plan.total_install_cost_php)} total</dd>
              </dl>
              <div id="pilot-map" style="margin-top:12px"></div>
            </div>
            <div class="card">
              <h3 style="margin-bottom:10px">Test design</h3>
              <dl class="kv">
                <dt>Smallest effect it can detect</dt><dd>${plan.power.minimum_detectable_effect_pct.toFixed(1)}%</dd>
                <dt>Confidence</dt><dd>${Math.round(plan.power.power * 100)}% power, α ${plan.power.alpha}</dd>
                <dt>Baseline before the change</dt><dd>${plan.pre_period_days} days</dd>
              </dl>
              ${plan.power.underpowered ? `<p class="small" style="margin-top:8px;color:var(--warning-text)">▲ ${esc(plan.power.note || '')}</p>` : ''}
              <h3 style="margin:14px 0 8px">Test stores</h3><ul class="store-list">${plan.test_stores.map(storeRow).join('')}</ul>
              <h3 style="margin:12px 0 8px">Control stores</h3><ul class="store-list">${plan.control_stores.map(storeRow).join('')}</ul>
              <h3 style="margin:14px 0 8px">Guardrails</h3><ul class="plain small">${plan.guardrails.map((g) => `<li>${esc(g)}</li>`).join('')}</ul>
              ${isRec ? `<h3 style="margin:14px 0 8px">Risks</h3><ul class="plain small">${run.recommendation.explanation.risks.map((r) => `<li>${esc(r)}</li>`).join('')}</ul>` : ''}
            </div>
          </div>
        </div></details>
      </div>`;

    const body = root.querySelector('#pilot-body');
    function paintBody(rec) {
      if (rec) {
        body.innerHTML = `
          <div class="launched" role="status">
            <div class="check" aria-hidden="true">✓</div>
            <h2>Pilot ${esc(rec.pilot_id)} is scheduled</h2>
            <p class="secondary" style="margin-top:6px">${plan.test_stores.length} test stores · ${plan.control_stores.length} control stores · ${plan.duration_days} days</p>
            <ol>${plan.schedule.map((s) => `<li>${esc(s)}</li>`).join('')}</ol>
            <div class="row" style="justify-content:center;margin-top:18px">
              <button type="button" class="btn" id="export-plan">Export plan</button>
              <a class="btn primary" href="#store">Back to the store</a>
            </div>
          </div>`;
      } else {
        body.innerHTML = `
          <div class="pilot-facts">
            <div class="fact"><div class="big">${plan.test_stores.length}</div><div class="lbl">test stores</div>
              <div class="sub">${plan.test_stores.map((s) => esc(s.store_id)).join(' · ')}</div></div>
            <div class="fact"><div class="big">${plan.control_stores.length}</div><div class="lbl">control stores</div>
              <div class="sub">${plan.control_stores.map((s) => esc(s.store_id)).join(' · ')}</div></div>
            <div class="fact"><div class="big">${plan.duration_days}</div><div class="lbl">days</div>
              <div class="sub">after a ${plan.pre_period_days}-day baseline</div></div>
          </div>
          <div class="success-cond"><div class="eyebrow">It's a success if</div>${cond}</div>
          <div class="launch-row">
            <button type="button" class="btn go huge" id="launch">Launch pilot</button>
            <div class="row">
              <button type="button" class="btn ghost" id="show-method">View methodology</button>
              <button type="button" class="btn ghost" id="export-plan">Export plan</button>
              <span class="menu"><button type="button" class="btn ghost" id="more-btn" aria-haspopup="menu" aria-expanded="false">More ▾</button></span>
            </div>
            <span id="launch-error"></span>
          </div>`;
        body.querySelector('#launch').addEventListener('click', launch);
        body.querySelector('#show-method').addEventListener('click', () => {
          const d = root.querySelector('#pilot-method');
          d.open = true;
          d.scrollIntoView({ behavior: 'smooth' });
        });
        const moreBtn = body.querySelector('#more-btn');
        moreBtn.addEventListener('click', () => {
          const menu = moreBtn.parentElement;
          const open = menu.querySelector('.menu-list');
          if (open) { open.remove(); moreBtn.setAttribute('aria-expanded', 'false'); return; }
          moreBtn.setAttribute('aria-expanded', 'true');
          const list = document.createElement('div');
          list.className = 'menu-list';
          list.setAttribute('role', 'menu');
          list.innerHTML = '<button type="button" role="menuitem" id="dl-json">Download as JSON (for developers)</button>';
          menu.appendChild(list);
          list.querySelector('#dl-json').addEventListener('click', () => {
            download(`storelab-pilot-${run.run_id}-${c.id}.json`, JSON.stringify({ objective: o, experiment: c, plan }, null, 2), 'application/json');
            list.remove();
          });
        });
      }
      body.querySelector('#export-plan').addEventListener('click', () =>
        download(`storelab-pilot-${run.run_id}-${c.id}.md`, toMarkdown(run, c, plan, title, isRec), 'text/markdown'));
    }

    async function launch() {
      const btn = body.querySelector('#launch');
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Scheduling…';
      try {
        const rec = await postJSON('api/pilots', { plan, objective: o.raw_text });
        saveSession(launchedKey, rec);
        root.querySelector('.pilot-head .eyebrow').textContent = 'Pilot scheduled';
        paintBody(rec);
      } catch (err) {
        btn.disabled = false;
        btn.textContent = 'Launch pilot';
        body.querySelector('#launch-error').innerHTML = `<div class="error-box">${esc(err.message)}</div>`;
      }
    }

    paintBody(launched);
    if (c.layout) {
      renderFloor(root.querySelector('#pilot-map'), state.store, {
        mini: true, layout: c.layout, baseline: state.store.baseline_layout, target: o.target_category, title: 'Layout for the pilot',
      });
    }
  }

  render();
  return { refresh: render, onShow: render };
}

function storeRow(s) {
  return `<li><span>${esc(s.store_id)} · ${esc(s.name)}</span><span class="muted">${fmtInt(s.weekly_visitors)}/wk</span></li>`;
}

function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function toMarkdown(run, c, p, title, isRec) {
  const e = p.expected;
  const list = (xs) => xs.map((v) => `- ${v}`).join('\n');
  const stores = (xs) => xs.map((s) => `- ${s.store_id} · ${s.name} (${s.weekly_visitors.toLocaleString('en-US')} visitors/week)`).join('\n');
  const x = isRec ? run.recommendation.explanation : null;
  return `# Pilot: ${title}

Goal: ${run.objective.raw_text}

## The change
${list(p.changes)}

${x ? `## Why\n${x.why}\n\n` : ''}## Expected (simulated)
- ${p.primary_kpi}: ${pointText(e.primary_pct)} (likely ${rangeText(e.primary_ci_pct[0], e.primary_ci_pct[1])})
- Checkout queue: ${pointText(e.congestion_pct)} (likely ${rangeText(e.congestion_ci_pct[0], e.congestion_ci_pct[1])})
- Cost: ₱${p.cost_per_store_php.toLocaleString('en-US')} per store, ₱${p.total_install_cost_php.toLocaleString('en-US')} total

## Test
${p.test_stores.length} test stores, ${p.control_stores.length} control stores, ${p.duration_days} days after a ${p.pre_period_days}-day baseline.

Test stores:
${stores(p.test_stores)}

Control stores:
${stores(p.control_stores)}

Success: ${p.success_criterion}

Guardrails:
${list(p.guardrails)}

## Schedule
${list(p.schedule)}

---
StoreLab predictions are hypotheses for real-world testing, not guaranteed outcomes. Demo built on synthetic data.
`;
}
