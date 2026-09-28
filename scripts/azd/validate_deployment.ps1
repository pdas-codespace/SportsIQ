$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$webUrl = (azd env get-value WEB_URL).Trim()
if (-not $webUrl) {
    throw "WEB_URL was not produced by provisioning."
}

$deadline = (Get-Date).AddMinutes(5)
do {
    try {
        $response = Invoke-WebRequest -Uri "$webUrl/login" -UseBasicParsing -TimeoutSec 20
        if ($response.StatusCode -eq 200) {
            Write-Host "Sports-IQ web application is healthy at $webUrl"
            exit 0
        }
    } catch {
        Start-Sleep -Seconds 10
    }
} while ((Get-Date) -lt $deadline)

throw "The deployed web application did not become healthy within five minutes: $webUrl"
