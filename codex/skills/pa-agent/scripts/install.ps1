[CmdletBinding()]
param(
    [string]$CodexHome = $(if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }),
    [string]$ProjectRoot,
    [switch]$PersistProjectRoot
)

$ErrorActionPreference = "Stop"
$Source = Split-Path -Parent $PSScriptRoot
$Destination = Join-Path $CodexHome "skills\pa-agent"

if (-not (Test-Path -LiteralPath (Join-Path $Source "SKILL.md") -PathType Leaf)) {
    throw "找不到 PA Agent 技能源文件：$Source"
}

if (Test-Path -LiteralPath $Destination) {
    $Backup = "$Destination.backup-$(Get-Date -Format 'yyyyMMddHHmmss')"
    Move-Item -LiteralPath $Destination -Destination $Backup
}

New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force

if ($PersistProjectRoot) {
    if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
        throw "-PersistProjectRoot 需要同时提供 -ProjectRoot。"
    }
    $ResolvedProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
    [Environment]::SetEnvironmentVariable("PA_AGENT_HOME", $ResolvedProjectRoot, "User")
}

[pscustomobject]@{
    status = "installed"
    destination = $Destination
    project_root_persisted = [bool]$PersistProjectRoot
} | ConvertTo-Json -Compress
