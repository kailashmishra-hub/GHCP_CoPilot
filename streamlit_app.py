from __future__ import annotations

import json
import difflib
import html
import shutil
import subprocess
from pathlib import Path

import streamlit as st

from impact_analyzer import Analysis, NoActivePullRequest, analyze, analyze_branch_snapshot, available_refs, default_base, parse_azure_branch_url, parse_azure_pull_request_url, parse_github_pull_location, prepare_azure_branch_repository, prepare_azure_pull_repository, prepare_remote_pull_repository, risk_score, run_git, validate_repo


st.set_page_config(page_title="GitHub Impact Tracker", page_icon="🔎", layout="wide")

STATUS_NAMES = {
    "A": "Added",
    "C": "Copied",
    "D": "Deleted",
    "M": "Modified",
    "R": "Renamed",
    "U": "Unmerged",
}


def impact_rows(analysis: Analysis) -> list[dict[str, object]]:
    return [{
        "Feature": impact.scenario.file,
        "Scenario": impact.scenario.name,
        "Tags": " ".join(impact.scenario.tags) or "—",
        "Impacted steps": " | ".join(impact.impacted_steps),
        "Changed classes": " | ".join(impact.changed_files),
        "Reason": " | ".join(impact.reasons),
    } for impact in analysis.impacts]


def recommendation_rows(analysis: Analysis) -> list[dict[str, object]]:
    return [{
        "Priority": index,
        "Scenario": impact.scenario.name,
        "Feature": impact.scenario.file,
        "Tags": " ".join(impact.scenario.tags) or "—",
        "Coverage units": len(impact.coverage_units),
        "Risk score": risk_score(impact),
        "Why selected": "Covers " + ", ".join(impact.changed_files),
    } for index, impact in enumerate(analysis.recommended, 1)]


def highlighted_pair(before: str, after: str, before_changed: bool, after_changed: bool) -> tuple[str, str]:
    if not before_changed and not after_changed:
        return html.escape(before), html.escape(after)
    if not before:
        return "<span class='diff-absent'>(not present)</span>", f"<mark>{html.escape(after)}</mark>"
    if not after:
        return f"<mark>{html.escape(before)}</mark>", "<span class='diff-absent'>(removed)</span>"
    before_parts: list[str] = []
    after_parts: list[str] = []
    for operation, a1, a2, b1, b2 in difflib.SequenceMatcher(None, before, after).get_opcodes():
        before_text = html.escape(before[a1:a2])
        after_text = html.escape(after[b1:b2])
        if operation == "equal":
            before_parts.append(before_text)
            after_parts.append(after_text)
        else:
            if before_text:
                before_parts.append(f"<mark>{before_text}</mark>")
            if after_text:
                after_parts.append(f"<mark>{after_text}</mark>")
    return "".join(before_parts), "".join(after_parts)


def render_code_change_table(change) -> None:
    rows: list[str] = []
    for row in change.rows:
        before, after = highlighted_pair(row.before, row.after, row.before_changed, row.after_changed)
        changed_class = " changed-row" if row.before_changed or row.after_changed else ""
        rows.append(
            f"<tr class='{changed_class}'><td><code>{before}</code></td>"
            f"<td><code>{after}</code></td></tr>"
        )
    st.markdown(
        """
        <style>
        .code-diff { width: 100%; border-collapse: collapse; table-layout: fixed; margin: .35rem 0 1rem; }
        .code-diff th { text-align: left; padding: .55rem .7rem; border: 1px solid #d0d7de; background: #f6f8fa; }
        .code-diff td { width: 50%; vertical-align: top; padding: .4rem .7rem; border: 1px solid #d8dee4; }
        .code-diff code { white-space: pre-wrap; overflow-wrap: anywhere; color: inherit; background: transparent; }
        .code-diff mark { background: #d0d0d0; color: #111; padding: 1px 0; }
        .code-diff .diff-absent { color: #6e7781; font-style: italic; }
        </style>
        """
        f"<table class='code-diff'><thead><tr><th>Master code</th><th>Committed code</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>",
        unsafe_allow_html=True,
    )


