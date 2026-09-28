$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not on PATH."
    }
}

function Get-AzdValue {
    param([string]$Name)
    $value = azd env get-value $Name 2>$null
    if ($LASTEXITCODE -ne 0) { return "" }
    return $value.Trim()
}

function Set-AzdDefault {
    param([string]$Name, [string]$Value)
    if (-not (Get-AzdValue $Name)) {
        azd env set $Name $Value | Out-Null
    }
}

Require-Command az
Require-Command azd
Require-Command python

az account show --only-show-errors | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Azure CLI is not authenticated. Run 'az login' before 'azd up'."
}

Set-AzdDefault "ADMIN_USERNAME" "sportsiq-admin"
Set-AzdDefault "FOUNDRY_MODEL" "gpt-4.1"
Set-AzdDefault "SPORTS_IQ_SPORT" "basketball"
Set-AzdDefault "EVENTHOUSE_DB" "SportsIQ_Eventhouse"
Set-AzdDefault "LAKEHOUSE_DB" "SportsIQ_Lakehouse"

if (-not (Get-AzdValue "AUTH_SECRET")) {
    $bytes = [byte[]]::new(48)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $secret = [Convert]::ToBase64String($bytes)
    azd env set AUTH_SECRET $secret --secret | Out-Null
}

if (-not (Get-AzdValue "ADMIN_PASSWORD")) {
    $bytes = [byte[]]::new(24)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $password = [Convert]::ToBase64String($bytes)
    azd env set ADMIN_PASSWORD $password --secret | Out-Null
}

if (-not (Get-AzdValue "FOUNDRY_PROJECT_ENDPOINT")) {
    throw @"
FOUNDRY_PROJECT_ENDPOINT is required. Create or select a Microsoft Foundry
project, deploy the model named by FOUNDRY_MODEL, then run:
  azd env set FOUNDRY_PROJECT_ENDPOINT https://<account>.services.ai.azure.com/api/projects/<project>
"@
}

python data_generators/generate_all.py --output data/generated
if ($LASTEXITCODE -ne 0) {
    throw "Synthetic data generation failed."
}

python scripts/fabric_bootstrap.py
if ($LASTEXITCODE -ne 0) {
    throw "Fabric bootstrap failed. No deployment will continue with partial Fabric setup."
}
