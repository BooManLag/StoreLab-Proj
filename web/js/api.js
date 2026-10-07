// API client. The AI Lab run is a POST that streams server-sent events.

async function errorMessage(r) {
  try {
    const j = await r.json();
    if (typeof j.detail === 'string') return j.detail;
    if (Array.isArray(j.detail)) return j.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  } catch (_) { /* not JSON */ }
  return `Request failed (${r.status})`;
}

export async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await errorMessage(r));
  return r.json();
}

export async function postJSON(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await errorMessage(r));
  return r.json();
}

export async function streamLab(body, onEvent, signal) {
  const r = await fetch('api/lab/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  });
  if (!r.ok) throw new Error(await errorMessage(r));
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const flush = (chunk) => {
    for (const line of chunk.split('\n')) {
      if (line.startsWith('data: ')) onEvent(JSON.parse(line.slice(6)));
    }
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let i;
    while ((i = buffer.indexOf('\n\n')) >= 0) {
      flush(buffer.slice(0, i));
      buffer = buffer.slice(i + 2);
    }
  }
  buffer += decoder.decode();
  if (buffer.trim()) flush(buffer);
}
