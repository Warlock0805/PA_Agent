[CmdletBinding()]
param(
    [string]$ProjectRoot = $env:PA_AGENT_HOME
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    throw "请传入 -ProjectRoot，或设置 PA_AGENT_HOME。"
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$PyProject = Join-Path $ProjectRoot "pyproject.toml"
$Entrypoint = Join-Path $ProjectRoot "pa_agent\main.py"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

foreach ($Path in @($PyProject, $Entrypoint, $Python)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "PA Agent 启动条件不完整：$Path"
    }
}

$Existing = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object {
        $_.CommandLine -and $_.CommandLine.Contains("-m pa_agent.main") -and
        $_.CommandLine.Contains($ProjectRoot)
    } |
    Select-Object -First 1

if ($Existing) {
    [pscustomobject]@{
        status = "already_running"
        project_root = $ProjectRoot
        process_id = $Existing.ProcessId
    } | ConvertTo-Json -Compress
    exit 0
}

$Process = Start-Process -FilePath $Python -ArgumentList "-m", "pa_agent.main" `
    -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru

[pscustomobject]@{
    status = "started"
    project_root = $ProjectRoot
    process_id = $Process.Id
} | ConvertTo-Json -Compress
