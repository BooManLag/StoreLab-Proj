# Deploy StoreLab to Cloud Run with Gemini on Vertex AI (Windows PowerShell).
#   .\deploy\deploy_cloud_run.ps1 -ProjectId my-project
param(
  [string]$ProjectId = (gcloud config get-value project 2>$null),
  [string]$Region = "asia-southeast1",
  [string]$Service = "storelab",
  [string]$GeminiModel = "gemini-3.5-flash",
  [string]$GeminiLocation = "global"
)
$ErrorActionPreference = "Stop"
if (-not $ProjectId) { throw "Pass -ProjectId or run: gcloud config set project <id>" }
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Enabling APIs in $ProjectId"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com --project $ProjectId
if ($LASTEXITCODE -ne 0) { throw "Enabling APIs failed" }

$ProjectNumber = gcloud projects describe $ProjectId --format="value(projectNumber)"
$RuntimeSa = "$ProjectNumber-compute@developer.gserviceaccount.com"

Write-Host "==> Granting $RuntimeSa Vertex AI access (Gemini) and Cloud Run build rights"
foreach ($role in @("roles/aiplatform.user", "roles/run.builder")) {
  gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$RuntimeSa" --role=$role --condition=None --quiet | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Granting $role failed" }
}

Write-Host "==> Building and deploying $Service to $Region"
gcloud run deploy $Service `
  --source . `
  --project $ProjectId `
  --region $Region `
  --allow-unauthenticated `
  --memory 2Gi --cpu 2 `
  --timeout 600 `
  --concurrency 20 `
  --min-instances 0 --max-instances 3 `
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$GeminiLocation,GEMINI_MODEL=$GeminiModel"
if ($LASTEXITCODE -ne 0) { throw "Deploy failed" }

$Url = gcloud run services describe $Service --project $ProjectId --region $Region --format="value(status.url)"
Write-Host "==> Deployed: $Url"
Write-Host "    Check the agent mode: $Url/api/config"
