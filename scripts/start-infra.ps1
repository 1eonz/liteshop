param([switch]$Build)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$arguments = @('compose', '--project-directory', $root, 'up', '-d')

if ($Build) {
    $arguments += '--build'
}

& docker @arguments postgres redis
if ($LASTEXITCODE -ne 0) {
    throw "Local infrastructure failed to start, exit code: $LASTEXITCODE"
}

Write-Host 'Local PostgreSQL and Redis started.'
