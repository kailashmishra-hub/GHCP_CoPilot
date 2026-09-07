import tempfile
import unittest
import subprocess
from pathlib import Path

from unittest.mock import patch

from impact_analyzer import (
    ChangedFile, Impact, Scenario, StepDefinition, analyze_branch_snapshot, cucumber_pattern, default_base,
    discover_scenarios, impacted_definitions, minimal_subset, parse_github_pull_location,
    parse_azure_branch_url, parse_azure_pull_request_url, parse_pull_request_url,
)


class ImpactAnalyzerTests(unittest.TestCase):
    def test_cucumber_string_and_int_expressions(self):
        self.assertTrue(cucumber_pattern("I search for {string}").fullmatch('I search for "Laptop"'))
        self.assertTrue(cucumber_pattern("I enter {string} and {string}").fullmatch('I enter "user" and "password"'))
        self.assertTrue(cucumber_pattern("I have {int} items").fullmatch("I have 12 items"))
        self.assertFalse(cucumber_pattern("I have {int} items").fullmatch("I have many items"))

    def test_parses_scenario_local_tags(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            feature = repo / "src/test/resources/cart.feature"
            feature.parent.mkdir(parents=True)
            feature.write_text("""@feature_tag
Feature: Cart
  @smoke @cart
  Scenario: Add
    Given I have 1 items
""", encoding="utf-8")
            scenarios = discover_scenarios(repo)
            self.assertEqual(scenarios[0].tags, ["@smoke", "@cart"])

    def test_minimal_subset_covers_all_units(self):
        first = Impact(Scenario("a.feature", "Broad", 1), [], [], [], {"A", "B"})
        second = Impact(Scenario("a.feature", "Narrow", 5), [], [], [], {"A"})
        third = Impact(Scenario("b.feature", "Other", 1), [], [], [], {"C"})
        selected, uncovered = minimal_subset([first, second, third])
        self.assertEqual([item.scenario.name for item in selected], ["Broad", "Other"])
        self.assertFalse(uncovered)

    def test_changed_page_object_impacts_referencing_step(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            step_file = repo / "src/test/java/LoginSteps.java"
            step_file.parent.mkdir(parents=True)
            step_file.write_text("class LoginSteps { LoginPage loginPage; }", encoding="utf-8")
            definition = StepDefinition(
                "src/test/java/LoginSteps.java", "I sign in", 1, 1,
                '@When("I sign in") void signIn() { loginPage.signIn(); }',
            )
            with patch("impact_analyzer.changed_line_numbers", return_value={1}):
                links = impacted_definitions(
                    repo, [ChangedFile("M", "src/main/java/LoginPage.java", True)],
                    [definition], "base", "HEAD", True,
                )
            self.assertIn(definition, links)
            self.assertIn("src/main/java/LoginPage.java", links[definition])

    def test_local_head_includes_later_uncommitted_class_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)

            def git(*args: str) -> None:
                subprocess.run(
                    ["git", *args], cwd=repo, check=True,
                    capture_output=True, text=True, encoding="utf-8",
                )

            git("init", "-b", "master")
            git("config", "user.email", "impact-tracker@example.test")
            git("config", "user.name", "Impact Tracker Test")
            page = repo / "src/test/java/pages/LoginPage.java"
            steps = repo / "src/test/java/steps/LoginSteps.java"
            feature = repo / "src/test/resources/features/login.feature"
            page.parent.mkdir(parents=True)
            steps.parent.mkdir(parents=True)
            feature.parent.mkdir(parents=True)
            page.write_text("class LoginPage { void login() { int version = 1; } }\n", encoding="utf-8")
            steps.write_text(
                'class LoginSteps { LoginPage page; @When("I log in") void login() { page.login(); } }\n',
                encoding="utf-8",
            )
            feature.write_text("Feature: Login\n  Scenario: User login\n    When I log in\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "base")
            git("switch", "-c", "work")
            page.write_text("class LoginPage { void login() { int version = 2; } }\n", encoding="utf-8")
            git("add", str(page.relative_to(repo)))
            git("commit", "-m", "first change")
            page.write_text("class LoginPage { void login() { int version = 3; } }\n", encoding="utf-8")

            analysis = analyze_branch_snapshot(repo, "master", "HEAD")
            page_change = next(item for item in analysis.changed_files if item.path.endswith("LoginPage.java"))
            rendered_after = "\n".join(row.after for change in page_change.code_changes for row in change.rows)
            self.assertIn("version = 3", rendered_after)
            self.assertEqual([impact.scenario.name for impact in analysis.impacts], ["User login"])

    def test_parses_github_pull_request_url(self):
        self.assertEqual(
            parse_pull_request_url("https://github.com/kailashmishra-hub/GHCP/pull/1"),
            ("kailashmishra-hub", "GHCP", 1),
        )
        self.assertIsNone(parse_pull_request_url("https://github.com/kailashmishra-hub/GHCP/pulls"))
        self.assertEqual(
            parse_github_pull_location("https://github.com/kailashmishra-hub/GHCP/pulls"),
            ("kailashmishra-hub", "GHCP", None),
        )

    def test_parses_azure_pull_request_url(self):
        self.assertEqual(
            parse_azure_pull_request_url(
                "https://dev.azure.com/example-org/Automation/_git/UI-Tests/pullrequest/42"
            ),
            ("example-org", "Automation", "UI-Tests", 42),
        )
        self.assertEqual(
            parse_azure_pull_request_url(
                "https://example-org.visualstudio.com/Automation/_git/UI-Tests/pullrequest/42"
            ),
            ("example-org", "Automation", "UI-Tests", 42),
        )
        self.assertIsNone(parse_azure_pull_request_url("https://dev.azure.com/example-org/Automation"))

    def test_detects_main_then_master_base(self):
        with patch("impact_analyzer.available_refs", return_value=["origin/main", "origin/master"]):
            self.assertEqual(default_base(Path(".")), "origin/main")
        with patch("impact_analyzer.available_refs", return_value=["origin/master"]):
            self.assertEqual(default_base(Path(".")), "origin/master")

    def test_parses_azure_branch_url(self):
        self.assertEqual(
            parse_azure_branch_url(
                "https://dev.azure.com/bob/bob1/_git/P111_BWKYCOAUTOMATION"
                "?version=GB04.44_SampleY"
            ),
            ("bob", "bob1", "P111_BWKYCOAUTOMATION", "04.44_SampleY"),
        )
        self.assertIsNone(
            parse_azure_branch_url(
                "https://dev.azure.com/bob/bob1/_git/P111_BWKYCOAUTOMATION"
            )
        )


if __name__ == "__main__":
    unittest.main()
