$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& docker compose --project-directory $root up -d --build
