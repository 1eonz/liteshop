$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& pnpm --dir $root install
