#!/usr/bin/env bash
# Ask a person, at a terminal, to type the literal word "yes".
#
#   scripts/dev/confirm.sh "Drop every table in the dev database?"
#
# Reads from /dev/tty, never stdin, so the answer cannot be piped or scripted
# in and an agent's shell (no terminal) always gets a refusal. There is
# deliberately no environment variable or flag that skips the question.
set -euo pipefail

question="${1:?usage: confirm.sh <question>}"

if ! { exec 3</dev/tty; } 2>/dev/null; then
    echo "Refusing: this needs a person at a terminal to type 'yes'." >&2
    exit 1
fi

printf '%s\nType yes to continue: ' "$question" >/dev/tty
read -r answer <&3
exec 3<&-

if [ "$answer" != "yes" ]; then
    echo "Not confirmed (got '${answer}'). Nothing done." >&2
    exit 1
fi
