import type { LabDone, PilotPlan, PilotStoreRow } from '../api/labTypes';
import { fmtSigned } from './format';
import { rangeText } from './present';

const list = (xs: string[]) => xs.map((v) => `- ${v}`).join('\n');
const stores = (xs: PilotStoreRow[]) => xs.map((s) => `- ${s.store_id} · ${s.name} (${s.weekly_visitors.toLocaleString('en-US')} visitors/week)`).join('\n');

export function pilotToMarkdown(run: LabDone, p: PilotPlan, title: string, isRec: boolean): string {
  const e = p.expected;
  const why = isRec ? run.recommendation?.explanation.why : null;
  return `# Pilot: ${title}

Goal: ${run.objective.raw_text}

## The change
${list(p.changes)}

${why ? `## Why\n${why}\n\n` : ''}## Expected (simulated)
- ${p.primary_kpi}: ${fmtSigned(e.primary_pct)} (likely ${rangeText(e.primary_ci_pct[0], e.primary_ci_pct[1])})
- Checkout queue: ${fmtSigned(e.congestion_pct)} (likely ${rangeText(e.congestion_ci_pct[0], e.congestion_ci_pct[1])})
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
