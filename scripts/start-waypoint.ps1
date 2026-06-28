# Bring up the full Waypoint stack on the ThinkPad, on demand.
#
# Run this when you want Waypoint; nothing here auto-starts on its own (containers
# use restart: "no"). It's idempotent: anything already running is left alone.
#
#   pwsh -File scripts\start-waypoint.ps1      (or right-click > Run with PowerShell)
#
# To stop everything when you're done: `docker compose stop` + `docker stop otp`,
# and close llama-swap from Task Manager (or just reboot — nothing comes back).
$ErrorActionPreference = 'Stop'
$repo    = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $repo '.env.deploy'

function Test-Docker { docker info *> $null; return ($LASTEXITCODE -eq 0) }
function Wait-Docker([int]$timeoutSec = 120) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) { if (Test-Docker) { return $true }; Start-Sleep -Seconds 3 }
    return $false
}

Write-Host '== Waypoint bring-up =='

# 1. Docker engine. Docker Desktop starts at login, but the engine takes a moment;
#    if it isn't up at all, nudge Docker Desktop, then wait for readiness.
if (-not (Test-Docker)) {
    $dd = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (Test-Path $dd) { Write-Host 'Starting Docker Desktop...'; Start-Process $dd | Out-Null }
}
if (-not (Wait-Docker)) { throw 'Docker engine did not become ready within 120s.' }
Write-Host 'Docker: ready'

# 2. OTP routing on :8090 (start the existing container, or create it from the prebuilt graph).
$otpExists = (docker ps -a --format '{{.Names}}' | Select-String -Quiet '^otp$')
if ($otpExists) {
    docker start otp | Out-Null
} else {
    docker run -d --name otp --restart no -p 8090:8080 `
        -e 'JAVA_TOOL_OPTIONS=-Xmx8g' -v 'C:\otp:/var/opentripplanner' `
        docker.io/opentripplanner/opentripplanner:2.7.0 --load --serve | Out-Null
}
Write-Host 'OTP: up on :8090'

# 3. App + Postgres on :8000 (api runs migrations on boot).
Push-Location $repo
try { docker compose --env-file $envFile up -d | Out-Null } finally { Pop-Location }
Write-Host 'App + db: up on :8000'

# 4. Analyst gateway (llama-swap) on :8080 - launch hidden if not already serving.
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host 'Analyst: already on :8080'
} else {
    $exe = (Get-Command llama-swap -ErrorAction SilentlyContinue).Source
    if (-not $exe) { $exe = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\mostlygeek.llama-swap_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-swap.exe' }
    if (-not (Test-Path $exe)) { throw "llama-swap.exe not found (PATH and $exe)" }
    $config = Join-Path $env:USERPROFILE 'llama-swap.yaml'
    $logDir = Join-Path $env:USERPROFILE '.waypoint'
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
    Start-Process -FilePath $exe -ArgumentList @('-config', $config, '-listen', '0.0.0.0:8080') `
        -RedirectStandardOutput (Join-Path $logDir 'llama-swap.out.log') `
        -RedirectStandardError  (Join-Path $logDir 'llama-swap.err.log') -WindowStyle Hidden
    Write-Host 'Analyst: launched on :8080 (loads the model on first request)'
}

# 5. Print the LAN URL for the Mac's browser.
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -notlike '*vEthernet*' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress
Write-Host ''
Write-Host "Waypoint is starting. From the Mac:  http://${ip}:8000"
Write-Host '(give the api ~20-30s to migrate + boot, then hard-refresh Safari.)'
