import { useCallback, useEffect, useRef, useState } from 'react';
import { streamLabRun } from '../api/client';
import type { DiagnosisInsight, LabDone, ObjectiveOverrides, StepLogEntry } from '../api/labTypes';
import { useApp } from '../context/AppContext';
import { Compose } from './experiments/Compose';
import { Progress, type RunProgress } from './experiments/Progress';
import { Results } from './experiments/Results';
import './Experiments.css';

interface LiveAccumulator {
  stepLog: StepLogEntry[];
  diagnosis: DiagnosisInsight[];
  overrides: ObjectiveOverrides | null;
  error: string | null;
  done: boolean;
}

function useLabRun(onDone: (done: LabDone) => void) {
  const [progress, setProgress] = useState<RunProgress>({ steps: {}, designed: 0, simulated: 0 });
  const [runError, setRunError] = useState<string | null>(null);
  const liveRef = useRef<LiveAccumulator | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  const start = useCallback((text: string, mode: 'fast' | 'thorough', overrides: ObjectiveOverrides | null) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    liveRef.current = { stepLog: [], diagnosis: [], overrides, error: null, done: false };
    setProgress({ steps: {}, designed: 0, simulated: 0 });
    setRunError(null);

    streamLabRun({ objective: text, mode, overrides: overrides ?? undefined }, (ev) => {
      const live = liveRef.current;
      if (!live) return;
      switch (ev.type) {
        case 'step':
          setProgress((p) => ({ ...p, steps: { ...p.steps, [ev.id]: ev.status } }));
          if (ev.status === 'done') live.stepLog.push({ title: ev.title, source: ev.source, detail: ev.detail, fallback: ev.fallback_reason ?? null });
          break;
        case 'candidate':
          setProgress((p) => ({ ...p, designed: p.designed + 1 }));
          break;
        case 'simulation':
          if (ev.status === 'done') setProgress((p) => ({ ...p, simulated: p.simulated + 1 }));
          break;
        case 'diagnosis':
          live.diagnosis = ev.insights;
          break;
        case 'error':
          live.error = ev.message;
          break;
        case 'done': {
          live.done = true;
          onDone({
            run_id: ev.run_id, objective: ev.objective, candidates: ev.candidates, ranking: ev.ranking,
            recommendation: ev.recommendation, plan: ev.plan, agent: ev.agent, gemini_calls: ev.gemini_calls,
            fallbacks: ev.fallbacks, tool_calls: ev.tool_calls, seconds: ev.seconds,
            steps: live.stepLog, diagnosis: live.diagnosis, overrides: live.overrides,
          });
          break;
        }
        default:
          break;
      }
    }, controller.signal).then(() => {
      if (!liveRef.current?.done) setRunError(liveRef.current?.error || 'The run ended before finishing. Please try again.');
    }).catch((err: unknown) => {
      if (err instanceof Error && err.name === 'AbortError') return;
      setRunError(err instanceof Error ? err.message : 'The run failed.');
    });
  }, [onDone]);

  // Leaving Experiments mid-run shouldn't leave an orphaned fetch streaming into a dead
  // component's state setters — the old app never needed this (its screens never unmounted).
  useEffect(() => () => controllerRef.current?.abort(), []);

  return { progress, runError, start };
}

export function Experiments() {
  const { data, lastRun, selectedId, navigate, select, runFinished, consumePendingGoal } = useApp();
  const [view, setView] = useState<'compose' | 'progress' | 'results'>(() => (lastRun ? 'results' : 'compose'));
  const [goalText, setGoalText] = useState('');
  const [initialGoal] = useState(() => consumePendingGoal() ?? '');

  const handleDone = useCallback((done: LabDone) => {
    runFinished(done);
    setView('results');
  }, [runFinished]);

  const { progress, runError, start } = useLabRun(handleDone);

  const handleStart = (text: string, mode: 'fast' | 'thorough', overrides: ObjectiveOverrides | null = null) => {
    setGoalText(text);
    setView('progress');
    start(text, mode, overrides);
  };

  if (view === 'progress') return <Progress goalText={goalText} progress={progress} />;

  if (view === 'results' && lastRun) {
    return (
      <Results
        done={lastRun}
        store={data.store}
        selectedId={selectedId}
        onSelect={select}
        onNewGoal={() => setView('compose')}
        onRerun={(text, overrides) => handleStart(text, 'fast', overrides)}
        onLaunchPilot={(id) => { select(id); navigate('pilot'); }}
      />
    );
  }

  return (
    <Compose
      briefing={data.analytics.summary.briefing}
      initialGoal={initialGoal}
      hasLastRun={!!lastRun}
      onShowLastRun={() => setView('results')}
      onStart={(text, mode) => handleStart(text, mode)}
      error={runError}
    />
  );
}
