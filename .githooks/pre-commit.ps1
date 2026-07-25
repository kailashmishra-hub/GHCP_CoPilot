$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    $repoRoot = (Resolve-Path .).Path
}
Set-Location $repoRoot

mvn -q -DskipTests compile | Out-Null
java -cp target/classes com.example.impact.CommitImpactHelper
exit $LASTEXITCODE
