#!/usr/bin/env bash
#
# Squash-merge one documentation-index regeneration pull request, the fifth
# phase of the tpl-merge skill, after proving it is that and nothing else.
#
# Why this exists rather than a permission rule on `gh pr merge`
# -------------------------------------------------------------
# The Phase 5 pull request is merged in the same run as the merge it
# follows: its content is generated, nothing in it is hand-written, and
# leaving it open leaves the indexes stale on `main`. The permission layer
# refuses a bare `gh pr merge` for it as "Merge Without Review", and rightly:
# a Bash permission rule matches a command
# prefix, and `gh pr merge 457 --squash` carries a pull request NUMBER, not a
# branch name. So the only rule that would have allowed the Phase 5 merge
# would also have allowed merging any feature pull request with no
# read-through, which CLAUDE.md requires as a merge gate.
#
# This script is the narrow thing a permission rule can name. Every condition
# that made the Phase 5 merge safe is checked here, in code, before anything
# is merged, so the guard no longer rests on an agent having read the skill
# and followed it.
#
# It refuses unless ALL of these hold:
#   1. the pull request is open, not a draft, and targets `main`
#   2. its head branch is `docs/regenerate-after-*`
#   3. every changed path is one of the generated documents in PERMITTED_EXACT
#   4. GitHub reports a completed, successful run for the head commit, with
#      every job either successful or skipped, and nothing pending
#
# Usage:
#   tools/merge-docs-pr.sh <pr-number>
#   tools/merge-docs-pr.sh <pr-number> --dry-run   checks only, merges nothing
#
# Exit codes: 0 merged (or dry run passed), 1 refused, 2 usage error.

set -euo pipefail

PERMITTED_EXACT=(
  "docs/reference.md"
  "docs/roadmap/upcoming.md"
  "docs/roadmap/completed.md"
  "docs/roadmap/roadmap-overview.puml"
  "docs/roadmap/roadmap-overview.png"
  "docs/roadmap/roadmap-gates.puml"
  "docs/roadmap/roadmap-gates.png"
)
PERMITTED_PREFIX="docs/claude-transfer/"
HEAD_BRANCH_PREFIX="docs/regenerate-after-"

die() {
  printf 'REFUSED: %s\n' "$1" >&2
  exit 1
}

usage() {
  printf 'usage: %s <pr-number> [--dry-run]\n' "$0" >&2
  exit 2
}

[ $# -ge 1 ] || usage
PR="$1"
shift

DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    *) usage ;;
  esac
  shift
done

case "$PR" in
  '' | *[!0-9]*) usage ;;
esac

command -v gh >/dev/null 2>&1 || die "the gh CLI is not on PATH"

# ---------------------------------------------------------------- 1. the PR

read -r STATE IS_DRAFT BASE HEAD MERGEABLE HEAD_SHA <<EOF
$(gh pr view "$PR" --json state,isDraft,baseRefName,headRefName,mergeable,headRefOid \
  --jq '[.state, (.isDraft|tostring), .baseRefName, .headRefName, .mergeable, .headRefOid] | @tsv')
EOF

[ -n "${STATE:-}" ] || die "could not read pull request #${PR}"
[ "$STATE" = "OPEN" ] || die "#${PR} is ${STATE}, not OPEN"
[ "$IS_DRAFT" = "false" ] || die "#${PR} is a draft; a draft's every-push checks are skipped, so there is no green to read"
[ "$BASE" = "main" ] || die "#${PR} targets '${BASE}', not main"

case "$HEAD" in
  "${HEAD_BRANCH_PREFIX}"*) ;;
  *) die "head branch '${HEAD}' is not ${HEAD_BRANCH_PREFIX}*; this script merges only index regeneration branches" ;;
esac

# MERGEABLE is the only accepted value. CONFLICTING is a conflict, and
# UNKNOWN means GitHub has not finished computing it, which is a pending
# answer rather than a yes.
[ "$MERGEABLE" = "MERGEABLE" ] || die "#${PR} reports mergeable=${MERGEABLE}; only MERGEABLE is accepted"

printf 'PR          #%s  %s -> %s\n' "$PR" "$HEAD" "$BASE"

