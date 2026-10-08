import { lazy, Suspense, useRef } from 'react';
import './App.css';
import { useHashRoute, type Screen } from './hooks/useHashRoute';
import { AppProvider, useApp } from './context/AppContext';
import { Pilot } from './screens/Pilot';
import { About, type AboutHandle } from './screens/About';

// Store and Experiments both embed the Three.js StoreScene (~700KB) — split them into their
// own chunks so Pilot/About don't pay for a 3D scene they never load.
const Store = lazy(() => import('./screens/Store').then((m) => ({ default: m.Store })));
const Experiments = lazy(() => import('./screens/Experiments').then((m) => ({ default: m.Experiments })));

const SCREEN_LABELS: Record<Screen, string> = { store: 'Store', experiments: 'Experiments', pilot: 'Pilot' };
const SCREEN_ORDER: Screen[] = ['store', 'experiments', 'pilot'];

function ScreenBody({ screen }: { screen: Screen }) {
  switch (screen) {
    case 'store': return <Suspense fallback={<p className="secondary">Loading the store…</p>}><Store /></Suspense>;
    case 'experiments': return <Suspense fallback={<p className="secondary">Loading…</p>}><Experiments /></Suspense>;
    case 'pilot': return <Pilot />;
  }
}

function DemoPill({ onOpen }: { onOpen: () => void }) {
  const { data } = useApp();
  const gemini = data.config.agent.mode !== 'offline';
  return (
    <button
      type="button"
      className={`demo-pill${gemini ? ' gemini' : ''}`}
      aria-haspopup="dialog"
      title={gemini ? `Gemini · ${data.config.agent.model}` : 'Offline planner (no Gemini credentials)'}
      onClick={onOpen}
    >
      <span className="dot" aria-hidden="true" />
      <span>Demo mode</span>
    </button>
  );
}

function App() {
  const [screen, navigate] = useHashRoute();
  const aboutRef = useRef<AboutHandle>(null);

  return (
    <AppProvider navigate={navigate}>
      <header className="topbar">
        <a className="brand" href="#store" aria-label="StoreLab home">
          <span className="logo" aria-hidden="true">SL</span>
          <span className="wordmark">StoreLab</span>
        </a>
        <nav className="tabs" aria-label="Screens">
          {SCREEN_ORDER.map((s) => (
            <a
              key={s}
              href={`#${s}`}
              data-screen={s}
              className={s === screen ? 'active' : undefined}
              aria-current={s === screen ? 'page' : undefined}
              onClick={(e) => { e.preventDefault(); navigate(s); }}
            >
              {SCREEN_LABELS[s]}
            </a>
          ))}
        </nav>
        <DemoPill onOpen={() => aboutRef.current?.open()} />
      </header>

      <main>
        <ScreenBody screen={screen} />
      </main>

      <footer className="site-footer">
        <span>Demo Mart BGC is a fictional store. Shoppers are tracked anonymously — no faces, names or cross-visit identity.</span>
        <button type="button" className="btn ghost" onClick={() => aboutRef.current?.open()}>
          About the data &amp; how StoreLab works
        </button>
      </footer>

      <About ref={aboutRef} />
    </AppProvider>
  );
}

export default App;
