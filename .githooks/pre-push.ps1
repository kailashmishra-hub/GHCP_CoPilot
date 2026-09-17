$ErrorActionPreference = "Stop"

$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) { throw "The pre-push hook must run inside a Git repository." }
Set-Location $repoRoot

Write-Host "[pre-push] Refreshing the master/main remote reference..."
$remoteHead = git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>$null
$baseBranch = if ($remoteHead) { $remoteHead } elseif (git show-ref --verify --quiet refs/remotes/origin/master) { "origin/master" } else { "origin/main" }
$baseName = $baseBranch -replace '^origin/', ''
git fetch origin $baseName --quiet
if ($LASTEXITCODE -ne 0) { throw "Unable to refresh origin/$baseName. Push cancelled." }

Write-Host "[pre-push] Running local GHCP impact agent against $baseBranch..."
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCommand) {
    throw "Python is not installed or is not on PATH. Push cancelled."
}

& $pythonCommand.Source impact_agent.py --base $baseBranch
if ($LASTEXITCODE -ne 0) { throw "The local impact agent failed. Push cancelled." }

Write-Host "[pre-push] Impact analysis completed. Continuing push."
