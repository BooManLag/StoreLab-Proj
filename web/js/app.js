// StoreLab web app: Store → Experiments → Pilot.
import { getJSON } from './api.js';
import { esc, loadSession, saveSession } from './util.js';
import { mountStore } from './screens/store.js';
import { mountExperiments } from './screens/experiments.js';
import { mountPilot } from './screens/pilot.js';
import { mountAbout } from './about.js';

const state = {
  config: null,
  store: null,
  analytics: null,
  sample: null,
  lastRun: loadSession('storelab:lastRun'),
  selectedId: loadSession('storelab:selected'),
};

const SCREENS = ['store', 'experiments', 'pilot'];
const ALIASES = { live: 'store', ask: 'experiments', lab: 'experiments', plan: 'pilot' };
const views = {};

function show(name) {
  name = ALIASES[name] || name;
  if (!SCREENS.includes(name)) name = 'store';
  for (const s of SCREENS) {
    document.getElementById('screen-' + s).classList.toggle('active', s === name);
    const link = document.querySelector(`.tabs a[data-screen="${s}"]`);
    link.classList.toggle('active', s === name);
    if (s === name) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
    if (s !== name) views[s]?.onHide?.();
  }
  views[name]?.onShow?.();
  window.scrollTo({ top: 0 });
}

function navigate(name) {
  if (location.hash !== '#' + name) location.hash = name;
  else show(name);
}

const ctx = {
  state,
  navigate,
  /** Start an experiment search from anywhere (e.g. a Store callout). */
  findExperiments(goal) {
    navigate('experiments');
    views.experiments.start(goal);
  },
  prefillGoal(goal) {
    views.experiments.prefill(goal);
    navigate('experiments');
  },
  select(id) {
    state.selectedId = id;
    saveSession('storelab:selected', id);
    views.pilot?.refresh();
  },
  runFinished(done) {
    state.lastRun = done;
    saveSession('storelab:lastRun', done);
    ctx.select(done.recommendation?.candidate_id || null);
  },
  openAbout(section) { views.about.open(section); },
};

async function boot() {
  try {
    const [config, store, analytics, sample] = await Promise.all([
      getJSON('api/config'), getJSON('api/store'), getJSON('api/analytics'), getJSON('api/journeys/sample'),
    ]);
    Object.assign(state, { config, store, analytics, sample });
  } catch (err) {
    document.querySelector('main').innerHTML =
      `<div class="error-box">StoreLab could not load its data: ${esc(err.message)}. Is the API running?</div>`;
    return;
  }
  const pill = document.getElementById('demo-pill');
  const gemini = state.config.agent.mode !== 'offline';
  pill.classList.toggle('gemini', gemini);
  pill.title = gemini ? `Gemini · ${state.config.agent.model}` : 'Offline planner (no Gemini credentials)';
  views.about = mountAbout(document.getElementById('about-root'), ctx);
  pill.addEventListener('click', () => ctx.openAbout());
  document.querySelectorAll('[data-open-about]').forEach((b) => b.addEventListener('click', () => ctx.openAbout()));
  views.pilot = mountPilot(document.getElementById('screen-pilot'), ctx);
  views.experiments = mountExperiments(document.getElementById('screen-experiments'), ctx);
  views.store = mountStore(document.getElementById('screen-store'), ctx);
  window.addEventListener('hashchange', () => show(location.hash.slice(1)));
  show(location.hash.slice(1) || 'store');
}

boot();
