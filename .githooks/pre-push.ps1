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

Write-Host "[pre-push] Detecting changed class files against $baseBranch..."
New-Item -ItemType Directory -Force runtime/hook-classes | Out-Null
javac -d runtime/hook-classes src/main/java/com/example/impact/CommitImpactHelper.java
if ($LASTEXITCODE -ne 0) { throw "Unable to compile CommitImpactHelper. Push cancelled." }
java -cp runtime/hook-classes com.example.impact.CommitImpactHelper --base $baseBranch
if ($LASTEXITCODE -ne 0) { throw "Changed-class analysis failed. Push cancelled." }

if (-not (Get-Command copilot -ErrorAction SilentlyContinue)) {
    throw "GitHub Copilot CLI is not installed or is not on PATH. Push cancelled."
}

Write-Host "[pre-push] Invoking the impact-tracker Copilot agent..."
copilot --agent=impact-tracker --prompt "Read runtime/changed-class-files.txt, calculate impacted Cucumber scenarios and tags, write the two runtime reports, and print a concise read-only summary."
if ($LASTEXITCODE -ne 0) { throw "The impact-tracker agent failed. Push cancelled." }

Write-Host "[pre-push] Impact analysis completed. Continuing push."
