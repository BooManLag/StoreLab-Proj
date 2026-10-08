import { useState } from 'react';
import type { BriefingItem } from '../../api/storeTypes';

const EXAMPLES = [
  { label: '日本語', text: 'スナックの売上を10%伸ばしたい。予算は3万ペソ。レジの混雑は増やさないこと。冷蔵庫は動かせない。' },
  { label: '한국어', text: '커피 동반 구매율을 높이고 싶어요. 예산 5만 페소, 계산대 혼잡은 늘리지 마세요.' },
  { label: 'Bahasa', text: 'Tingkatkan penjualan camilan 10% tanpa menambah antrean kasir. Anggaran ₱30.000.' },
  { label: 'Filipino', text: 'Dagdagan ang benta ng snacks ng 10%, budget P30,000, huwag dagdagan ang pila sa kahera.' },
];

export function Compose({
  briefing, initialGoal, hasLastRun, onShowLastRun, onStart, error,
}: {
  briefing: BriefingItem[];
  initialGoal: string;
  hasLastRun: boolean;
  onShowLastRun: () => void;
  onStart: (text: string, mode: 'fast' | 'thorough') => void;
  error: string | null;
}) {
  const briefGoals = briefing.filter((b) => b.action.type === 'goal');
  const [text, setText] = useState(initialGoal || briefGoals[0]?.action.goal || '');
  const [mode, setMode] = useState<'fast' | 'thorough'>('fast');

  return (
    <div className="composer">
      <h1>What do you want to improve?</h1>
      <p className="lede">
        Say it the way you would to a colleague — the goal, the budget, what must not change.
        StoreLab designs store changes and tests them on simulated shoppers before you touch the real floor.
      </p>
      {error && <div className="error-box" style={{ marginBottom: 'var(--space-3)', textAlign: 'left' }}>{error}</div>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const v = text.trim();
          if (v.length < 3) return;
          onStart(v, mode);
        }}
      >
        <label htmlFor="exp-text" className="sr-only">Your goal</label>
        <textarea id="exp-text" maxLength={600} required value={text} onChange={(e) => setText(e.target.value)} />
        <div className="suggest">
          {briefGoals.map((b, i) => (
            <button key={i} type="button" className="chip" onClick={() => setText(b.action.goal ?? '')}>{b.action.label}</button>
          ))}
          {EXAMPLES.map((ex) => (
            <button key={ex.label} type="button" className="chip" onClick={() => setText(ex.text)}>{ex.label}</button>
          ))}
        </div>
        <div className="go-row">
          <div className="seg" role="group" aria-label="Search depth">
            <button type="button" aria-pressed={mode === 'fast'} onClick={() => setMode('fast')}>Fast</button>
            <button type="button" aria-pressed={mode === 'thorough'} onClick={() => setMode('thorough')}>Thorough</button>
          </div>
          <button type="submit" className="btn primary big">Find experiments →</button>
        </div>
      </form>
      {hasLastRun && (
        <p className="small" style={{ marginTop: 'var(--space-6)' }}>
          <button type="button" className="link-btn" onClick={onShowLastRun}>See your last results</button>
        </p>
      )}
    </div>
  );
}
