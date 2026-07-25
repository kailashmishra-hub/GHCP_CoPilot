package com.example.impact;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public class CommitImpactHelper {
    public static void main(String[] args) throws Exception {
        List<String> changedFiles = getStagedFiles();
        if (changedFiles.isEmpty()) {
            return;
        }

        boolean onlyMainJavaFiles = changedFiles.stream()
                .allMatch(path -> path.startsWith("src/main/java/") && path.endsWith(".java"));

        boolean hasFeatureOrStepChanges = changedFiles.stream().anyMatch(path ->
                path.startsWith("src/test/resources/features/")
                        || path.startsWith("src/test/java/")
                        || path.endsWith(".feature")
                        || path.endsWith("Steps.java")
                        || path.endsWith("Hooks.java"));

        if (onlyMainJavaFiles && !hasFeatureOrStepChanges) {
            System.out.println("⚠️ Java class changes detected in src/main/java. Run the impact-tracker agent to inspect impacted Cucumber scenarios.");
        }
    }

    private static List<String> getStagedFiles() throws IOException, InterruptedException {
        Process process = new ProcessBuilder("git", "diff", "--cached", "--name-only", "--diff-filter=ACMR")
                .redirectErrorStream(true)
                .start();

        List<String> changedFiles = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (!line.trim().isEmpty()) {
                    changedFiles.add(line.trim());
                }
            }
        }

        int exitCode = process.waitFor();
        if (exitCode != 0) {
            throw new IOException("Unable to inspect staged files.");
        }
        return changedFiles;
    }
}
