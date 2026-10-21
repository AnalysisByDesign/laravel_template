#!/usr/bin/env bash
#
# scripts/deploy/verify.sh
#
# Post-deploy verify, the last step of deploy.yml. Asserts /up returns 200
# and / returns 200 with the expected structural marker present. The
# marker is deliberately the <html lang=...> attribute, never translated
# copy text, because wording changes independently of deploy correctness.
#
# Usage:
#   scripts/deploy/verify.sh <base-url>
#   VERIFY_BASE_URL=<base-url> scripts/deploy/verify.sh
#
# <base-url> is the public origin to verify against, e.g. https://{{PRODUCTION_DOMAIN}}
# (passed from deploy.yml's PRODUCTION_URL variable, so this script
# stays testable against any origin).
#
# The "/" response's status and body are fetched with a single curl call
# (-w appends the status code after the body, then the two are split back
# apart) so the status checked and the body inspected are guaranteed to
# come from the same response; two separate curls to the same path
# could observe two different responses.

set -euo pipefail

BASE_URL="${1:-${VERIFY_BASE_URL:-}}"
if [[ -z "${BASE_URL}" ]]; then
  echo "error: no base url given (pass as \$1 or set VERIFY_BASE_URL)" >&2
  exit 1
fi

BASE_URL="${BASE_URL%/}"

up_status="$(curl -sS -o /dev/null -w '%{http_code}' "${BASE_URL}/up")"
if [[ "${up_status}" != "200" ]]; then
  echo "::error::${BASE_URL}/up returned ${up_status}, expected 200"
  exit 1
fi

home_response="$(curl -sS -w '\n%{http_code}' "${BASE_URL}/")"
home_status="${home_response##*$'\n'}"
home_body="${home_response%$'\n'*}"

if [[ "${home_status}" != "200" ]]; then
  echo "::error::${BASE_URL}/ returned ${home_status}, expected 200"
  exit 1
fi

if ! grep -qi '<html lang=' <<< "${home_body}"; then
  echo "::error::${BASE_URL}/ response is missing an <html lang=...> marker"
  exit 1
fi

echo "==> /up and / both verified 200 with expected content"
