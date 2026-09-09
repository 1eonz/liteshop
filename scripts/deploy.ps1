param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('staging', 'production')]
    [string]$Env
)

$ErrorActionPreference = 'Stop'

# 生产发布需要目标主机、镜像仓库、密钥和回滚版本，禁止误用本地 Compose 代替。
throw "Deployment target '$Env' is not configured. Configure images, secrets, backups, and rollback first. Use scripts/start-infra.ps1 for local dependencies."
