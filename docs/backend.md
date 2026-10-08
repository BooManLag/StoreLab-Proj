# FastAPI backend

The existing entry point remains `uvicorn storelab.main:app --port 8080`.
The API paths, static frontend, and SSE event format remain compatible.
Interactive OpenAPI docs are served at `/docs`, with the schema at `/openapi.json`.

## Structure

- `storelab/main.py`: ASGI entry point.
- `storelab/api/application.py`: `create_app()`, cache settings, startup/shutdown.
- `storelab/api/routes/`: resource routers for system, store, experiments, pilots,
  vision, and CSV exports. Each has a separate OpenAPI tag.
- `storelab/api/schemas.py`: Pydantic request contracts. Unknown top-level fields,
  non-finite numbers, and invalid numeric ranges are rejected.
- `storelab/api/dependencies.py`: `WorldDep` provides the shared world through
  `Depends(get_world)`. Tests can override `get_world` using FastAPI's
  `app.dependency_overrides`.
- `storelab/api/state.py`: application-scoped pilot records and AI run limiter.
- `storelab/api/cache.py`: bounded serialized response cache and conditional HTTP responses.
- `storelab/api/responses.py`: scientific Python values serialized as strict JSON.
- `storelab/api/web.py`: static frontend delivery.

Domain calculations stay in the existing analytics, simulator, agent, validator,
and pilot modules. Add HTTP contracts to schemas, use a resource router, and keep
business calculations in domain modules. Register new routers in `create_app()`.
The application factory allows independent cache, pilot, and rate-limit state in tests.
The immutable demo world and its existing simulator cache are shared in-process.

## Caching

`GET /api/store`, `/api/analytics`, and `/api/journeys/sample` cache serialized
JSON bytes. Repeated requests avoid rebuilding and serializing these payloads.
Cache keys include the world identity, data cache version, seed, build timestamp,
resource, and all validated query parameters. Replacing the world starts a new
namespace; expiry, LRU eviction, and shutdown clear retained responses.

| Setting | Default | Meaning |
| --- | --- | --- |
| `STORELAB_CACHE_TTL_SECONDS` | `60` | Lifetime after a response is built |
| `STORELAB_CACHE_MAX_ENTRIES` | `128` | Maximum number of responses |
| `STORELAB_CACHE_MAX_BYTES` | `16777216` | Maximum retained response-body bytes |

Set any setting to zero to disable server-side retention. Invalid negative or
non-finite settings fail at application creation. Metadata uses additional bounded
memory beyond the response-body budget. A lock coalesces concurrent cache misses;
keep cache factories short and synchronous. Failures and oversized bodies are not
cached. No external cache service or new dependency is required.

Cached reads return an ETag and `Cache-Control: private, no-cache`: clients can
retain a response but must revalidate. Matching `If-None-Match` returns 304; weak
validators and validator lists are supported. `X-Cache` reports HIT or MISS.
Disabling retention still permits ETag revalidation against a freshly built body.

Configuration, health, mutable pilots, uploads, and AI event streams are excluded
from this response cache. The existing versioned disk world cache and bounded
simulator result cache continue to work independently.

## Runtime and validation

Synchronous simulation and analytics routes run in FastAPI's worker thread pool.
Startup warms the world in a worker thread. Uploaded video processing also runs
in a worker thread, keeping CPU work off the async event loop; temporary video
files are removed in a `finally` block. AI SSE failures return a generic message
while details remain in server logs. Rate-limited AI requests include `Retry-After`.

Journey parameters now return 422 when out of range rather than silently clamping:
`day=0..6`, `start_hour=0..<24`, `minutes=5..120`, and `limit=1..200`.
Simulation budgets must be positive and at most PHP 10,000,000; the congestion
limit must be 0..100. Unknown top-level request fields are rejected.

```bash
.venv/bin/python -m pytest -q tests
```

The suite covers the product API and SSE workflow, cache hits/expiry/eviction,
concurrent misses, conditional responses, query isolation, world replacement,
application isolation, numeric validation, and video thread offloading.

This remains a single-process demo backend. Cache entries, pilot records, and
rate-limit counters are per process; pilots are lost on restart. Before scaling
across workers or replicas, introduce a persistent pilot repository and a shared
rate limiter (and a distributed response cache if needed). Authentication and
multi-tenant authorization are separate work; when adding tenants, include the
authorized store/tenant identity in cache keys. CPU-heavy production jobs may need
a bounded worker queue rather than sharing the HTTP worker pool.
