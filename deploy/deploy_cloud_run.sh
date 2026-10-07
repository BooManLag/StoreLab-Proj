#!/usr/bin/env bash
# Deploy StoreLab to Cloud Run with Gemini on Vertex AI (no API key: the service account is used).
#   PROJECT_ID=my-project ./deploy/deploy_cloud_run.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-asia-southeast1}"          # Singapore: JAPAC-first
SERVICE="${SERVICE:-storelab}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-3.5-flash}"
GEMINI_LOCATION="${GEMINI_LOCATION:-global}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "Set PROJECT_ID or run: gcloud config set project <id>" >&2
  exit 1
fi
cd "$(dirname "$0")/.."

echo "==> Enabling APIs in ${PROJECT_ID}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com --project "${PROJECT_ID}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "==> Granting ${RUNTIME_SA} Vertex AI access (Gemini) and Cloud Run build rights"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/aiplatform.user" --condition=None --quiet >/dev/null
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/run.builder" --condition=None --quiet >/dev/null

echo "==> Building and deploying ${SERVICE} to ${REGION}"
gcloud run deploy "${SERVICE}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi --cpu 2 \
  --timeout 600 \
  --concurrency 20 \
  --min-instances 0 --max-instances 3 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${GEMINI_LOCATION},GEMINI_MODEL=${GEMINI_MODEL}"

URL="$(gcloud run services describe "${SERVICE}" --project "${PROJECT_ID}" --region "${REGION}" --format='value(status.url)')"
echo "==> Deployed: ${URL}"
echo "    Check the agent mode: curl -s ${URL}/api/config"
