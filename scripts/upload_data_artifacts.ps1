param(
    [string]$Prefix = "global-commodity/v2"
)

$ErrorActionPreference = "Stop"

python scripts/prepare_data_artifacts.py
if ($LASTEXITCODE -ne 0) { throw "Artifact preparation failed." }

$loadedToken = $false
if (-not $env:BLOB_READ_WRITE_TOKEN) {
    vercel env pull .env.local --environment development --yes
    if ($LASTEXITCODE -ne 0) { throw "Unable to pull Blob credentials." }
    $tokenLine = Get-Content .env.local |
        Where-Object { $_ -like "BLOB_READ_WRITE_TOKEN=*" } |
        Select-Object -First 1
    if (-not $tokenLine) {
        throw "Connect a Vercel Blob store to this project before uploading."
    }
    $env:BLOB_READ_WRITE_TOKEN = ($tokenLine -split "=", 2)[1].Trim('"')
    $loadedToken = $true
}

$files = @(
    "trade_data.parquet",
    "cube_country_year_flow.parquet",
    "cube_category_year_flow.parquet",
    "cube_country_category_year.parquet",
    "cube_commodity_totals.parquet",
    "cube_year_records.parquet"
)

foreach ($file in $files) {
    vercel blob put "outputs/$file" `
        --access public `
        --pathname "$Prefix/$file" `
        --allow-overwrite true
    if ($LASTEXITCODE -ne 0) { throw "Failed to upload $file." }
}

if ($loadedToken) {
    Remove-Item Env:BLOB_READ_WRITE_TOKEN
}
