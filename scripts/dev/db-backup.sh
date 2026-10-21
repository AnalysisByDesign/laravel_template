#!/usr/bin/env bash
# Dump the dev database to backups/<database>-YYYYmmdd-HHMMSS.sql.gz.
#
# Runs mysqldump inside the Sail mysql container as root, so it needs the
# stack up. The dump carries CREATE DATABASE and USE (--databases), which is
# what db-restore.sh checks the target against. backups/ is gitignored.
# Single-quoted $VARS below expand inside the mysql container, from its own
# environment, which is the point: the host never holds the root password.
# shellcheck disable=SC2016
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
sail="$root/laravel/vendor/bin/sail"
dir="$root/backups"

cd "$root/laravel"
if ! "$sail" ps --status running --services 2>/dev/null | grep -qx mysql; then
    echo "The mysql container is not running. Start the stack with make up." >&2
    exit 1
fi

db="$("$sail" exec -T mysql sh -c 'printf %s "$MYSQL_DATABASE"')"
mkdir -p "$dir"
out="$dir/${db}-$(date +%Y%m%d-%H%M%S).sql.gz"

# MYSQL_PWD rather than -p keeps the password out of the process list and
# stops mysqldump warning about it on every run.
"$sail" exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot \
    --single-transaction --routines --triggers --no-tablespaces \
    --databases "$MYSQL_DATABASE"' | gzip >"$out.partial"

mv "$out.partial" "$out"
echo "Backed up ${db} to ${out#"$root"/} ($(du -h "$out" | cut -f1))."
