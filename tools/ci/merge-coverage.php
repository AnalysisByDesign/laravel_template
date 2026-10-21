<?php

/*
 * Merges the per-shard coverage files written by `pest --shard=N/M
 * --coverage-php=...` and applies the coverage floor to the whole suite,
 * the way `pest --coverage --min=N` does for a single run: lines covered
 * as a percentage of executable lines under phpunit.xml's <source>, with
 * the same one-decimal floor before comparing.
 *
 * Run from laravel/, so the vendor phpunit that wrote the files is the one
 * that reads them back:
 *
 *   php ../tools/ci/merge-coverage.php 70 coverage/*.cov
 */

declare(strict_types=1);

use SebastianBergmann\CodeCoverage\CodeCoverage;

require getcwd().'/vendor/autoload.php';

[, $min] = $argv + [null, null];
$files = array_slice($argv, 2);

if (! is_numeric($min) || $files === []) {
    fwrite(STDERR, "usage: merge-coverage.php <min-percent> <file.cov>...\n");
    exit(2);
}

$merged = null;

foreach ($files as $file) {
    $coverage = include $file;

    if (! $coverage instanceof CodeCoverage) {
        fwrite(STDERR, "{$file} is not a php-code-coverage file\n");
        exit(2);
    }

    $merged === null ? $merged = $coverage : $merged->merge($coverage);
}

$report = $merged->getReport();
$percent = floor($report->percentageOfExecutedLines()->asFloat() * 10) / 10;
$summary = sprintf(
    'Coverage across %d shard%s: %.1f%% of %d executable lines (floor %.1f%%).',
    count($files),
    count($files) === 1 ? '' : 's',
    $percent,
    $report->numberOfExecutableLines(),
    (float) $min,
);

echo $summary.PHP_EOL;

if (($summaryFile = getenv('GITHUB_STEP_SUMMARY')) !== false && $summaryFile !== '') {
    file_put_contents($summaryFile, "## Pest coverage\n\n{$summary}\n", FILE_APPEND);
}

exit($percent < (float) $min ? 1 : 0);
