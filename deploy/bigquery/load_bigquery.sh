#!/usr/bin/env bash
# Create the StoreLab dataset in BigQuery and load the synthetic demo tables.
#   python -m storelab.export --out exports
#   PROJECT_ID=my-project ./deploy/bigquery/load_bigquery.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
DATASET="${DATASET:-storelab}"
LOCATION="${LOCATION:-asia-southeast1}"
EXPORTS="${EXPORTS:-exports}"
cd "$(dirname "$0")/../.."

echo "==> dataset ${PROJECT_ID}:${DATASET} (${LOCATION})"
bq --location="${LOCATION}" mk -f --dataset "${PROJECT_ID}:${DATASET}"

echo "==> tables"
# storelab.table -> `project.dataset.table`
sed "s/storelab\.\([a-z_]*\)/\`${PROJECT_ID}.${DATASET}.\1\`/g" deploy/bigquery/schema.sql \
  | bq query --use_legacy_sql=false --project_id="${PROJECT_ID}" --location="${LOCATION}"

for t in stores zones products journey_events transactions; do
  echo "==> loading ${t}"
  bq load --project_id="${PROJECT_ID}" --location="${LOCATION}" --source_format=CSV --skip_leading_rows=1 \
    --replace "${DATASET}.${t}" "${EXPORTS}/${t}.csv"
done
echo "Done. Try: SELECT zone_id, COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.journey_events\` GROUP BY 1"
