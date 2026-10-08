import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import type { AnalyticsResponse, ConfigResponse, JourneySample, StoreGeometry } from '../api/storeTypes';
import type { LabDone } from '../api/labTypes';
import type { Screen } from '../hooks/useHashRoute';
import { loadSession, saveSession } from '../lib/storage';

export interface BaseData {
  config: ConfigResponse;
  store: StoreGeometry;
  analytics: AnalyticsResponse;
  sample: JourneySample;
}

interface AppContextValue {
  data: BaseData;
  lastRun: LabDone | null;
  selectedId: string | null;
  /** Set once by a Store/Pilot action, consumed once by Experiments' compose view. */
  pendingGoal: string | null;
  navigate: (screen: Screen) => void;
  select: (id: string | null) => void;
  runFinished: (done: LabDone) => void;
  /** Prefill the Experiments composer with a goal and switch to that screen — the old app's ctx.prefillGoal + ctx.navigate. */
  requestExperiment: (goal: string) => void;
  consumePendingGoal: () => string | null;
}

const AppCtx = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error('useApp() called outside AppProvider');
  return ctx;
}

/** Fetches the base data once (config/store/analytics/sample — every screen reads it), then provides shared cross-screen state. */
export function AppProvider({ navigate, children }: { navigate: (screen: Screen) => void; children: ReactNode }) {
  const [data, setData] = useState<BaseData | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Survive a refresh, same as the old app (storelab:lastRun / storelab:selected in sessionStorage) —
  // losing an in-progress-reviewed or just-finished AI Lab run to an accidental reload is a real regression otherwise.
  const [lastRun, setLastRun] = useState<LabDone | null>(() => loadSession('storelab:lastRun'));
  const [selectedId, setSelectedId] = useState<string | null>(() => loadSession('storelab:selected'));
  const [pendingGoal, setPendingGoal] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [config, store, analytics, sample] = await Promise.all([
          api.GET('/api/config'),
          api.GET('/api/store'),
          api.GET('/api/analytics'),
          api.GET('/api/journeys/sample'),
        ]);
        if (config.error || store.error || analytics.error || sample.error) throw new Error('Request failed');
        if (cancelled) return;
        setData({
          config: config.data as ConfigResponse,
          store: store.data as StoreGeometry,
          analytics: analytics.data as AnalyticsResponse,
          sample: sample.data as JourneySample,
        });
      } catch {
        if (!cancelled) setError('StoreLab could not load its data. Is the API running?');
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const select = useCallback((id: string | null) => {
    setSelectedId(id);
    saveSession('storelab:selected', id);
  }, []);
  const runFinished = useCallback((done: LabDone) => {
    setLastRun(done);
    saveSession('storelab:lastRun', done);
    const recId = done.recommendation?.candidate_id ?? null;
    setSelectedId(recId);
    saveSession('storelab:selected', recId);
  }, []);
  const requestExperiment = useCallback((goal: string) => {
    setPendingGoal(goal);
    navigate('experiments');
  }, [navigate]);
  const consumePendingGoal = useCallback(() => {
    let goal: string | null = null;
    setPendingGoal((current) => { goal = current; return null; });
    return goal;
  }, []);

  const value = useMemo<AppContextValue | null>(() => data && {
    data, lastRun, selectedId, pendingGoal, navigate, select, runFinished, requestExperiment, consumePendingGoal,
  }, [data, lastRun, selectedId, pendingGoal, navigate, select, runFinished, requestExperiment, consumePendingGoal]);

  if (error) return <div className="screen-placeholder" style={{ padding: 'var(--space-8)' }}><p className="secondary">{error}</p></div>;
  if (!value) return <div className="screen-placeholder" style={{ padding: 'var(--space-8)' }}><p className="secondary">Loading StoreLab…</p></div>;
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}
