param([Parameter(Mandatory = $true)][string]$Plan)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$planPath = Join-Path $root ("plans\plan-{0}.md" -f $Plan)
if (-not (Test-Path -LiteralPath $planPath)) { throw "Plan not found: $planPath" }
Write-Host "Plan file exists: $planPath"
& pnpm --dir $root typecheck
