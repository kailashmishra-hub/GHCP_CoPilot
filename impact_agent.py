from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from impact_analyzer import (
    Analysis,
    Impact,
    analyze,
    default_base,
    risk_score,
    scenario_report,
    tag_report,
    validate_repo,
)


RUNTIME_DIR = "runtime"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the GHCP impact-analysis agent without Streamlit.",
    )
    parser.add_argument("--repo", default=".", help="Repository path. Defaults to current directory.")
    parser.add_argument("--base", default="", help="Base branch/ref. Defaults to Master.")
    parser.add_argument("--target", default="HEAD", help="Target branch/ref. Defaults to HEAD.")
    parser.add_argument("--committed-only", action="store_true", help="Ignore staged and unstaged changes.")
    parser.add_argument("--runtime-dir", default=RUNTIME_DIR, help="Directory for generated reports.")
    parser.add_argument("--run-tests", action="store_true", help="Run Maven for the selected impacted scenario tags.")
    return parser


def changed_file_rows(analysis: Analysis) -> list[dict[str, Any]]:
    return [
        {
            "status": item.status,
            "path": item.path,
            "changeSummary": item.change_summary,
            "codeChanges": [
                {
                    "method": change.method,
                    "changeType": change.change_type,
                    "rows": [
                        {
                            "before": row.before,
                            "after": row.after,
                            "beforeChanged": row.before_changed,
                            "afterChanged": row.after_changed,
                        }
                        for row in change.rows
                    ],
                }
                for change in item.code_changes
            ],
        }
        for item in analysis.changed_files
        if item.source
    ]


def impact_rows(impacts: list[Impact]) -> list[dict[str, Any]]:
    return [
        {
            "scenarioId": impact.scenario.key,
            "featureFile": impact.scenario.file,
            "scenario": impact.scenario.name,
            "line": impact.scenario.line,
            "tags": impact.scenario.tags,
            "impactedSteps": impact.impacted_steps,
            "changedClassFiles": impact.changed_files,
            "reasons": impact.reasons,
            "coverageUnitIds": sorted(impact.coverage_units),
            "riskScore": risk_score(impact),
        }
        for impact in impacts
    ]


def report_payload(analysis: Analysis) -> dict[str, Any]:
    return {
        "baseBranch": "Master",
        "baseRef": analysis.base_ref,
        "baseCommit": analysis.base_sha,
        "targetRef": analysis.target_ref,
        "changedClassFiles": changed_file_rows(analysis),
        "impactedScenarios": impact_rows(analysis.impacts),
        "selectedMinimalSubset": impact_rows(analysis.recommended),
        "uncoveredCoverageUnits": sorted(analysis.uncovered_units),
    }


def changed_classes_text(analysis: Analysis) -> str:
    lines: list[str] = []
    impacting_paths = {path for impact in analysis.impacts for path in impact.changed_files}
    for item in analysis.changed_files:
        if not item.source:
            continue
        marker = "TRACEABLE" if item.path in impacting_paths else "NO_SCENARIO"
        lines.append(f"[{item.status}] {item.path} [{marker}]")
        if item.change_summary:
            lines.append(item.change_summary)
        lines.append("")
    return "\n".join(lines)


def selected_tag_expression(impacts: list[Impact]) -> str:
    tags = []
    for impact in impacts:
        tags.extend(tag for tag in impact.scenario.tags if tag.startswith("@"))
    unique_tags = list(dict.fromkeys(tags))
    return " or ".join(unique_tags)


def write_reports(analysis: Analysis, runtime_dir: Path) -> dict[str, Path]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "changed_classes": runtime_dir / "changed-class-files.txt",
        "impacted_scenarios": runtime_dir / "impacted-scenarios.txt",
        "impacted_tags": runtime_dir / "impacted-tags.txt",
        "selected_subset": runtime_dir / "selected-scenarios.txt",
        "json": runtime_dir / "impact-report.json",
        "summary": runtime_dir / "impact-summary.txt",
    }

    files["changed_classes"].write_text(changed_classes_text(analysis), encoding="utf-8")
    files["impacted_scenarios"].write_text(scenario_report(analysis.impacts), encoding="utf-8")
    files["impacted_tags"].write_text(tag_report(analysis.impacts), encoding="utf-8")
    files["selected_subset"].write_text(scenario_report(analysis.recommended), encoding="utf-8")
    files["json"].write_text(json.dumps(report_payload(analysis), indent=2), encoding="utf-8")

    summary = [
        "GHCP Impact Agent Summary",
        f"Base Branch: Master ({analysis.base_ref})",
        f"Base Commit: {analysis.base_sha}",
        f"Target Ref: {analysis.target_ref}",
        f"Changed class files: {len([item for item in analysis.changed_files if item.source])}",
        f"Impacted scenarios: {len(analysis.impacts)}",
        f"Selected minimal subset: {len(analysis.recommended)}",
        f"Selected tag expression: {selected_tag_expression(analysis.recommended) or '(none)'}",
    ]
    files["summary"].write_text("\n".join(summary) + "\n", encoding="utf-8")
    return files


def run_selected_tests(repo: Path, analysis: Analysis, runtime_dir: Path) -> int:
    tag_expression = selected_tag_expression(analysis.recommended)
    output_file = runtime_dir / "test-execution.txt"
    if not tag_expression:
        output_file.write_text("No impacted scenario tags found. Maven was not run.\n", encoding="utf-8")
        return 0

    command = ["mvn", "test", f"-Dcucumber.filter.tags={tag_expression}"]
    completed = subprocess.run(
        command,
        cwd=repo,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    output_file.write_text(
        "Command: " + " ".join(command) + "\n"
        f"Exit code: {completed.returncode}\n\n"
        "STDOUT\n"
        f"{completed.stdout}\n\n"
        "STDERR\n"
        f"{completed.stderr}",
        encoding="utf-8",
    )
    return completed.returncode


def print_summary(analysis: Analysis, files: dict[str, Path]) -> None:
    print("GHCP Impact Agent")
    print(f"Base Branch: Master ({analysis.base_ref})")
    print(f"Changed class files: {len([item for item in analysis.changed_files if item.source])}")
    print(f"Impacted scenarios: {len(analysis.impacts)}")
    print(f"Selected minimal subset: {len(analysis.recommended)}")
    print()
    print("Reports written:")
    for path in files.values():
        print(f"- {path.resolve()}")
    if not analysis.impacts:
        print()
        print("No changed class files impact any feature scenarios.")


def main() -> int:
    args = build_parser().parse_args()
    try:
        repo = validate_repo(Path(args.repo))
        base_ref = args.base.strip() or default_base(repo)
        analysis = analyze(repo, base_ref, args.target, not args.committed_only)
        files = write_reports(analysis, repo / args.runtime_dir)
        test_exit = run_selected_tests(repo, analysis, repo / args.runtime_dir) if args.run_tests else 0
        print_summary(analysis, files)
        return test_exit
    except Exception as exc:
        print(f"Impact agent failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