def ai_recommendation(analysis: Analysis) -> str:
    impacting_paths = sorted({path for impact in analysis.impacts for path in impact.changed_files})
    facts = {
        "changed_files_with_feature_impact": impacting_paths,
        "changed_feature_files": [
            {"path": item.path, "status": STATUS_NAMES.get(item.status, item.status)}
            for item in analysis.changed_files if item.path.lower().endswith(".feature")
        ],
        "impacted_scenarios": impact_rows(analysis),
        "deterministic_minimal_subset": recommendation_rows(analysis),
    }
    copilot = shutil.which("copilot")
    if not copilot:
        raise RuntimeError(
            "GitHub Copilot CLI was not found. Install it, restart the terminal, and run 'copilot login'."
        )

    prompt = (
        "You are a senior test-impact analyst. Use only the supplied facts. Select the smallest "
        "defensible scenario subset that covers every changed class and impacted step, prioritizing "
        "higher regression risk when multiple equally small subsets exist. Never invent files, tags, "
        "or scenarios. Return a concise Markdown table with Priority, Feature, Scenario, Tags, and "
        "Coverage reason, followed by one sentence explaining why the subset is sufficient.\n\n"
        f"Facts:\n{json.dumps(facts, indent=2)}"
    )
    try:
        result = subprocess.run(
            [copilot, "--prompt", prompt, "--no-color", "--no-ask-user"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("GitHub Copilot did not respond within 3 minutes.") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unknown Copilot CLI error."
        raise RuntimeError(detail)
    if not result.stdout.strip():
        raise RuntimeError("GitHub Copilot returned an empty response.")
    return result.stdout.strip()


def render_analysis(analysis: Analysis) -> None:
    st.caption(
        f"Comparison: `{analysis.base_ref}` → `{analysis.target_ref}` "
        f"(base commit `{analysis.base_sha[:10]}`)"
    )
    impacting_paths = {path for impact in analysis.impacts for path in impact.changed_files}
    impacting_classes = [
        item for item in analysis.changed_files
        if item.source and item.path in impacting_paths
    ]
    changed_features = [
        item for item in analysis.changed_files if item.path.lower().endswith(".feature")
    ]
    metrics = st.columns(3)
    metrics[0].metric("Impacting class files", len(impacting_classes))
    metrics[1].metric("Changed feature files", len(changed_features))
    metrics[2].metric("Impacted scenarios", len(analysis.impacts))

    st.subheader("1. Changed class files with feature impact")
    if impacting_classes:
        for item in impacting_classes:
            with st.expander(f"{STATUS_NAMES.get(item.status, item.status)} · {item.path}", expanded=True):
                for change in item.code_changes:
                    st.markdown(f"**Method/Function:** `{change.method}`")
                    st.markdown(f"**Change Type:** {change.change_type}")
                    render_code_change_table(change)
    else:
        st.info("No changed class files could be traced to any feature scenario.")

    st.subheader("2. Changed feature files")
    if changed_features:
        for item in changed_features:
            with st.expander(f"{STATUS_NAMES.get(item.status, item.status)} · {item.path}", expanded=True):
                for change in item.code_changes:
                    st.markdown(f"**Scenario/Context:** `{change.method}`")
                    st.markdown(f"**Change Type:** {change.change_type}")
                    render_code_change_table(change)
                related = [impact for impact in analysis.impacts if item.path in impact.changed_files]
                if related:
                    st.markdown("**Affected scenarios and tags:**")
                    for impact in related:
                        tags = " ".join(impact.scenario.tags) or "No tags"
                        st.markdown(f"- `{impact.scenario.name}` — {tags}")
    else:
        st.info("No feature files changed between the selected branches.")

def main() -> None:
    st.title("GitHub Impacted Scenarios Tracker")
    st.write("Compare a working branch with master/main, trace source changes into Cucumber scenarios, and choose a compact regression set.")

    with st.sidebar:
        st.header("Repository")
        source_mode = st.radio(
            "Choose analysis source",
            [
                "Local repository",
                "GitHub PR link",
                "Azure DevOps PR link",
                "Azure DevOps branch link",
            ],
        )
        repo_path: Path | None = None
        detected_base = "origin/main"
        base_options = ["origin/main", "origin/master", "main", "master"]
        current_branch = "Not detected"
        target_options = ["HEAD (current branch)"]
        custom_base = ""
        pull_request_link = ""
        azure_pat = ""
        azure_base = "PR target branch (automatic)"
        if source_mode == "Local repository":
            selected_repo_path = st.text_input(
                "Local Git repository path",
                placeholder="C:\\path\\to\\your\\automation-project",
                help="Paste the IntelliJ project root containing the .git folder.",
            )
            if selected_repo_path:
                try:
                    repo_path = validate_repo(Path(selected_repo_path.strip().strip('"')))
                    detected_base = default_base(repo_path)
                    refs = set(available_refs(repo_path))
                    base_options = [
                        ref for ref in ("origin/main", "origin/master", "main", "master")
                        if ref in refs
                    ] or [detected_base]
                    current_branch = run_git(
                        repo_path, "branch", "--show-current", check=False
                    ).strip() or "Detached HEAD"
                    target_options = ["HEAD (current branch)"] + sorted(
                        ref for ref in refs
                        if ref not in {"origin/HEAD", "HEAD"}
                    )
                except Exception as exc:
                    st.error(str(exc))
            selected_base = st.selectbox(
                "Base branch",
                base_options,
                index=base_options.index(detected_base) if detected_base in base_options else 0,
                help="The current branch will be compared with this branch.",
            )
            selected_target = st.selectbox(
                "Target branch",
                target_options,
                help=(
                    "Choose HEAD for the branch currently open in IntelliJ, or select another fetched "
                    "branch. Other branches are analyzed in a temporary worktree without switching IntelliJ."
                ),
            )
            st.caption(f"Currently checked out: `{current_branch}`")
            custom_base = st.text_input(
                "Custom base ref/commit (optional)",
                help="Leave empty to use the selected base branch, or enter another branch, tag, SHA, or commit.",
            )
        elif source_mode == "GitHub PR link":
            pull_request_link = st.text_input(
                "GitHub pull request link",
                placeholder="https://github.com/owner/repository/pull/1",
                help="You can also enter the repository pull-request list URL ending in /pulls.",
            )
            st.text_input("Base branch", value="origin/main", disabled=True, key="pr_base_branch")
        elif source_mode == "Azure DevOps PR link":
            pull_request_link = st.text_input(
                "Azure DevOps pull request link",
                placeholder="https://dev.azure.com/org/project/_git/repository/pullrequest/123",
            )
            azure_base = st.selectbox(
                "Base branch",
                [
                    "PR target branch (automatic)",
                    "origin/main",
                    "origin/master",
                    "main",
                    "master",
                ],
                help="Automatic uses the target branch configured on the Azure DevOps pull request.",
            )
            azure_pat = st.text_input(
                "Azure DevOps PAT (optional for public repositories)",
                type="password",
                help="For private repositories, use a PAT with Code (Read) permission. It is not stored.",
            )
        else:
            pull_request_link = st.text_input(
                "Azure DevOps repository/branch link",
                placeholder=(
                    "https://dev.azure.com/org/project/_git/repository?version=GBfeature-branch"
                ),
                help="The branch is read from the version=GB... part of the URL.",
            )
            st.text_input("Base branch", value="origin/master", disabled=True, key="azure_branch_base")
            azure_pat = st.text_input(
                "Azure DevOps PAT (optional for public repositories)",
                type="password",
                key="azure_branch_pat",
                help="For private repositories, use a PAT with Code (Read) permission. It is not stored.",
            )
        analyze_clicked = st.button("Analyze impact", type="primary", use_container_width=True)

        st.divider()
        st.header("GitHub Copilot")
        if shutil.which("copilot"):
            st.success("Copilot CLI detected")
        else:
            st.warning("Copilot CLI is not installed or is not on PATH.")
            st.caption("Install it locally, restart the terminal, then run: copilot login")

    if analyze_clicked:
        try:
            with st.spinner("Comparing Git changes and tracing Cucumber coverage..."):
                if source_mode == "GitHub PR link":
                    if not parse_github_pull_location(pull_request_link):
                        st.error("Enter a valid GitHub PR link ending in /pull/NUMBER or /pulls.")
                        return
                    analysis_repo, pull_number, base_ref = prepare_remote_pull_repository(pull_request_link)
                    target_ref = "HEAD"
                    st.session_state.pr_number = pull_number
                    st.session_state.pr_provider = "GitHub"
                elif source_mode == "Azure DevOps PR link":
                    if not parse_azure_pull_request_url(pull_request_link):
                        st.error("Enter a valid Azure DevOps pull request link ending in /pullrequest/NUMBER.")
                        return
                    analysis_repo, pull_number, pr_base_ref = prepare_azure_pull_repository(
                        pull_request_link, azure_pat.strip()
                    )
                    base_ref = (
                        pr_base_ref
                        if azure_base == "PR target branch (automatic)"
                        else azure_base
                    )
                    target_ref = "HEAD"
                    st.session_state.pr_number = pull_number
                    st.session_state.pr_provider = "Azure DevOps"
                elif source_mode == "Azure DevOps branch link":
                    if not parse_azure_branch_url(pull_request_link):
                        st.error(
                            "Enter a valid Azure DevOps repository link containing ?version=GBbranch-name."
                        )
                        return
                    analysis_repo, target_ref, base_ref = prepare_azure_branch_repository(
                        pull_request_link, azure_pat.strip()
                    )
                    st.session_state.pop("pr_number", None)
                    st.session_state.pop("pr_provider", None)
                else:
                    if repo_path is None:
                        st.error("Select a local Git repository before running impact analysis.")
                        return
                    analysis_repo = repo_path
                    base_ref = custom_base.strip() or selected_base
                    target_ref = "HEAD" if selected_target == "HEAD (current branch)" else selected_target
                    st.session_state.pop("pr_number", None)
                    st.session_state.pop("pr_provider", None)
                st.session_state.analysis = (
                    analyze_branch_snapshot(analysis_repo, base_ref, target_ref)
                    if source_mode == "Local repository"
                    else analyze(analysis_repo, base_ref, target_ref, False)
                )
                st.session_state.analysis_source_mode = source_mode
                st.session_state.pop("ai_review", None)
        except NoActivePullRequest as exc:
            st.session_state.pop("analysis", None)
            st.session_state.pop("ai_review", None)
            st.session_state.pop("pr_number", None)
            st.session_state.pop("pr_provider", None)
            st.info(str(exc))
            return
        except Exception as exc:
            st.error(str(exc))
            return

    analysis = (
        st.session_state.get("analysis")
        if st.session_state.get("analysis_source_mode") == source_mode
        else None
    )
    if not analysis:
        st.info("Choose a repository and select **Analyze impact**.")
        return
    if st.session_state.get("pr_number"):
        provider = st.session_state.get("pr_provider", "GitHub")
        st.success(f"Analyzing {provider} pull request #{st.session_state.pr_number} against its target branch.")
    render_analysis(analysis)

    st.subheader("3. GitHub Copilot recommended regression subset")
    st.caption("GitHub Copilot reviews only the traceable impacted scenarios and chooses the smallest risk-aware subset that covers the changed class behavior.")
    if not analysis.impacts:
        st.info("There are no impacted scenarios for AI to optimize.")
        return
    if st.button("Generate smallest subset with GitHub Copilot", type="primary"):
        try:
            with st.spinner("GitHub Copilot is selecting the smallest risk-aware regression subset..."):
                st.session_state.ai_review = ai_recommendation(analysis)
        except Exception as exc:
            st.error(f"GitHub Copilot generation failed: {exc}")
    if st.session_state.get("ai_review"):
        st.markdown(st.session_state.ai_review)


if __name__ == "__main__":
    main()