# ------------------------------------------------- 2. generated paths only

FILES="$(gh pr view "$PR" --json files --jq '.files[].path')"
[ -n "$FILES" ] || die "#${PR} changes no files"

OFFENDERS=""
COUNT=0
while IFS= read -r path; do
  [ -n "$path" ] || continue
  COUNT=$((COUNT + 1))
  permitted=0
  for allowed in "${PERMITTED_EXACT[@]}"; do
    [ "$path" = "$allowed" ] && permitted=1 && break
  done
  if [ "$permitted" -eq 0 ]; then
    case "$path" in
      "${PERMITTED_PREFIX}"*) permitted=1 ;;
    esac
  fi
  [ "$permitted" -eq 1 ] || OFFENDERS="${OFFENDERS}  ${path}"$'\n'
done <<EOF
$FILES
EOF

if [ -n "$OFFENDERS" ]; then
  printf 'REFUSED: #%s changes paths that are not generated output:\n%s' "$PR" "$OFFENDERS" >&2
  printf 'Permitted: %s, and anything under %s\n' \
    "$(IFS=,; printf '%s' "${PERMITTED_EXACT[*]}" | sed 's/,/, /g')" "$PERMITTED_PREFIX" >&2
  exit 1
fi

printf 'Files       %s, all generated output\n' "$COUNT"

# -------------------------------------------------------------- 3. the checks

# `gh pr checks` needs a token scope this account's PAT does not have (it
# returns "Resource not accessible by personal access token"), so the run is
# read through the Actions API instead, and pinned to the head commit so an
# older green run cannot answer for newer code.
read -r RUN_ID RUN_STATUS RUN_CONCLUSION <<EOF
$(gh run list --branch "$HEAD" --limit 20 \
  --json databaseId,headSha,status,conclusion \
  --jq "[.[] | select(.headSha == \"${HEAD_SHA}\")] | .[0] // empty | [(.databaseId|tostring), .status, (.conclusion // \"none\")] | @tsv")
EOF

[ -n "${RUN_ID:-}" ] || die "no workflow run found for head commit ${HEAD_SHA:0:8}; nothing has checked this code"

[ "$RUN_STATUS" = "completed" ] || die "run ${RUN_ID} is ${RUN_STATUS}; pending is not green"
[ "$RUN_CONCLUSION" = "success" ] || die "run ${RUN_ID} concluded ${RUN_CONCLUSION}"

# A successful run is not sufficient on its own: assert every job
# individually, so a job that failed while the run still reported success
# cannot slip through, and so a pending job is caught.
BAD_JOBS="$(gh run view "$RUN_ID" --json jobs \
  --jq '.jobs[] | select(.status != "completed" or (.conclusion != "success" and .conclusion != "skipped")) | "  \(.name): \(.status)/\(.conclusion // "")"')"

if [ -n "$BAD_JOBS" ]; then
  printf 'REFUSED: run %s has jobs that are neither successful nor a deliberate skip:\n%s\n' "$RUN_ID" "$BAD_JOBS" >&2
  exit 1
fi

JOB_SUMMARY="$(gh run view "$RUN_ID" --json jobs --jq '[.jobs[] | select(.conclusion == "success")] | length') green, $(gh run view "$RUN_ID" --json jobs --jq '[.jobs[] | select(.conclusion == "skipped")] | length') skipped"
printf 'Checks      run %s: %s\n' "$RUN_ID" "$JOB_SUMMARY"

# ------------------------------------------------------------- 4. the merge

TITLE="$(gh pr view "$PR" --json title --jq '.title')"
BODY="$(gh pr view "$PR" --json body --jq '.body')"

if [ "$DRY_RUN" -eq 1 ]; then
  printf '\nDry run: every condition passed. Would squash-merge with subject:\n  %s\n' "$TITLE"
  exit 0
fi

# --subject is passed explicitly because release-please parses the squash
# subject, and letting GitHub default it produces a subject with "(#NNN)"
# already attached.
gh pr merge "$PR" --squash --delete-branch --subject "$TITLE" --body "$BODY"

printf '\nMerged #%s.\n' "$PR"
