# impact-tracker.agent.md

name: impact-tracker
description: Detects impacted scenarios in feature files when any class file changes, and extracts their tags.
prompts:
  - impactcheck:
      usage:
        - Run `git diff --name-only HEAD~1 HEAD` to detect changed files
        - Ignore non-source files (e.g., .idea/, .github/, config files)
        - For each changed source file:
            - If it contains @Given/@When/@Then annotations:
                - Extract only the changed step texts
                - Match against feature files
                - Report impacted scenarios (only the impacted steps)
            - If it contains Selenium locators or page methods:
                - Find step definition files that reference this class
                - Extract only the impacted annotations
                - Match against feature files
                - Report impacted scenarios (only the impacted steps)
        - After identifying all impacted scenarios, extract tags:
            - For each impacted scenario, open its feature file
            - Collect any tags (lines starting with @) directly above the scenario definition
            - Format tags with proper indentation
        - Write two separate formatted outputs:
            - Write impacted scenarios (Feature > Scenario > Step) to runtime/impacted-scenarios.txt
            - Write impacted tags (Feature > Scenario > Tag) to runtime/impacted-tags.txt
response_format:
  - "Feature: <feature file>"
  - "  Scenario: <scenario name>"
  - "    Step: <step text>"
  - "    Tag: <tagname>"
output_style: multiline
output_file: runtime/impacted-scenarios.txt + runtime/impacted-tags.txt
