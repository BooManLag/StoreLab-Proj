const STEP_GROUPS = [
  { key: 'understand', label: 'Understanding your goal', ids: ['interpret', 'sense'] },
  { key: 'design', label: 'Designing store changes', ids: ['diagnose', 'design'] },
  { key: 'test', label: 'Testing each change on simulated shoppers', ids: ['simulate', 'review_1', 'resim_1', 'review_2', 'resim_2', 'final_review'] },
  { key: 'choose', label: 'Choosing the best option', ids: ['rank', 'recommend'] },
] as const;

export interface RunProgress {
  steps: Record<string, 'running' | 'done'>;
  designed: number;
  simulated: number;
}

function computeGroups(steps: Record<string, 'running' | 'done'>) {
  const doneSteps = new Set(Object.entries(steps).filter(([, v]) => v === 'done').map(([k]) => k));
  let activeFound = false;
  return STEP_GROUPS.map((s, i) => {
    const started = s.ids.some((id) => id in steps);
    const allDone = started && s.ids.filter((id) => id in steps).every((id) => doneSteps.has(id));
    const later = STEP_GROUPS.slice(i + 1).some((x) => x.ids.some((id) => id in steps));
    const isDone = allDone && later;
    const status: 'done' | 'active' | '' = isDone ? 'done' : !activeFound && started ? 'active' : '';
    if (!isDone && started) activeFound = true;
    return { key: s.key, label: s.label, status };
  });
}

export function Progress({ goalText, progress }: { goalText: string; progress: RunProgress }) {
  const groups = computeGroups(progress.steps);
  return (
    <div className="progress" aria-live="polite">
      <h2>Working on it…</h2>
      <p className="sub">&ldquo;{goalText}&rdquo;</p>
      <ol className="steps">
        {groups.map((g) => {
          const note = g.key === 'design' && progress.designed ? `${progress.designed} ideas`
            : g.key === 'test' && progress.designed ? `${progress.simulated} of ${progress.designed} tested`
            : '';
          return (
            <li key={g.key} className={g.status}>
              <span className="mark">{g.status === 'done' ? '✓' : g.status === 'active' ? <span className="spinner" /> : null}</span>
              <span>{g.label}</span>
              <span className="note">{note}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
