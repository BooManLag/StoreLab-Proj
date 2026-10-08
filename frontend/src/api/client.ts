import createClient from 'openapi-fetch';
import type { components, paths } from './schema';
import type { Candidate, DiagnosisInsight, LabDoneRaw, ObjectiveSpec } from './labTypes';

export const api = createClient<paths>({ baseUrl: '/' });

/**
 * Uploads a clip to /api/cv/upload. Multipart + a bare `Response` return (no OpenAPI schema
 * either side), so this bypasses openapi-fetch the same way streamLabRun does for SSE.
 */
export async function uploadCvClip(file: File): Promise<unknown> {
  const body = new FormData();
  body.append('file', file);
  const res = await fetch('/api/cv/upload', { method: 'POST', body });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = (json as { detail?: unknown }).detail;
    throw new Error(typeof detail === 'string' ? detail : `Upload failed (${res.status})`);
  }
  return json;
}

/**
 * Server-sent events from POST /api/lab/run (storelab/agent.py LabAgent.run()).
 * FastAPI's OpenAPI schema doesn't cover a StreamingResponse body, so this
 * union is kept by hand against agent.py — see labTypes.ts for the shapes
 * shared with the final "done" event (ObjectiveSpec, Candidate, etc.).
 */
export type LabEvent =
  | { type: 'run'; run_id: string; agent: unknown; objective_text: string; simulated_journeys: number }
  | { type: 'step'; id: string; title: string; status: 'running' | 'done'; source: string; detail: string; fallback_reason?: string | null }
  | { type: 'objective'; objective: ObjectiveSpec; constraints: unknown; target_category: string }
  | { type: 'diagnosis'; insights: DiagnosisInsight[]; source: string }
  | { type: 'candidate'; candidate: Candidate }
  | { type: 'validation'; id: string; valid: boolean; errors: string[]; warnings: unknown; cost: number; descriptions: unknown; changes: unknown; layout: unknown }
  | { type: 'simulation'; id: string; status: 'running' | 'done'; result?: unknown; gate?: unknown }
  | { type: 'critique'; id: string; verdict: 'keep' | 'reject'; reason: string; source: string }
  | { type: 'review'; round: number; reasoning: string; source: string }
  | { type: 'ranking'; ranking: unknown }
  | { type: 'recommendation'; recommendation: unknown; plan: unknown; candidate: unknown }
  | ({ type: 'done' } & LabDoneRaw)
  | { type: 'error'; message: string };

export type LabRequest = components['schemas']['LabRequest'];

/**
 * Streams one AI Lab run. The endpoint is SSE (`Accept: text/event-stream`),
 * which openapi-fetch doesn't model, so this calls it directly — typed by
 * LabRequest/LabEvent above, same contract as the rest of the client.
 */
export async function streamLabRun(
  body: LabRequest,
  onEvent: (event: LabEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch('/api/lab/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`AI Lab run failed to start (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const flush = (chunk: string) => {
    for (const line of chunk.split('\n')) {
      if (line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)) as LabEvent);
    }
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buffer.indexOf('\n\n')) >= 0) {
      flush(buffer.slice(0, i));
      buffer = buffer.slice(i + 2);
    }
  }
  buffer += decoder.decode();
  if (buffer.trim()) flush(buffer);
}
