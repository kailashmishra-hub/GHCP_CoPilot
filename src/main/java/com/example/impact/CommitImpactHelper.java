package com.example.impact;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Reports source files introduced by the current branch relative to master/main. */
public final class CommitImpactHelper {
    private static final Set<String> SOURCE_EXTENSIONS = new HashSet<String>(Arrays.asList(
            ".java", ".kt", ".kts", ".groovy", ".scala", ".cs",
            ".py", ".js", ".jsx", ".ts", ".tsx"));

    private CommitImpactHelper() { }

    public static void main(String[] args) throws Exception {
        String requestedBase = option(args, "--base");
        String target = valueOrDefault(option(args, "--target"), "HEAD");
        String base = requestedBase == null ? detectBase() : requestedBase;
        String mergeBase = git("merge-base", base, target).trim();
        if (mergeBase.isEmpty()) {
            throw new IllegalStateException("No merge base found between " + base + " and " + target);
        }

        List<String> diff = gitLines("diff", "--name-status", "--find-renames",
                "--diff-filter=ACMR", mergeBase, target);
        List<String> changedSources = new ArrayList<String>();
        for (String entry : diff) {
            String[] columns = entry.split("\\t");
            if (columns.length < 2) continue;
            String status = columns[0].substring(0, 1);
            String path = (status.equals("R") || status.equals("C")) && columns.length >= 3
                    ? columns[2] : columns[1];
            if (isSource(path)) changedSources.add(status + "  " + path);
        }

        Path output = Paths.get("runtime", "changed-class-files.txt");
        Files.createDirectories(output.getParent());
        List<String> report = new ArrayList<String>();
        report.add("Base: " + base);
        report.add("Target: " + target);
        report.add("Changed class files: " + changedSources.size());
        report.add("");
        report.addAll(changedSources);
        Files.write(output, report, StandardCharsets.UTF_8);

        System.out.println("Compared " + base + "..." + target);
        System.out.println("Changed class files: " + changedSources.size());
        for (String source : changedSources) System.out.println(source);
        System.out.println("Report: " + output.toAbsolutePath());
    }

    private static String detectBase() throws Exception {
        Set<String> refs = new HashSet<String>(gitLines(
                "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes"));
        for (String candidate : Arrays.asList("origin/master", "master", "origin/main", "main")) {
            if (refs.contains(candidate)) return candidate;
        }
        throw new IllegalStateException("No master/main ref found. Pass --base <ref>.");
    }

    private static boolean isSource(String path) {
        String lower = path.toLowerCase();
        for (String extension : SOURCE_EXTENSIONS) {
            if (lower.endsWith(extension)) return true;
        }
        return false;
    }

    private static String option(String[] args, String name) {
        for (int index = 0; index < args.length; index++) {
            if (name.equals(args[index])) {
                if (index + 1 >= args.length) throw new IllegalArgumentException("Missing value for " + name);
                return args[index + 1];
            }
        }
        return null;
    }

    private static String valueOrDefault(String value, String fallback) {
        return value == null || value.trim().isEmpty() ? fallback : value;
    }

    private static List<String> gitLines(String... args) throws Exception {
        String output = git(args);
        List<String> lines = new ArrayList<String>();
        for (String line : output.split("\\R")) {
            if (!line.trim().isEmpty()) lines.add(line.trim());
        }
        return lines;
    }

    private static String git(String... args) throws IOException, InterruptedException {
        List<String> command = new ArrayList<String>();
        command.add("git");
        command.add("-c");
        command.add("safe.directory=" + Paths.get("").toAbsolutePath().normalize().toString().replace('\\', '/'));
        command.addAll(Arrays.asList(args));
        Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
        StringBuilder output = new StringBuilder();
        BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) output.append(line).append(System.lineSeparator());
        int exitCode = process.waitFor();
        if (exitCode != 0) throw new IllegalStateException(output.toString().trim());
        return output.toString();
    }
}
