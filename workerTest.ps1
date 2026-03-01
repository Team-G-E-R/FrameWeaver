param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$UserId = "u1",
  [int]$SleepSec = 2,
  [int]$MaxWaitSec = 180
)

function Post-Job([string]$prompt) {
  $headers = @{
    "X-User-Id"    = $UserId
    "Content-Type" = "application/json"
  }

  $bodyObj = @{
    type   = "sprites"
    params = @{
      prompt = $prompt
    }
  }

  $body = $bodyObj | ConvertTo-Json -Depth 10

  try {
    $resp = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/jobs" -Headers $headers -Body $body
    return @{ Code = 200; Body = $resp }
  } catch {
    $status = $null
    $raw = $null

    try { $status = $_.Exception.Response.StatusCode.value__ } catch { $status = -1 }

    try {
      $stream = $_.Exception.Response.GetResponseStream()
      if ($stream) {
        $reader = New-Object System.IO.StreamReader($stream)
        $raw = $reader.ReadToEnd()
      }
    } catch {}

    if (-not $raw) { $raw = $_.ToString() }

    return @{ Code = $status; Raw = $raw; Sent = $body }
  }
}

function Get-Job([string]$jobId) {
  $headers = @{ "X-User-Id" = $UserId }
  return Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/jobs/$jobId" -Headers $headers
}

Write-Host "== 1) First POST (expect 200) =="

$r1 = Post-Job "test-1-$([guid]::NewGuid())"

if ($r1.Code -ne 200) {
  Write-Host "FAIL: expected 200 got $($r1.Code)" -ForegroundColor Red
  Write-Host "Response:"
  Write-Host $r1.Raw
  Write-Host "`nSent body:"
  Write-Host $r1.Sent
  exit 1
}

$jobId = $r1.Body.job_id
Write-Host "Created job: $jobId"

Write-Host "`n== 2) Second POST immediately (expect 409) =="

$r2 = Post-Job "test-2-$([guid]::NewGuid())"

if ($r2.Code -ne 409) {
  Write-Host "FAIL: expected 409 got $($r2.Code)" -ForegroundColor Red
  Write-Host $r2.Raw
  exit 1
}

Write-Host "OK: got 409 as expected"

Write-Host "`n== 3) Wait job to finish =="

$elapsed = 0

while ($true) {
  $job = Get-Job $jobId
  $status = $job.status
  Write-Host "Status: $status (elapsed ${elapsed}s)"

  if ($status -eq "succeeded" -or $status -eq "failed") {
    break
  }

  if ($elapsed -ge $MaxWaitSec) {
    Write-Host "FAIL: timeout waiting job finish" -ForegroundColor Red
    exit 1
  }

  Start-Sleep -Seconds $SleepSec
  $elapsed += $SleepSec
}

Write-Host "Finished with status: $status"

Write-Host "`n== 4) Third POST after completion (expect 200) =="

$r3 = Post-Job "test-3-$([guid]::NewGuid())"

if ($r3.Code -ne 200) {
  Write-Host "FAIL: expected 200 got $($r3.Code)" -ForegroundColor Red
  Write-Host $r3.Raw
  exit 1
}

Write-Host "OK: new job created: $($r3.Body.job_id)"

Write-Host "`nALL TESTS PASSED" -ForegroundColor Green