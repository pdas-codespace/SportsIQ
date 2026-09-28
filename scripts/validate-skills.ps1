<#
.SYNOPSIS
    Validate Sports-IQ customization assets — SKILL.md, *.agent.md, *.instructions.md, *.prompt.md.

.DESCRIPTION
    Walks .github/skills, .github/agents, .github/instructions, .github/prompts and verifies
    that each asset has the required YAML frontmatter keys. Exits with code 1 on any failure
    so CI can gate PRs on the result.

    Run locally:
        pwsh ./scripts/validate-skills.ps1

    Run with verbose output:
        pwsh ./scripts/validate-skills.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()

function Read-Frontmatter {
    param([string]$Path)

    $lines = Get-Content -Path $Path -ErrorAction Stop
    if ($lines.Count -lt 3) { return $null }
    if ($lines[0].Trim() -ne '---') { return $null }

    $end = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') { $end = $i; break }
    }
    if ($end -lt 1) { return $null }

    $body = $lines[1..($end - 1)] -join "`n"
    $map = @{}
    foreach ($line in $body -split "`n") {
        if ($line -match '^\s*([A-Za-z0-9_-]+)\s*:\s*(.*)$') {
            $map[$matches[1]] = $matches[2].Trim()
        }
    }
    return $map
}

function Test-Frontmatter {
    param(
        [string]$Path,
        [string[]]$Required,
        [string]$AssetType
    )

    $rel = $Path.Substring($RepoRoot.Length).TrimStart('\','/')
    Write-Verbose "checking $rel"

    $fm = Read-Frontmatter -Path $Path
    if ($null -eq $fm) {
        $failures.Add("[$AssetType] $rel — missing or malformed YAML frontmatter")
        return
    }

    foreach ($key in $Required) {
        if (-not $fm.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($fm[$key])) {
            $failures.Add("[$AssetType] $rel — missing required key '$key'")
        }
    }
}

# 1. Skills
$skillsRoot = Join-Path $RepoRoot '.github/skills'
if (Test-Path $skillsRoot) {
    Get-ChildItem -Path $skillsRoot -Directory | ForEach-Object {
        $skillFile = Join-Path $_.FullName 'SKILL.md'
        if (-not (Test-Path $skillFile)) {
            $failures.Add("[skill] $($_.Name) — missing SKILL.md")
            return
        }
        Test-Frontmatter -Path $skillFile `
            -Required @('name','description','argument-hint','user-invocable','disable-model-invocation') `
            -AssetType 'skill'

        $fm = Read-Frontmatter -Path $skillFile
        if ($fm -and $fm['name'] -ne $_.Name) {
            $failures.Add("[skill] $($_.Name) — frontmatter name '$($fm['name'])' does not match folder name")
        }
    }
}

# 2. Agents
$agentsRoot = Join-Path $RepoRoot '.github/agents'
if (Test-Path $agentsRoot) {
    Get-ChildItem -Path $agentsRoot -Recurse -Filter '*.agent.md' | ForEach-Object {
        Test-Frontmatter -Path $_.FullName `
            -Required @('name','description') `
            -AssetType 'agent'
    }
}

# 3. Instructions
$instructionsRoot = Join-Path $RepoRoot '.github/instructions'
if (Test-Path $instructionsRoot) {
    Get-ChildItem -Path $instructionsRoot -Filter '*.instructions.md' | ForEach-Object {
        Test-Frontmatter -Path $_.FullName `
            -Required @('applyTo') `
            -AssetType 'instruction'
    }
}

# 4. Prompts (repo convention: name, description, agent, argument-hint)
$promptsRoot = Join-Path $RepoRoot '.github/prompts'
if (Test-Path $promptsRoot) {
    Get-ChildItem -Path $promptsRoot -Filter '*.prompt.md' | ForEach-Object {
        Test-Frontmatter -Path $_.FullName `
            -Required @('name','description','agent','argument-hint') `
            -AssetType 'prompt'
    }
}

if ($failures.Count -eq 0) {
    Write-Host 'OK — all customization assets have valid frontmatter.' -ForegroundColor Green
    exit 0
}

Write-Host "FAILED — $($failures.Count) issue(s):" -ForegroundColor Red
foreach ($f in $failures) { Write-Host "  - $f" -ForegroundColor Red }
exit 1
