param(
  [string]$ImagePath = "sample.jpg",
  [string]$RequestId = "lrs_manual_test_001"
)

$uri = "http://127.0.0.1:8000/api/v1/road-damage/segment"
$form = @{
  file = Get-Item $ImagePath
  request_id = $RequestId
  return_mask = "true"
  return_overlay = "true"
  return_evidence_json = "true"
  min_area_pixels = "80"
}
Invoke-RestMethod -Uri $uri -Method Post -Form $form
