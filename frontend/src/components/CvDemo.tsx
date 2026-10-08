import { useEffect, useState } from 'react';
import { api, uploadCvClip } from '../api/client';
import type { CvResult } from '../api/cvTypes';
import type { StoreGeometry } from '../api/storeTypes';
import { CAT_LABEL, fmtInt } from '../lib/format';

/** "aisle_2" → "Snacks" when a category occupies that zone, else a title-cased fallback. */
function zoneLabel(store: StoreGeometry, zone: string): string {
  const cat = Object.entries(store.baseline_layout.category_slot).find(([, slot]) => slot === zone)?.[0];
  if (cat) return CAT_LABEL[cat] ?? cat;
  return zone.charAt(0).toUpperCase() + zone.slice(1);
}

export function CvDemo({ store }: { store: StoreGeometry }) {
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CvResult | null>(null);
  const [frameIdx, setFrameIdx] = useState(0);

  const run = async (promise: Promise<unknown>, label: string) => {
    if (status) return;
    setStatus(label);
    setError(null);
    try {
      setResult(await promise as CvResult);
      setFrameIdx(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setStatus(null);
    }
  };

  const frames = result?.previews.filter((p) => p.jpeg_base64) ?? [];

  useEffect(() => {
    if (!frames.length) return;
    const id = setInterval(() => setFrameIdx((i) => (i + 1) % frames.length), 600);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result]);

  const journeys = result?.tracks.filter((t) => t.journey.length).slice(0, 10) ?? [];

  return (
    <section>
      <h3>Camera pipeline</h3>
      <p className="secondary small">Person detection → tracking → camera-to-floor mapping → zone events. Frames are discarded after processing.</p>
      <div className="row" style={{ marginTop: 10 }}>
        <button
          type="button" className="btn" disabled={!!status}
          onClick={() => run(
            api.POST('/api/cv/demo').then((res) => { if (res.error) throw new Error('The demo clip failed to process.'); return res.data; }),
            'Processing the 45-second clip…',
          )}
        >
          Run on the demo camera clip
        </button>
        <label className="btn ghost" htmlFor="cv-file">Process your own clip…</label>
        <input
          type="file" id="cv-file" accept="video/*" className="sr-only" disabled={!!status}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = '';
            if (file) run(uploadCvClip(file), `Processing ${file.name}…`);
          }}
        />
        {status && <span className="small muted"><span className="spinner" /> {status}</span>}
      </div>

      {error && <div className="error-box" style={{ marginTop: 12 }}>{error}</div>}

      {result && (
        <div style={{ marginTop: 12 }}>
          <div className="cv-player">
            {frames.length > 0 && (
              <img src={`data:image/jpeg;base64,${frames[frameIdx % frames.length].jpeg_base64}`} alt="Camera frame with anonymous shopper boxes" />
            )}
          </div>
          <dl className="kv" style={{ marginTop: 10 }}>
            <dt>Anonymous tracks</dt><dd>{fmtInt(result.tracks.length)}</dd>
            {result.evaluation && (
              <>
                <dt>Shoppers found</dt><dd>{result.evaluation.people_tracked} of {result.evaluation.people_in_clip}</dd>
                <dt>Position accuracy</dt>
                <dd>{result.evaluation.mean_position_error_m != null ? `±${(result.evaluation.mean_position_error_m * 100).toFixed(0)} cm` : '–'}</dd>
                <dt>Shoppers split into 2 tracks</dt><dd>{result.evaluation.fragmented_people}</dd>
              </>
            )}
          </dl>
          <ul className="journey-list" style={{ marginTop: 10 }}>
            {journeys.map((t) => (
              <li key={t.anonymous_track_id}>
                <code>{t.anonymous_track_id}</code>
                <span>{t.journey.map((z) => zoneLabel(store, z)).join(' → ')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
