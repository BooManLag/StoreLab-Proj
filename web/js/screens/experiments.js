// Experiments — goal in, best store change out. Recommendation first, evidence second, machinery last.
import { postJSON, streamLab } from '../api.js';
import { changedRoutes, renderFloor } from '../floorplan.js';
import { costText, impact, pointText, risk, tagHTML } from '../present.js';
import { CAT_LABEL, LANG_LABEL, esc, fmtInt, fmtPeso } from '../util.js';

const EXAMPLES = [
  { label: '日本語', text: 'スナックの売上を10%伸ばしたい。予算は3万ペソ。レジの混雑は増やさないこと。冷蔵庫は動かせない。' },
  { label: '한국어', text: '커피 동반 구매율을 높이고 싶어요. 예산 5만 페소, 계산대 혼잡은 늘리지 마세요.' },
  { label: 'Bahasa', text: 'Tingkatkan penjualan camilan 10% tanpa menambah antrean kasir. Anggaran ₱30.000.' },
  { label: 'Filipino', text: 'Dagdagan ang benta ng snacks ng 10%, budget P30,000, huwag dagdagan ang pila sa kahera.' },
];
const STEPS = [
  { key: 'understand', label: 'Understanding your goal', ids: ['interpret', 'sense'] },
  { key: 'design', label: 'Designing store changes', ids: ['diagnose', 'design'] },
  { key: 'test', label: 'Testing each change on simulated shoppers', ids: ['simulate', 'review_1', 'resim_1', 'review_2', 'resim_2', 'final_review'] },
  { key: 'choose', label: 'Choosing the best option', ids: ['rank', 'recommend'] },
];
const PRINCIPLE = 'StoreLab predictions are hypotheses for real-world testing, not guaranteed outcomes.';

