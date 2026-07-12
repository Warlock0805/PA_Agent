$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$errors = [System.Collections.Generic.List[string]]::new()

function Add-HarnessError([string]$Message) {
    $errors.Add($Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
}

function Require-File([string]$Path) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $Path) -PathType Leaf)) {
        Add-HarnessError "缺少 Harness 文件 '$Path'。请创建该文件或修正入口引用。"
    }
}

$requiredFiles = @(
    "AGENTS.md",
    "docs/HARNESS.md",
    "docs/WORKFLOW.md",
    "docs/TESTING.md",
    "docs/harness/evals.jsonl",
    ".github/ISSUE_TEMPLATE/agent-task.yml",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    ".githooks/pre-commit",
    "tools/setup_git_secrets.ps1"
)
$requiredFiles | ForEach-Object { Require-File $_ }

foreach ($doc in @("AGENTS.md", "CONTRIBUTING.md", "docs/HARNESS.md", "docs/WORKFLOW.md", "docs/TESTING.md", ".github/pull_request_template.md")) {
    $docPath = Join-Path $Root $doc
    if (-not (Test-Path -LiteralPath $docPath)) { continue }
    $docText = Get-Content -LiteralPath $docPath -Raw -Encoding UTF8
    foreach ($match in [regex]::Matches($docText, '\[[^\]]+\]\(([^)]+)\)')) {
        $target = $match.Groups[1].Value.Trim()
        if ($target -match '^(https?://|mailto:|#)') { continue }
        $targetPath = ($target -split '#', 2)[0]
        if ([string]::IsNullOrWhiteSpace($targetPath)) { continue }
        $resolved = Join-Path (Split-Path -Parent $docPath) $targetPath
        if (-not (Test-Path -LiteralPath $resolved)) {
            Add-HarnessError "'$doc' 包含失效本地链接 '$target'。请修正目标或移除链接。"
        }
    }
}

$agentPath = Join-Path $Root "AGENTS.md"
if (Test-Path -LiteralPath $agentPath) {
    $agentText = Get-Content -LiteralPath $agentPath -Raw -Encoding UTF8
    foreach ($reference in @("docs/WORKFLOW.md", "docs/TESTING.md", "docs/HARNESS.md")) {
        if (-not $agentText.Contains($reference)) {
            Add-HarnessError "AGENTS.md 未链接 '$reference'。请把详细规则保留在权威文档并从入口导航。"
        }
    }
}

$canonicalTest = '.\.venv\Scripts\python.exe -m pytest -m "not live and not e2e" -q'
foreach ($doc in @("AGENTS.md", "docs/TESTING.md", "CONTRIBUTING.md")) {
    $path = Join-Path $Root $doc
    if ((Test-Path -LiteralPath $path) -and -not (Get-Content -LiteralPath $path -Raw -Encoding UTF8).Contains($canonicalTest)) {
        Add-HarnessError "'$doc' 缺少统一离线回归命令：$canonicalTest"
    }
}

$evalPath = Join-Path $Root "docs/harness/evals.jsonl"
if (Test-Path -LiteralPath $evalPath) {
    $lineNumber = 0
    $evalIds = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($line in Get-Content -LiteralPath $evalPath -Encoding UTF8) {
        $lineNumber++
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $case = $line | ConvertFrom-Json -ErrorAction Stop
        } catch {
            Add-HarnessError "evals.jsonl 第 $lineNumber 行不是有效 JSON：$($_.Exception.Message)"
            continue
        }
        foreach ($field in @("id", "category", "prompt", "expected_guides", "allowed_actions", "forbidden_actions", "required_evidence")) {
            if ($null -eq $case.$field -or ($case.$field -is [string] -and [string]::IsNullOrWhiteSpace($case.$field))) {
                Add-HarnessError "evals.jsonl 第 $lineNumber 行缺少字段 '$field'。"
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($case.id) -and -not $evalIds.Add([string]$case.id)) {
            Add-HarnessError "evals.jsonl 第 $lineNumber 行使用了重复 id '$($case.id)'。"
        }
        foreach ($field in @("expected_guides", "allowed_actions", "forbidden_actions", "required_evidence")) {
            if (@($case.$field).Count -eq 0) {
                Add-HarnessError "evals.jsonl 第 $lineNumber 行数组字段 '$field' 不能为空。"
            }
        }
        foreach ($guide in @($case.expected_guides)) {
            if (-not (Test-Path -LiteralPath (Join-Path $Root $guide) -PathType Leaf)) {
                Add-HarnessError "evals.jsonl 第 $lineNumber 行引用的指南不存在：'$guide'。"
            }
        }
    }
}

$issueTemplatePath = Join-Path $Root ".github/ISSUE_TEMPLATE/agent-task.yml"
if (Test-Path -LiteralPath $issueTemplatePath) {
    $issueText = Get-Content -LiteralPath $issueTemplatePath -Raw -Encoding UTF8
    foreach ($id in @("goal", "non_goals", "allowed", "forbidden", "acceptance", "verification", "authority", "risks")) {
        if (-not $issueText.Contains("id: $id")) {
            Add-HarnessError "智能体任务模板缺少字段 id '$id'。"
        }
    }
}

$prTemplatePath = Join-Path $Root ".github/pull_request_template.md"
if (Test-Path -LiteralPath $prTemplatePath) {
    $prText = Get-Content -LiteralPath $prTemplatePath -Raw -Encoding UTF8
    foreach ($heading in @("## 范围", "## RED / GREEN 证据", "## 验证分层", "## 风险与未验证内容")) {
        if (-not $prText.Contains($heading)) {
            Add-HarnessError "PR 模板缺少审查章节 '$heading'。"
        }
    }
}

$ignoreChecks = @(
    "config/settings.json",
    "config/exception_state.json",
    "logs/pa_agent.log",
    "records/pending/harness-check.json",
    "experience/harness-check.json",
    "trade_records/harness-check.csv"
)
foreach ($path in $ignoreChecks) {
    & git check-ignore -q -- $path
    if ($LASTEXITCODE -ne 0) {
        Add-HarnessError "敏感或运行时路径 '$path' 未被 .gitignore 忽略。"
    }
}

$trackedForbidden = & git ls-files -- `
    "config/settings.json" `
    "config/settings.local.json" `
    "config/exception_state.json" `
    "logs/*" `
    "records/pending/*" `
    "experience/*" `
    "trade_records/*"
foreach ($path in $trackedForbidden) {
    if ($path -notmatch '\.gitkeep$') {
        Add-HarnessError "禁止提交的运行时或敏感文件已被 Git 跟踪：'$path'。"
    }
}

$ciPath = Join-Path $Root ".github/workflows/ci.yml"
if (Test-Path -LiteralPath $ciPath) {
    $ciText = Get-Content -LiteralPath $ciPath -Raw -Encoding UTF8
    if (-not $ciText.Contains("tools\check_project_harness.ps1")) {
        Add-HarnessError "CI 未调用 tools\check_project_harness.ps1，本地与合并门禁会发生漂移。"
    }
}

if ($errors.Count -gt 0) {
    Write-Host "Harness 检查失败：$($errors.Count) 项。" -ForegroundColor Red
    exit 1
}

Write-Host "Harness 检查通过：入口、命令、eval、忽略规则和 CI 接线一致。" -ForegroundColor Green
exit 0
