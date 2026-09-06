$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root '.env.development'
if (-not (Test-Path -LiteralPath $target)) {
  Copy-Item -LiteralPath (Join-Path $root '.env.example') -Destination $target
  Write-Host "Created $target"
} else {
  Write-Host "$target already exists; leaving it unchanged."
}