export function mountExperiments(root, ctx) {
  const { state } = ctx;
  let goalText = '';
  let mode = 'fast';
  let controller = null;
  let live = null;            // collected events of the current run
  let particles = [];
  const trackCache = new Map();

  // ---------------------------------------------------------------- compose
  function renderCompose(error) {
    stopParticles();
    const briefGoals = state.analytics.summary.briefing.filter((b) => b.action.type === 'goal');
    root.innerHTML = `
      <div class="composer">
        <h1 id="exp-title">What do you want to improve?</h1>
        <p class="lede">Say it the way you would to a colleague — the goal, the budget, what must not change.
          StoreLab designs store changes and tests them on simulated shoppers before you touch the real floor.</p>
        ${error ? `<div class="error-box" style="margin-bottom:14px;text-align:left">${esc(error)}</div>` : ''}
        <form id="exp-form">
          <label for="exp-text" class="sr-only">Your goal</label>
          <textarea id="exp-text" maxlength="600" required>${esc(goalText || briefGoals[0]?.action.goal || '')}</textarea>
          <div class="suggest">
            ${briefGoals.map((b, i) => `<button type="button" class="chip" data-brief="${i}">${esc(b.action.label)}</button>`).join('')}
            ${EXAMPLES.map((e, i) => `<button type="button" class="chip" data-ex="${i}">${esc(e.label)}</button>`).join('')}
          </div>
          <div class="go-row">
            <div class="seg" role="group" aria-label="Search depth">
              <button type="button" data-mode="fast" aria-pressed="${mode === 'fast'}">Fast</button>
              <button type="button" data-mode="thorough" aria-pressed="${mode === 'thorough'}">Thorough</button>
            </div>
            <button type="submit" class="btn primary big">Find experiments →</button>
          </div>
        </form>
        ${state.lastRun ? `<p class="small" style="margin-top:22px"><button type="button" class="link-btn" id="exp-last">See your last results</button></p>` : ''}
      </div>`;
    const text = root.querySelector('#exp-text');
    root.querySelectorAll('[data-brief]').forEach((b) => b.addEventListener('click', () => { text.value = briefGoals[Number(b.dataset.brief)].action.goal; text.focus(); }));
    root.querySelectorAll('[data-ex]').forEach((b) => b.addEventListener('click', () => { text.value = EXAMPLES[Number(b.dataset.ex)].text; text.focus(); }));
    root.querySelectorAll('[data-mode]').forEach((b) => b.addEventListener('click', () => {
      mode = b.dataset.mode;
      root.querySelectorAll('[data-mode]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    }));
    root.querySelector('#exp-form').addEventListener('submit', (e) => {
      e.preventDefault();
      const v = text.value.trim();
      if (v.length < 3) { text.focus(); return; }
      start(v);
    });
    root.querySelector('#exp-last')?.addEventListener('click', () => renderResults(state.lastRun));
  }

  // ---------------------------------------------------------------- run
  async function start(text, overrides = null) {
    goalText = text;
    if (controller) controller.abort();
    controller = new AbortController();
    live = { steps: {}, designed: 0, simulated: 0, diagnosis: [], stepLog: [], overrides };
    renderProgress(text);
    try {
      await streamLab({ objective: text, mode, overrides }, onEvent, controller.signal);
      if (!live.done) throw new Error(live.error || 'The run ended before finishing. Please try again.');
    } catch (err) {
      if (err.name === 'AbortError') return;
      renderCompose(err.message);
    }
  }

  function renderProgress(text) {
    stopParticles();
    root.innerHTML = `
      <div class="progress" aria-live="polite">
        <h2 id="exp-title">Working on it…</h2>
        <p class="sub">“${esc(text)}”</p>
        <ol class="steps">${STEPS.map((s, i) => `<li data-step="${s.key}" class="${i === 0 ? 'active' : ''}">
          <span class="mark">${i === 0 ? '<span class="spinner"></span>' : ''}</span><span>${s.label}</span><span class="note"></span></li>`).join('')}</ol>
      </div>`;
  }

  function setProgress() {
    const doneSteps = new Set(Object.entries(live.steps).filter(([, v]) => v === 'done').map(([k]) => k));
    let activeFound = false;
    for (const s of STEPS) {
      const li = root.querySelector(`[data-step="${s.key}"]`);
      if (!li) continue;
      const started = s.ids.some((id) => id in live.steps);
      const allDone = started && s.ids.filter((id) => id in live.steps).every((id) => doneSteps.has(id));
      const later = STEPS.slice(STEPS.indexOf(s) + 1).some((x) => x.ids.some((id) => id in live.steps));
      const isDone = allDone && later;
      li.className = isDone ? 'done' : !activeFound && started ? 'active' : '';
      if (!isDone && started) activeFound = true;
      li.querySelector('.mark').innerHTML = isDone ? '✓' : li.className === 'active' ? '<span class="spinner"></span>' : '';
      if (s.key === 'design' && live.designed) li.querySelector('.note').textContent = `${live.designed} ideas`;
      if (s.key === 'test' && live.designed) li.querySelector('.note').textContent = `${live.simulated} of ${live.designed} tested`;
    }
  }

  function onEvent(ev) {
    switch (ev.type) {
      case 'step':
        live.steps[ev.id] = ev.status;
        if (ev.status === 'done') live.stepLog.push({ title: ev.title, source: ev.source, detail: ev.detail, fallback: ev.fallback_reason || null });
        setProgress();
        break;
      case 'candidate': live.designed += 1; setProgress(); break;
      case 'simulation': if (ev.status === 'done') { live.simulated += 1; setProgress(); } break;
      case 'diagnosis': live.diagnosis = ev.insights; break;
      case 'error': live.error = ev.message; break;
      case 'done': {
        const done = { ...ev, steps: live.stepLog, diagnosis: live.diagnosis, overrides: live.overrides || null };
        live.done = done;
        ctx.runFinished(done);
        renderResults(done);
        break;
      }
      default: break;
    }
  }

  // ---------------------------------------------------------------- results
  function stopParticles() {
    particles.forEach((p) => p.stop());
    particles = [];
  }

  function renderResults(done) {
    stopParticles();
    const o = done.objective;
    const tol = o.max_congestion_increase_pct;
    const recId = done.recommendation?.candidate_id || null;
    const byId = Object.fromEntries(done.candidates.map((c) => [c.id, c]));
    let selId = state.selectedId && byId[state.selectedId]?.simulation && byId[state.selectedId].status !== 'rejected' ? state.selectedId : recId;
    const tested = done.candidates.filter((c) => c.simulation).length;
    const rejected = done.candidates.filter((c) => c.status === 'rejected');
    const goodOnes = done.candidates.filter((c) => c.simulation && c.status !== 'rejected');

    root.innerHTML = `
      ${goalBar(o)}
      <div id="exp-main"></div>
      <div class="section-title" ${goodOnes.length > 1 ? '' : 'hidden'}><h2>Other options that work</h2></div>
      <div class="alts" id="exp-alts"></div>
      ${rejected.length ? `
      <details class="more"><summary>${rejected.length} idea${rejected.length > 1 ? 's' : ''} rejected</summary>
        <div class="body card"><ul class="rejected-list">${rejected.map((c) => `
          <li><span class="x" aria-hidden="true">✕</span><div><b>${esc(c.name)}</b><div class="secondary small">${esc(plainReason(c))}</div></div></li>`).join('')}
        </ul></div></details>` : ''}
      <details class="more" id="exp-decided"><summary>How StoreLab decided</summary><div class="body">${decided(done)}</div></details>`;
    wireGoalBar(o, done);

    function paint() {
      const main = root.querySelector('#exp-main');
      if (!selId) {
        main.innerHTML = `<div class="card" style="padding:28px"><div class="eyebrow">I tested ${tested} option${tested === 1 ? '' : 's'}</div>
          <h1 id="exp-title" style="margin:6px 0 10px">None fits your limits</h1>
          <p class="secondary">Every idea either broke a limit or didn't help. Try a bigger budget or a looser checkout limit above.</p></div>`;
        root.querySelector('#exp-alts').innerHTML = '';
        return;
      }
      const c = byId[selId];
      const isRec = selId === recId;
      const x = isRec ? done.recommendation.explanation : null;
      const title = isRec ? x.title : c.name;
      const why = isRec ? x.why : c.hypothesis;
      const im = impact(c);
      const rk = risk(c, tol);
      const cong = c.simulation.deltas.congestion;
      main.innerHTML = `
        <div class="result-head">
          <div><div class="eyebrow">I tested ${tested} option${tested === 1 ? '' : 's'}${isRec ? ' · this is the best bet' : ''}</div>
          <h1 id="exp-title" style="margin-top:6px">${esc(title)}</h1></div>
        </div>
        <article class="hero ${isRec ? '' : 'alt'}">
          <div class="hero-top">
            ${isRec ? '<span class="tag good"><span class="ico">★</span>Recommended</span>' : '<span class="tag neutral">Alternative you picked</span>'}
            ${!isRec && recId ? `<button type="button" class="link-btn" id="back-rec">Back to the recommendation</button>` : ''}
            <span class="spacer"></span>
            <button type="button" class="btn ghost" id="sim-play">Pause</button>
          </div>
          <div class="compare">
            <div><div class="eyebrow">Your store today</div><div id="map-base"></div></div>
            <div><div class="eyebrow">With this change <span class="tag neutral" id="changed-count" hidden></span></div><div id="map-cand"></div></div>
          </div>
          <div class="legend" style="padding:0 22px 6px">
            <span class="key"><span class="sw" style="background:var(--change)"></span>Shopper whose route changes</span>
            <span class="key"><span class="sw" style="background:var(--particle-buyer)"></span>Buys</span>
            <span class="key"><span class="sw" style="background:var(--particle-browser)"></span>Leaves without buying</span>
            <span class="key"><span class="sq" style="background:var(--change)"></span>What changes in the store</span>
          </div>
          <div class="impact">
            <div><div class="label">${esc(im.label)}</div><div class="value">${pointText(im.point)}</div>
              <div class="hint">likely ${im.range}${done.recommendation?.target_pct && isRec ? ` · goal +${done.recommendation.target_pct}%` : ''}</div></div>
            <div><div class="label">Checkout queue</div><div class="value">${pointText(cong.relative_pct)}</div>
              <div class="hint">${tagHTML(rk)} <span>limit +${tol}%</span></div></div>
            <div><div class="label">Cost</div><div class="value">${costText(c)}</div><div class="hint">one-time, per store</div></div>
          </div>
          <div class="why">
            <div><div class="eyebrow" style="margin-bottom:6px">Why this works</div><p>${esc(why)}</p>
              ${rk.cls === 'risk' ? `<p class="small" style="margin-top:6px;color:var(--warning-text)">${esc(rk.detail)}</p>` : ''}</div>
            <div class="actions">
              <button type="button" class="btn go big" id="to-pilot">Launch pilot →</button>
              ${goodOnes.length > 1 ? '<button type="button" class="btn big" id="try-another">Try another</button>' : ''}
            </div>
          </div>
          <p class="principle">${PRINCIPLE}</p>
        </article>`;
      root.querySelector('#to-pilot').addEventListener('click', () => { ctx.select(selId); ctx.navigate('pilot'); });
      root.querySelector('#try-another')?.addEventListener('click', () => root.querySelector('#exp-alts').scrollIntoView({ behavior: 'smooth' }));
      root.querySelector('#back-rec')?.addEventListener('click', () => choose(recId));
      showMaps(c);
      renderAlts();
    }

    function renderAlts() {
      const alts = goodOnes.filter((c) => c.id !== selId);
      root.querySelector('#exp-alts').innerHTML = alts.map((c) => {
        const im = impact(c);
        return `<article class="card alt">
          <div class="row">${c.id === recId ? '<span class="tag good"><span class="ico">★</span>Recommended</span>' : ''}</div>
          <div class="alt-name">${esc(c.id === recId ? done.recommendation.explanation.title : c.name)}</div>
          <div class="stats"><span>Impact<b>${im.range}</b></span><span>Cost<b>${costText(c)}</b></span><span>Risk<b>${tagHTML(risk(c, tol))}</b></span></div>
          <p class="secondary small">${esc(c.hypothesis)}</p>
          <div><button type="button" class="btn" data-pick="${c.id}">View this option</button></div>
        </article>`;
      }).join('');
      root.querySelectorAll('[data-pick]').forEach((b) => b.addEventListener('click', () => choose(b.dataset.pick)));
    }

    function choose(id) {
      selId = id;
      ctx.select(id);
      paint();
      root.querySelector('#exp-main').scrollIntoView({ behavior: 'smooth' });
    }

    async function showMaps(c) {
      stopParticles();
      const store = state.store;
      const a = renderFloor(root.querySelector('#map-base'), store, { mini: true, target: o.target_category, title: 'Current store' });
      const b = renderFloor(root.querySelector('#map-cand'), store, {
        mini: true, layout: c.layout, baseline: store.baseline_layout, target: o.target_category, title: 'Store with this change',
      });
      try {
        const [tb, tc] = await Promise.all([tracksFor(store.baseline_layout), tracksFor(c.layout)]);
        if (!root.querySelector('#map-base')?.contains(a.svg)) return; // re-rendered meanwhile
        const changed = changedRoutes(tb.tracks, tc.tracks);
        const badge = root.querySelector('#changed-count');
        badge.hidden = false;
        badge.textContent = `${changed.size} of ${tc.tracks.length} shoppers re-routed`;
        particles = [a.particles(tb.tracks, { speed: 30, window: tb.window_s }),
          b.particles(tc.tracks, { speed: 30, window: tc.window_s, changed })];
        if (root.classList.contains('active')) particles.forEach((p) => p.start());
        const btn = root.querySelector('#sim-play');
        btn.onclick = () => { btn.textContent = particles.map((p) => p.toggle())[0] ? 'Pause' : 'Play'; };
      } catch (err) {
        root.querySelector('#sim-play').hidden = true;
      }
    }

    paint();
  }

  async function tracksFor(layout) {
    const key = JSON.stringify([layout.category_slot, layout.displays]);
    if (!trackCache.has(key)) {
      trackCache.set(key, postJSON('api/tracks', { category_slot: layout.category_slot, displays: layout.displays })
        .catch((e) => { trackCache.delete(key); throw e; }));
    }
    return trackCache.get(key);
  }

  // ---------------------------------------------------------------- editable goal
  function goalBar(o) {
    const cats = Object.keys(CAT_LABEL);
    return `
      <form class="goal-bar" id="goal-form">
        <span class="goal-text">Goal</span>
        <label class="edit-chip">Grow
          <select name="target_category" aria-label="Category">
            ${cats.map((c) => `<option value="${c}" ${c === o.target_category ? 'selected' : ''}>${CAT_LABEL[c]}</option>`).join('')}
            ${o.target_category ? '' : '<option value="" selected>whole store</option>'}
          </select></label>
        <label class="edit-chip">by +<input type="number" name="target_uplift_pct" min="0" max="500" step="1" value="${o.target_uplift_pct ?? ''}" placeholder="any" aria-label="Target increase percent">%</label>
        <label class="edit-chip">Budget ₱<input type="number" name="budget_php" min="1000" step="1000" value="${Math.round(o.budget_php)}" aria-label="Budget in pesos"></label>
        <label class="edit-chip">Checkout queue ≤ +<input type="number" name="max_congestion_increase_pct" min="0" max="100" step="1" value="${o.max_congestion_increase_pct}" aria-label="Checkout congestion limit percent">%</label>
        <span class="edit-chip" style="padding-right:12px">Keep in place <b>${o.fixed_categories.length ? o.fixed_categories.map((c) => esc(CAT_LABEL[c])).join(', ') : 'Coolers'}</b></span>
        <button type="submit" class="btn primary" id="goal-update" hidden>Update results</button>
        <span class="spacer"></span>
        <button type="button" class="btn ghost" id="goal-new">New goal</button>
      </form>`;
  }

  function wireGoalBar(o, done) {
    const form = root.querySelector('#goal-form');
    const upd = root.querySelector('#goal-update');
    form.addEventListener('input', () => { upd.hidden = false; });
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const f = new FormData(form);
      const num = (k) => (f.get(k) === '' ? null : Number(f.get(k)));
      const budget = num('budget_php');
      if (!(budget > 0)) { form.querySelector('[name=budget_php]').focus(); return; }
      // Send only what the manager actually changed, on top of any earlier edits.
      const overrides = { ...(done.overrides || {}) };
      if (budget !== Math.round(o.budget_php)) overrides.budget_php = budget;
      const cong = num('max_congestion_increase_pct');
      if (cong !== null && cong !== o.max_congestion_increase_pct) overrides.max_congestion_increase_pct = cong;
      const target = num('target_uplift_pct') ?? 0;
      if (target !== (o.target_uplift_pct ?? 0)) overrides.target_uplift_pct = target;
      const cat = f.get('target_category') || null;
      if (cat && cat !== o.target_category) overrides.target_category = cat;
      start(done.objective.raw_text, overrides);
    });
    root.querySelector('#goal-new').addEventListener('click', () => { goalText = ''; renderCompose(); });
  }

  // ---------------------------------------------------------------- explain mode
  function decided(done) {
    const o = done.objective;
    const gem = done.agent.mode !== 'offline';
    const rows = done.candidates.map((c) => {
      const d = c.simulation?.deltas;
      return `<tr><td><b>${esc(c.id)}</b></td><td>${esc(c.name)}<div class="small muted">round ${c.round} · designed by ${esc(c.source === 'gemini' ? 'Gemini' : 'offline planner')}</div></td>
        <td class="n">${d ? `${pointText(d.primary.relative_pct)}<div class="small muted">${pointText(d.primary.ci_low_pct)} to ${pointText(d.primary.ci_high_pct)}</div>` : '–'}</td>
        <td class="n">${d ? `${pointText(d.congestion.relative_pct)}<div class="small muted">${pointText(d.congestion.ci_low_pct)} to ${pointText(d.congestion.ci_high_pct)}</div>` : '–'}</td>
        <td class="n">${fmtPeso(c.cost)}</td>
        <td>${c.status === 'recommended' ? '<span class="tag good">★ chosen</span>' : c.verdict === 'keep' ? '<span class="tag neutral">kept</span>' : '<span class="tag bad">✕ rejected</span>'}
          <div class="small muted">${esc(c.verdict_source || '')}${c.verdict_reason ? ': ' + esc(c.verdict_reason) : ''}</div></td></tr>`;
    }).join('');
    return `<div class="decided card">
      <div><h3>Agent</h3><p class="secondary">${gem ? `Gemini (${esc(done.agent.model)})` : 'Offline heuristic planner (no Gemini credentials)'} ·
        ${done.gemini_calls} Gemini calls · ${done.tool_calls.length} tool calls · ${done.seconds} s${done.fallbacks.length ? ` · ${done.fallbacks.length} steps fell back to the offline planner` : ''}</p></div>
      <div><h3>How the goal was read</h3><p class="secondary">${esc(o.normalized_objective)} <span class="muted">(${esc(LANG_LABEL[o.language] || o.language)})</span></p>
        ${o.notes.length ? `<ul class="plain small">${o.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : ''}</div>
      ${done.diagnosis?.length ? `<div><h3>Hypotheses</h3><ul class="plain">${done.diagnosis.map((i) => `<li><b>${esc(i.observation)}</b> ${esc(i.hypothesis)}</li>`).join('')}</ul></div>` : ''}
      <div><h3>Every option tested</h3>
        <p class="small muted" style="margin-bottom:6px">Each option ran on ${fmtInt(state.config.simulator.journeys_per_run)} simulated shopper journeys —
          the same shoppers for every option. Ranges are 95% intervals across ${state.config.simulator.days_per_run} simulated days. Hard limits are checked by code and override the AI.</p>
        <div class="table-scroll"><table class="data"><thead><tr><th></th><th>Option</th><th class="n">${esc(done.candidates.find((c) => c.simulation)?.simulation.deltas.primary.label || 'Goal')}</th>
          <th class="n">Checkout queue</th><th class="n">Cost</th><th>Verdict</th></tr></thead><tbody>${rows}</tbody></table></div></div>
      ${done.steps?.length ? `<div><h3>Steps</h3><ol class="timeline">${done.steps.map((s) => `<li>${esc(s.title)} <span class="src ${esc(s.source)}">${esc(s.source)}</span>
        <span class="muted">${esc(s.detail || '')}</span>${s.fallback ? `<div class="small muted">Fell back: ${esc(s.fallback)}</div>` : ''}</li>`).join('')}</ol></div>` : ''}
      <div><h3>Tool calls</h3>${done.tool_calls.map((t) => `<div class="tool-call"><span class="fn">${esc(t.name)}</span>(${esc(t.args)}) → ${esc(t.summary)}</div>`).join('')}</div>
    </div>`;
  }

  function plainReason(c) {
    if (!c.valid) return 'Not allowed in this store: ' + (c.errors[0] || '');
    const d = c.simulation?.deltas;
    if (c.gate && !c.gate.passed && d && /congestion/i.test(c.gate.reason)) {
      return `Would make the checkout queue ${pointText(d.congestion.relative_pct)} busier (your limit is +${c.gate.reason.match(/\+([\d.]+)% allowed/)?.[1] ?? ''}%), even though it lifts ${d.primary.label.toLowerCase()} ${pointText(d.primary.relative_pct)}.`;
    }
    if (d && d.primary.relative_pct <= 0) return `Didn't improve ${d.primary.label.toLowerCase()} (${pointText(d.primary.relative_pct)}).`;
    return c.verdict_reason || 'Rejected.';
  }

  if (state.lastRun) renderResults(state.lastRun);
  else renderCompose();

  return {
    start,
    prefill(goal) {
      if (controller && live && !live.done) return; // a run is in progress
      goalText = goal;
      renderCompose();
    },
    onShow() { particles.forEach((p) => p.start()); },
    onHide() { particles.forEach((p) => p.stop()); },
  };
}
