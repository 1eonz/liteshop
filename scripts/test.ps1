param([switch]$Integration)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& python (Join-Path $root 'scripts/check_enum_sync.py')
if ($LASTEXITCODE -ne 0) { throw 'enum sync check failed' }
& pnpm --dir $root test
if ($Integration) {
    $backend = Join-Path $root 'backend'
    $env:LITESHOP_RUN_INTEGRATION = '1'
    $env:LITESHOP_USE_DATABASE = 'true'
    & pytest -q (Join-Path $backend 'integration_tests/test_postgres_redis.py')
}
