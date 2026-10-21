<?php

/*
 * Builds laravel/tests/.pest/shards.json from the JUnit files the pest
 * shards write, in the format `pest --update-shards` produces. Pest reads
 * it to balance --shard by recorded time instead of by file count.
 *
 * `--update-shards` needs a whole unsharded run, which is the long run
 * sharding exists to avoid, so the timings come from the shards instead:
 * each JUnit <testsuite> with a file attribute is one test file, named by
 * class exactly as Pest keys its timings.
 *
 * Writes the new file to stdout, and to stderr how it differs from the
 * committed one (test files added or removed since it was last refreshed).
 *
 *   php ../tools/ci/build-shard-timings.php coverage/junit-*.xml > shards.json
 */

declare(strict_types=1);

$files = array_slice($argv, 1);

if ($files === []) {
    fwrite(STDERR, "usage: build-shard-timings.php <junit.xml>...\n");
    exit(2);
}

$timings = [];

// Read with a pattern, not an XML parser: PHPUnit writes dataset values
// into testcase names unfiltered, and a printing test's datasets hold raw
// control bytes (ESC), which make the file invalid XML. The <testsuite>
// elements carrying a file attribute, the only ones needed, are unaffected.
foreach ($files as $file) {
    $junit = file_get_contents($file);

    if ($junit === false || preg_match_all(
        '/<testsuite name="([^"]+)" file="[^"]*"[^>]*\btime="([0-9.]+)"/',
        $junit,
        $suites,
        PREG_SET_ORDER,
    ) === 0) {
        fwrite(STDERR, "{$file} has no per-file <testsuite> timings\n");
        exit(2);
    }

    foreach ($suites as [, $class, $time]) {
        $timings[$class] = round(($timings[$class] ?? 0.0) + (float) $time, 4);
    }
}

ksort($timings);
$canonical = array_keys($timings);

echo json_encode([
    'timings' => $timings,
    'checksum' => md5(implode("\n", $canonical)),
    'updated_at' => date('c'),
], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES).PHP_EOL;

$committedPath = getcwd().'/tests/.pest/shards.json';
$committed = is_file($committedPath)
    ? array_keys(json_decode((string) file_get_contents($committedPath), true)['timings'] ?? [])
    : [];

fwrite(STDERR, sprintf(
    "%d test files timed; %d not in the committed shards.json, %d in it no longer present.\n",
    count($canonical),
    count(array_diff($canonical, $committed)),
    count(array_diff($committed, $canonical)),
));
