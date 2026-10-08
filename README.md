# StoreLab: A/B testing for physical retail

**Understand the store. Simulate the change. Test what matters.**

StoreLab turns anonymous shopper movement and POS baskets into a behavioural digital twin
of a store. A manager states a goal in plain language (any language). A Gemini-powered
agent then designs physical experiments and runs each one on synthetic shoppers. It
rejects designs that break constraints, revises them, and recommends the best one for a
real-store A/B pilot.

> Everything in this MVP runs on **clearly labelled synthetic demo data**: a fictional
> convenience store ("Demo Mart BGC"), 10,000 anonymous journeys over 7 days, about 2,000
> POS transactions, and a rendered CCTV clip.

## What the MVP does (spec §17)

| # | Capability | Where |
|---|---|---|
| 1 | **Video → anonymous trajectories.** Detection, multi-object tracking, homography to floor metres, zone events. Scored against ground truth: about 95% recall, 6 cm mean error. | `storelab/cv/`, *About the data* drawer |
| 2 | **Trajectories → heatmap and zone transitions**, plus dwell, backtracking, dead zones and journey clusters. | `analytics.py`, Store |
| 3 | **POS join → physical shopping funnel.** Baskets are linked to journeys by checkout-time matching (no identity), giving visited → engaged → purchased per aisle. | `analytics.py` |
| 4 | **Plain-language objective** (EN / 日本語 / 한국어 / Bahasa / Filipino), normalised into metric, target, budget and constraints, then editable as chips. | Experiments |
| 5 | **Gemini designs three candidate experiments** as structured JSON changes, using the floor-plan image and the twin's metrics. | `agent.py` |
| 6 | **The simulator runs each candidate** on the fitted twin. Every candidate is tested on the same 40,000 synthetic shoppers, with paired 95% CIs. | `simulator.py`, `engine.py` |
| 7 | **The AI rejects poor candidates, revises them, and recommends a physical experiment.** It sizes a test-vs-control pilot with a power calculation. | Experiments → Pilot |

### The product: three screens, built around *Problem → Options → Test*

- **Store.** The map is the hero. StoreLab marks one **opportunity**, one **friction** and one
  **pattern** on it, each with a next step. Clicking an aisle shows plain tags, with the
  evidence available on request. Raw analytics sit under *View analytics*.
- **Experiments.** You state the goal and get the best store change: a large before/after
  simulation, then impact, risk, cost and a one-line why. Alternatives sit below, rejected
  ideas are collapsed, and the goal chips (budget, target, checkout limit) are editable and
  re-run the search.
- **Pilot.** "Ready to test": the number of test and control stores, the duration, the
  success condition, and one Launch button.

The machinery (Gemini calls, tool calls, constraint checks, confidence ranges, the
simulation setup) stays one click away under **How StoreLab decided** and in the
**About the data** drawer. Judges see the whole system; managers see a decision.

### The rules from the spec that the code enforces
- **Gemini is never the simulator.** It proposes structured `Change`s. `validator.py`
  checks movability, refrigeration, budget, accessibility (clear walkway), the emergency
  egress route, geometry and experiment size. `simulator.py` produces every number.
- **Hard constraints override the AI.** If Gemini wants to keep a candidate that breaks
  the congestion limit, the constraint check rejects it, and the UI says who decided.
- **Hypotheses, not conclusions.** Prompts require hypotheses and allow only numbers that
  came from tool outputs. Simulation is presented as a pre-screen for a real A/B test.
- **Privacy.** There are only random track IDs (`anon_xxxxxx`): no faces, names or
  cross-visit identity. Uploaded video is deleted after processing.

## How the twin works (and why its numbers can be trusted)

1. **The hidden world** (`groundtruth.py`) generates the synthetic history from shopping
   *missions* that no other module can see.
2. **Analytics and fitting** (`analytics.py`, `fit.py`) use only what cameras and POS
   would record:
   - k-means journey clusters;
   - a conditional-logit zone-choice model (walking distance, complement pull, revisit
     penalty, "done");
   - a noisy-OR purchase model (aisle visits, promo-display interactions);
   - complements learned from behaviour;
   - checkout service time regressed from idle-counter customers.
3. **The simulator** replays shoppers on any layout. Free-standing displays change the
   A* walking paths. Displays sell mostly to "primed" shoppers. Checkout queues are a FIFO
   discrete-event simulation.
4. **Verification.** The twin reproduces the observed store to within a few percent
   (worst row about 12%), shown in the *About the data* drawer. On candidate
   experiments it predicts the sign of the hidden world's true effect, and its ranking
   matches the hidden truth's (`tests/test_fit_and_sim.py`).

The one modelled assumption is the extra counter time when a queueing shopper engages a
checkout rack (12 s). No rack exists in the baseline data to learn it from, so it is
labelled as an assumption in the UI.

## Run locally

```bash
python -m venv .venv
```
```bash
.venv/bin/pip install -r requirements-dev.txt
```
```bash
.venv/bin/uvicorn storelab.main:app --port 8080
```
On Windows, use `.venv\Scripts\pip` and `.venv\Scripts\uvicorn`. Open http://localhost:8080.

The first start builds the synthetic world (about 15 s) and caches it in `data/`. Without
Gemini credentials the agent runs as the **offline heuristic planner**: same loop, same
tools, rule-based judgement. The UI labels it on every step.

To use Gemini locally, put `GEMINI_API_KEY=...` in `.env` (see `.env.example`) and start with:
```bash
.venv/bin/uvicorn storelab.main:app --port 8080 --env-file .env
```

