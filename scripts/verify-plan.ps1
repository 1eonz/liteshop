param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{1,2}$')]
    [string]$Plan,

    [ValidateSet('Auto', 'Backend', 'H5', 'Admin', 'Site', 'Shared', 'Frontend', 'E2E', 'All')]
    [string]$Target = 'Auto'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$planNumber = [int]$Plan
$planName = $planNumber.ToString('00')
$planPath = Join-Path $root ("plans\plan-{0}.md" -f $planName)

if (-not (Test-Path -LiteralPath $planPath)) {
    throw "Plan file not found: $planPath"
}

function Assert-CommandSucceeded {
    param([Parameter(Mandatory = $true)][string]$CommandName)
    if ($LASTEXITCODE -ne 0) {
        throw "$CommandName failed with exit code $LASTEXITCODE"
    }
}

function Invoke-BackendVerification {
    Push-Location (Join-Path $root 'backend')
    try {
        & python (Join-Path $root 'scripts/check_enum_sync.py')
        Assert-CommandSucceeded 'enum sync check'
        & ruff check .
        Assert-CommandSucceeded 'ruff check'
        & ruff format --check .
        Assert-CommandSucceeded 'ruff format --check'
        & python -m mypy .
        Assert-CommandSucceeded 'mypy'
        & pytest -q --cov=app --cov-report=term-missing
        Assert-CommandSucceeded 'pytest'
    }
    finally {
        Pop-Location
    }
}

function Invoke-PackageVerification {
    param([Parameter(Mandatory = $true)][string]$PackagePath)
    $absolutePath = Join-Path $root $PackagePath
    & pnpm --dir $absolutePath typecheck
    Assert-CommandSucceeded "$PackagePath typecheck"
    & pnpm --dir $absolutePath lint
    Assert-CommandSucceeded "$PackagePath lint"
    & pnpm --dir $absolutePath test
    Assert-CommandSucceeded "$PackagePath test"
    & pnpm --dir $absolutePath build
    Assert-CommandSucceeded "$PackagePath build"
}

function Invoke-SharedVerification {
    foreach ($package in @('packages/shared-types', 'packages/shared-tokens', 'packages/shared-components', 'packages/shared-3d-components')) {
        & pnpm --dir (Join-Path $root $package) build
        Assert-CommandSucceeded "$package build"
        & pnpm --dir (Join-Path $root $package) test
        Assert-CommandSucceeded "$package test"
    }
}

function Invoke-E2EVerification {
    & pnpm --dir (Join-Path $root 'tests/e2e') test
    Assert-CommandSucceeded 'Playwright E2E'
}

function Resolve-AutoTargets {
    param([Parameter(Mandatory = $true)][int]$Number)
    switch ($Number) {
        { $_ -in 1..3 } { return @('Shared') }
        { $_ -in 4..6 } { return @('Backend') }
        { $_ -in 7..9 } { return @('H5') }
        { $_ -in 10..12 } { return @('Admin') }
        13 { return @('All') }
        { $_ -in 14..15 } { return @('Backend') }
        16 { return @('Backend', 'H5') }
        17 { return @('Backend', 'Admin') }
        18 { return @('Backend', 'H5', 'Admin') }
        19 { return @('Backend', 'Admin') }
        20 { return @('Backend', 'H5') }
        21 { return @('Backend', 'H5', 'Admin') }
        22 { return @('Shared', 'H5', 'Admin') }
        23 { return @('Backend', 'H5', 'Admin') }
        24 { return @('All') }
        25 { return @('Frontend') }
        26 { return @('Backend') }
        27 { return @('Site') }
        28 { return @('Backend', 'Admin', 'Site') }
        29 { return @('Backend', 'H5', 'Admin', 'Site') }
        30 { return @('Shared', 'Site') }
        31 { return @('Backend') }
        32 { return @('Backend', 'H5', 'Admin') }
        33 { return @('H5', 'Admin') }
        34 { return @('Admin', 'Site', 'E2E') }
        35 { return @('Backend', 'Admin', 'E2E') }
        36 { return @('H5', 'E2E') }
        37 { return @('Shared', 'Frontend') }
        default { return @('All') }
    }
}

$targets = if ($Target -eq 'Auto') { Resolve-AutoTargets $planNumber } else { @($Target) }
if ($targets -contains 'All') {
    $targets = @('Backend', 'Shared', 'Frontend', 'E2E')
}
if ($targets -contains 'Frontend') {
    $targets = @($targets | Where-Object { $_ -ne 'Frontend' }) + @('H5', 'Admin', 'Site')
}
$targets = @($targets | Select-Object -Unique)

Write-Host "Verifying plan-$planName"
Write-Host "Targets: $($targets -join ', ')"

foreach ($currentTarget in $targets) {
    switch ($currentTarget) {
        'Backend' { Invoke-BackendVerification }
        'Shared' { Invoke-SharedVerification }
        'H5' { Invoke-PackageVerification 'packages/h5-app' }
        'Admin' { Invoke-PackageVerification 'packages/admin-app' }
        'Site' { Invoke-PackageVerification 'packages/site-app' }
        'E2E' { Invoke-E2EVerification }
    }
}

Write-Host "plan-$planName verification completed"
