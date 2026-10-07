-- StoreLab data model (spec §10) for BigQuery. Replace `storelab` with your dataset name.
-- Load the synthetic demo tables with deploy/bigquery/load_bigquery.sh.

CREATE TABLE IF NOT EXISTS storelab.stores (
  store_id STRING NOT NULL, name STRING, region STRING, currency STRING, timezone STRING,
  floorplan_url STRING, width_m FLOAT64, depth_m FLOAT64
);

CREATE TABLE IF NOT EXISTS storelab.zones (
  zone_id STRING NOT NULL, store_id STRING NOT NULL, name STRING, category STRING,
  polygon STRING,          -- JSON array of [x, y] floor points in metres
  movable BOOL, kind STRING
);

CREATE TABLE IF NOT EXISTS storelab.products (
  sku STRING NOT NULL, name STRING, category STRING, price FLOAT64, margin FLOAT64,
  current_zone STRING, promotion BOOL
);

-- Anonymous only: an ephemeral track id, never a person.
CREATE TABLE IF NOT EXISTS storelab.journey_events (
  anonymous_track_id STRING NOT NULL, timestamp TIMESTAMP NOT NULL, store_id STRING NOT NULL,
  zone_id STRING, x FLOAT64, y FLOAT64, event_type STRING, dwell_seconds FLOAT64
)
PARTITION BY DATE(timestamp)
CLUSTER BY store_id, zone_id;

CREATE TABLE IF NOT EXISTS storelab.transactions (
  transaction_id STRING NOT NULL, store_id STRING NOT NULL, timestamp TIMESTAMP NOT NULL,
  sku STRING, category STRING, quantity INT64, price FLOAT64, revenue FLOAT64, discount FLOAT64
)
PARTITION BY DATE(timestamp)
CLUSTER BY store_id, category;

CREATE TABLE IF NOT EXISTS storelab.experiments (
  experiment_id STRING NOT NULL, objective STRING, constraints JSON, layout_version STRING,
  status STRING, created_by STRING, created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS storelab.simulation_runs (
  run_id STRING NOT NULL, experiment_id STRING NOT NULL, simulated_visitors INT64,
  predicted_conversion FLOAT64, predicted_revenue FLOAT64, predicted_congestion FLOAT64,
  confidence_interval JSON, created_at TIMESTAMP
);

-- Real-world pilot results: the data that calibrates StoreLab Sim over time.
CREATE TABLE IF NOT EXISTS storelab.physical_experiment_results (
  experiment_id STRING NOT NULL, store_id STRING NOT NULL, control_store_id STRING,
  actual_conversion_delta FLOAT64, actual_revenue_delta FLOAT64, actual_congestion_delta FLOAT64,
  measured_at TIMESTAMP
);