### Tests
```bash
.venv/bin/python -m pytest -q tests
```
67 tests cover: geometry, data volumes, anonymity, the POS join, model recovery,
calibration, simulator determinism, common random numbers, ranking agreement with the
hidden truth, every validator rule, the multilingual parser, the agent loop (offline, fake
Gemini, Gemini outage fallback, retry on bad JSON), CV accuracy and the HTTP API
(including the SSE stream).

## Deploy to Google Cloud (Cloud Run + Gemini on Vertex AI)

Prerequisite: the `gcloud` CLI, logged in, with billing enabled on the project.

```bash
PROJECT_ID=your-project ./deploy/deploy_cloud_run.sh
```
On Windows:
```powershell
.\deploy\deploy_cloud_run.ps1 -ProjectId your-project
```

The script:
- enables the Run, Cloud Build, Artifact Registry and Vertex AI APIs;
- grants the runtime service account `roles/aiplatform.user` (and `roles/run.builder` for source builds);
- builds the Dockerfile (the world and the demo clip are pre-built at build time, so cold starts only load a cache);
- deploys to `asia-southeast1` with `GOOGLE_GENAI_USE_VERTEXAI=true`. No API key is needed.

Check `https://<service-url>/api/config`: `agent.mode` should read `vertex-ai`.

**Optional: BigQuery.** Run `python -m storelab.export --out exports`, then
`PROJECT_ID=... ./deploy/bigquery/load_bigquery.sh`. This creates all eight data-model
tables (`deploy/bigquery/schema.sql`) and loads the synthetic data.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | unset, unset, `global` | Gemini via Vertex AI |
| `GEMINI_API_KEY` | unset | Gemini Developer API (alternative) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | any current Gemini model id |
| `GEMINI_THINKING_LEVEL` | `low` | `minimal`/`low`/`medium`/`high`/`default`; dropped automatically if a model rejects it |
| `GEMINI_TIMEOUT_S` | `90` | per-request timeout |
| `STORELAB_AGENT_MODE` | auto | `offline` forces the heuristic planner |
| `STORELAB_LAB_RUNS_PER_MINUTE` | `6` | per-instance rate limit (protects Gemini quota) |
| `STORELAB_SEED` | `20261018` | synthetic world seed |

Temperature is deliberately left at the model default: Google advises against lowering it
for Gemini 3 models.

## API

The backend uses modular FastAPI routers, dependency injection, and bounded response
caching. See [Backend development](docs/backend.md) for structure, cache settings,
validation contracts, and scaling limits.

| Method | Path | |
|---|---|---|
| GET | `/api/config`, `/api/store`, `/api/analytics`, `/api/journeys/sample` | twin, metrics, heatmap, calibration |
| POST | `/api/lab/run` `{objective, mode: fast/thorough, overrides?}` | **SSE stream** of the agent loop (`step`, `tool`, `candidate`, `simulation`, `critique`, `recommendation`, `done`) |
| POST | `/api/tracks` `{category_slot, displays}` | animated virtual shoppers for any layout (the same shoppers every time) |
| POST | `/api/pilot/plan` `{objective, candidate}` | pilot plan for any experiment the manager picks |
| POST | `/api/simulate` `{changes[], metric, category, budget_php}` | manual what-if |
| POST | `/api/cv/demo`, `/api/cv/upload` (multipart video + optional calibration) | Sense pipeline |
| POST/GET | `/api/pilots` | schedule / list physical pilots (in memory) |
| GET | `/api/data/{stores,zones,products,journey_events,transactions}.csv` | data-model exports |

Interactive docs: `/docs`.

## Repository map

```
storelab/
  store.py         demo store: fixtures, aisles, display slots, products, costs, constraints
  geometry.py      occupancy grid, A* + string pulling, display exposure, heat footprints
  engine.py        shared agent-based shopper engine + checkout queue (common random numbers)
  groundtruth.py   hidden synthetic world -> observed history (SYNTHETIC)
  analytics.py     POS join, funnels, transitions, clusters, heatmap, insights
  fit.py           behaviour-model calibration from observed data only
  simulator.py     StoreLab Sim: runs, paired CIs, comparisons
  validator.py     Constraint Validator
  objective.py     objective schema + multilingual offline parser
  tools.py         the agent's tools (spec §13)
  agent.py         StoreLab Agent loop (Gemini + per-step offline fallback)
  llm.py           google-genai wrapper: JSON-schema outputs, validation, retry
  planner_offline.py  heuristic planner used without Gemini
  pilot.py         StoreLab Pilot: test/control selection + power analysis
  cv/              synthetic CCTV renderer + detection/tracking/homography pipeline
  world.py, bootstrap.py, export.py, main.py
web/               no-build ES-module frontend: Store, Experiments, Pilot + About drawer
deploy/            Cloud Run scripts, BigQuery schema + loader
tests/             pytest suite
```

## Honest limitations (say these before a judge asks)
- **The data is synthetic.** The hidden world and the twin share a model *family*, so the
  twin is better specified than it would be in a real store. Real deployments must earn
  trust through physical pilots. The schema has a `physical_experiment_results` table so
  pilot outcomes can recalibrate the simulator.
- **Display effects are pooled** across categories, because the baseline store has only
  two promo displays to learn from.
- **The CV detector** is background subtraction, suited to fixed ceiling cameras. A deep
  person detector can replace `detect()` without touching the tracker.
- **Pilots are stored in memory.** Firestore, Firebase Auth, Pub/Sub, Vector Search and
  the Store Mapper (drawing zones) are next steps from spec §8, not part of the §17 MVP.
