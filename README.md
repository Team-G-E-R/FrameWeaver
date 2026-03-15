# GameAssetsGenerator

## How to setup(PowerShell):

git submodule init
git submodule update

## run(repo root dir) :
doker compose build
docker compose up -d

## test payload
payload:
@'
{
  "type": "icon",
  "params": {
    "prompt": "pixel art icon of a red potion bottle, simple, centered, clean outline, high contrast, plain background",
    "width": 256,
    "height": 256,
    "steps": 12
  }
}
'@ | Set-Content -Encoding UTF8 payload.json

## second payload
@'
{
  "type": "icon",
  "params": {
    "prompt": "pixel art, 2d game sprite, small cute robot character, centered, full body, simple silhouette, clean outline, limited palette, plain background",
    "negative_prompt": "text, watermark, logo, blurry, low quality, noisy, artifact, jpeg artifacts, deformed, extra limbs, cropped",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 5,
    "sampler_name": "Euler a",
    "seed": 12345
  }
}
'@ | Set-Content -Encoding UTF8 payload.json

## job startup
$uid = "0de06f7f-41d6-4524-bb97-fae4efedd30d"
$resp = curl.exe -s -X POST "http://localhost:8000/api/jobs" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: $uid" `
  --data-binary "@payload.json"

$jobId = ($resp | ConvertFrom-Json).job_id
if (-not $jobId) { throw "job_id is empty. resp=$resp" }
$jobId

## then whait for succseed

do 
{
  Start-Sleep -Seconds 2
  $url = "http://localhost:8000/api/jobs/{0}" -f $jobId
  $j = Invoke-RestMethod -Method Get -Uri $url -Headers @{ "X-User-Id" = $uid }
  "{0}  {1}" -f $j.status, $jobId
} while ($j.status -in @("queued","running"))

## show generated image

$cid = docker compose ps -q worker
mkdir downloads -Force | Out-Null
docker cp "$cid`:/data/jobs/$jobId/out/result.png" ".\downloads\$jobId.png"
start ".\downloads\$jobId.png"