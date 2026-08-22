GHCP - Cucumber BDD Automation Framework (sample)

Automatic pre-push impact analysis
----------------------------------
This repository includes a tracked Git pre-push hook and a GitHub Copilot custom
agent. Enable the hook once in each clone:

    git config core.hooksPath .githooks

After that, every `git push` refreshes the default remote branch, compares the
current branch with its merge base, writes `runtime/changed-class-files.txt`, and
invokes the `impact-tracker` agent. The agent writes:

- `runtime/impacted-scenarios.txt`
- `runtime/impacted-tags.txt`

Prerequisites are Git, JDK (`javac` and `java`), and an installed and authenticated
GitHub Copilot CLI (`copilot`). If analysis fails, the push is cancelled.

Purpose
-------
This repository (GHCP) contains a minimal Java project with a small sample application and unit test. The repository name and layout suggest it is intended as a Cucumber BDD automation framework, but the current source contains only a basic Maven Java app (org.example.App) and a JUnit 3 style test (AppTest).

Prerequisites
-------------
- Java JDK 8+ installed and JAVA_HOME set
- Maven 3.x installed and on your PATH

Build and test
--------------
From the repository root (where pom.xml is located):

- Build: mvn clean package
- Run unit tests: mvn test
- Run the application jar (after build): java -cp target/GHCP-1.0-SNAPSHOT.jar org.example.App

Cucumber tests (notes)
----------------------
This project currently has no Cucumber dependencies or .feature files. To add and run Cucumber tests:

1. Add Cucumber dependencies to pom.xml (cucumber-java, cucumber-junit or cucumber-junit-platform-engine for JUnit 5).
2. Add a test runner class annotated for Cucumber (or use the JUnit platform).
3. Place .feature files under src/test/resources/features and step definitions under src/test/java.
4. Run with: mvn test or using a specific Cucumber CLI option, e.g.:
   mvn test -Dcucumber.options="--tags @smoke"

Typical usage
-------------
- Developers will add step definitions under src/test/java and feature files under src/test/resources/features.
- Use Maven to build and execute tests. If you add the Cucumber dependencies, you can run BDD scenarios with the test runner.

Notes and assumptions
---------------------
- The current pom.xml only declares JUnit 3.8.1 as a test dependency; no Cucumber dependencies were found.
- No .feature files are present in the repository.
- Documentation under docs/ describes the existing package org.example and its classes.

Files created by doc-writer
--------------------------
- README.md (this file)
- docs/index.md
- docs/org.example.md
- docs/org.example.App.md

If you want me to add Cucumber support (pom changes, example feature + step defs, and a test runner), tell me and I can create a minimal working example.
