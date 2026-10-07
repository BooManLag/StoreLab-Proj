// "About the data & how StoreLab works": demo mode, data sources, camera pipeline, twin calibration.
import { postJSON } from './api.js';
import { CAT_LABEL, esc, fmtInt, fmtPct, fmtPeso, fmtSigned } from './util.js';

export function mountAbout(root, { state }) {
  let cvTimer = null;
  let lastFocus = null;

  function close() {
    if (cvTimer) clearInterval(cvTimer);
    root.innerHTML = '';
    document.removeEventListener('keydown', onKey);
    lastFocus?.focus?.();
  }
  function onKey(e) { if (e.key === 'Escape') close(); }

  function open(section) {
    lastFocus = document.activeElement;
    const { config, store, analytics } = state;
    const gemini = config.agent.mode !== 'offline';
    const m = analytics.model;
    const t = m.transition_model;
    const ck = m.checkout_model;
    root.innerHTML = `
      <div class="drawer-backdrop" data-close></div>
      <aside class="drawer" role="dialog" aria-modal="true" aria-labelledby="about-title">
        <div class="drawer-head"><h2 id="about-title">About the data & how StoreLab works</h2><span class="spacer"></span>
          <button type="button" class="btn ghost" data-close aria-label="Close">✕</button></div>

        <section id="about-demo">
          <h3>Demo mode</h3>
          <p class="secondary">${esc(store.name)} is fictional. Its ${fmtInt(config.history.journeys)} shopper journeys,
            ${fmtInt(config.history.transactions)} POS baskets (${esc(config.history.period)}) and camera footage are synthetic.</p>
          <p class="secondary" style="margin-top:8px">AI agent: ${gemini
            ? `<b>Gemini</b> (${esc(config.agent.model)}) via ${config.agent.mode === 'vertex-ai' ? 'Vertex AI' : 'the Gemini API'}.`
            : `<b>offline planner</b> — ${esc(config.agent.reason)}.`}</p>
        </section>

        <section>
          <h3>How it works</h3>
          <ul class="plain">
            <li><b>Sense</b> — store cameras become anonymous paths (no faces, random IDs); POS baskets are linked by checkout time.</li>
            <li><b>Twin</b> — a behaviour model is fitted to those paths and baskets: where shoppers walk, stop and buy.</li>
            <li><b>Design</b> — the AI agent turns your goal into concrete store changes (structured, never free-form).</li>
            <li><b>Check</b> — every change is validated against budget, refrigeration, walkway width and the emergency exit.</li>
            <li><b>Simulate</b> — each option runs on ${fmtInt(config.simulator.journeys_per_run)} simulated shopper journeys; the same shoppers see every option.</li>
            <li><b>Pilot</b> — the best option becomes a real-store test against control stores. Results feed back into the twin.</li>
          </ul>
        </section>

        <section id="about-camera">
          <h3>Camera pipeline</h3>
          <p class="secondary small">Person detection → tracking → camera-to-floor mapping → zone events. Frames are discarded after processing.</p>
          <div class="row" style="margin-top:10px">
            <button type="button" class="btn" id="cv-run">Run on the demo camera clip</button>
            <label class="btn ghost" for="cv-file">Process your own clip…</label>
            <input type="file" id="cv-file" accept="video/*" class="sr-only">
            <span class="small muted" id="cv-status"></span>
          </div>
          <div id="cv-out" style="margin-top:12px"></div>
        </section>

        <section id="about-model">
          <h3>How well the twin matches the store</h3>
          <div class="table-scroll"><table class="data"><thead><tr><th>Per week</th><th class="n">Observed</th><th class="n">Twin</th><th class="n">Gap</th></tr></thead><tbody>
          ${analytics.calibration.rows.map((r) => `<tr><td>${esc(r.metric)}</td><td class="n">${fmtCal(r, r.observed)}</td>
            <td class="n">${fmtCal(r, r.simulated)}</td><td class="n">${fmtSigned(r.error_pct)}</td></tr>`).join('')}</tbody></table></div>
          <p class="small secondary" style="margin-top:8px">Walking cost ${t.beta_dist_per_m.toFixed(3)}/m · categories bought together:
            ${m.complements.map((p) => p.map((x) => CAT_LABEL[x]).join(' & ')).join(', ')} · checkout ${ck.base_s.toFixed(0)} s + ${ck.per_item_s.toFixed(1)} s per item.
            The extra counter time for a checkout-queue display (${ck.rack_dwell_s} s) is an assumption: the store has no such display to learn from.</p>
        </section>

        <section>
          <h3>Data</h3>
          <div class="row">${['journey_events', 'transactions', 'products', 'zones', 'stores'].map((x) =>
            `<a class="chip" href="api/data/${x}.csv" download>${x}.csv</a>`).join('')}</div>
          <p class="small muted" style="margin-top:8px">${fmtInt(analytics.summary.pos_join.matched)} of ${fmtInt(analytics.summary.pos_join.transactions)}
            baskets linked to an anonymous journey by matching payment time to checkout exit. API docs: <a href="docs" target="_blank" rel="noopener">/docs</a>.</p>
        </section>
      </aside>`;
    root.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', close));
    document.addEventListener('keydown', onKey);
    wireCV();
    const target = section ? root.querySelector('#about-' + section) : null;
    (target || root.querySelector('.drawer')).scrollIntoView?.({ block: 'start' });
    root.querySelector('.drawer [data-close]').focus();
  }

  function fmtCal(r, v) {
    if (r.metric.includes('conversion')) return fmtPct(v);
    if (r.metric.includes('congestion')) return v.toFixed(2);
    if (r.metric.includes('₱')) return fmtPeso(v);
    return fmtInt(v);
  }

  function wireCV() {
    const out = root.querySelector('#cv-out');
    const status = root.querySelector('#cv-status');
    const buttons = () => root.querySelectorAll('#about-camera button');
    async function run(promise, label) {
      status.innerHTML = `<span class="spinner"></span> ${esc(label)}`;
      buttons().forEach((b) => (b.disabled = true));
      try {
        render(await promise);
        status.textContent = '';
      } catch (err) {
        status.textContent = '';
        out.innerHTML = `<div class="error-box">${esc(err.message)}</div>`;
      } finally {
        buttons().forEach((b) => (b.disabled = false));
      }
    }
    root.querySelector('#cv-run').addEventListener('click', () => run(postJSON('api/cv/demo'), 'Processing the 45-second clip…'));
    root.querySelector('#cv-file').addEventListener('change', (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append('file', f);
      const p = fetch('api/cv/upload', { method: 'POST', body: fd }).then(async (r) => {
        const j = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : `Upload failed (${r.status})`);
        return j;
      });
      e.target.value = '';
      run(p, `Processing ${f.name}…`);
    });

    function render(r) {
      if (cvTimer) clearInterval(cvTimer);
      const ev = r.evaluation;
      const journeys = r.tracks.filter((t) => t.journey.length).slice(0, 10);
      out.innerHTML = `
        <div class="cv-player"><img id="cv-img" alt="Camera frame with anonymous shopper boxes"></div>
        <dl class="kv" style="margin-top:10px">
          <dt>Anonymous tracks</dt><dd>${fmtInt(r.tracks.length)}</dd>
          ${ev ? `<dt>Shoppers found</dt><dd>${ev.people_tracked} of ${ev.people_in_clip}</dd>
          <dt>Position accuracy</dt><dd>${ev.mean_position_error_m != null ? '±' + (ev.mean_position_error_m * 100).toFixed(0) + ' cm' : '–'}</dd>
          <dt>Shoppers split into 2 tracks</dt><dd>${ev.fragmented_people}</dd>` : ''}
        </dl>
        <ul class="journey-list" style="margin-top:10px">${journeys.map((t) => `<li><code>${esc(t.anonymous_track_id)}</code><span>${t.journey.map((z) => esc(zoneName(z))).join(' → ')}</span></li>`).join('')}</ul>`;
      const frames = r.previews.filter((p) => p.jpeg_base64);
      const img = out.querySelector('#cv-img');
      let f = 0;
      const paint = () => { if (frames.length) img.src = 'data:image/jpeg;base64,' + frames[f++ % frames.length].jpeg_base64; };
      paint();
      cvTimer = setInterval(() => { if (!img.isConnected) { clearInterval(cvTimer); return; } paint(); }, 600);
    }
  }

  function zoneName(z) {
    const cat = Object.entries(state.store.baseline_layout.category_slot).find(([, sl]) => sl === z)?.[0];
    return cat ? CAT_LABEL[cat] : z.charAt(0).toUpperCase() + z.slice(1);
  }

  return { open, close };
}
