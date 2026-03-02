param(
  [Parameter(Mandatory=$true)][string]$JobId,
  [string]$OutDir = ".\downloads",
  [string]$Service = "worker",
  [switch]$Open
)

$ErrorActionPreference = "Stop"

# контейнер worker
$cid = docker compose ps -q $Service
if (-not $cid) { throw "Container for service '$Service' not found (is it running?)" }

# куда сохраняем на хосте
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$outFile = Join-Path $OutDir "$JobId.png"

# путь внутри контейнера
$src = "/data/jobs/$JobId/out/result.png"

Write-Host "Copying $src -> $outFile"
docker cp "$cid`:$src" "$outFile" | Out-Null

Write-Host "Saved: $outFile"

if ($Open) {
  Start-Process $outFile
}