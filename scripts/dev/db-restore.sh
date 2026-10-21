#!/usr/bin/env bash
# Restore the dev database from a dump in backups/.
#
#   scripts/dev/db-restore.sh            # the newest dump
#   scripts/dev/db-restore.sh latest     # the same
#   scripts/dev/db-restore.sh <file>     # a named dump, in backups/ or a path
#
# Asks for a typed "yes", backs up the current database first, then drops and
# recreates it before loading the dump, so tables created since the dump do
# not survive the restore.
# Single-quoted $VARS below expand inside the mysql container, from its own
# environment, which is the point: the host never holds the root password.
# shellcheck disable=SC2016
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
sail="$root/laravel/vendor/bin/sail"
dir="$root/backups"
want="${1:-latest}"

if [ "$want" = latest ]; then
    # Our own timestamped names, so ls -t is safe here.
    # shellcheck disable=SC2012
    dump="$(ls -1t "$dir"/*.sql.gz 2>/dev/null | head -1 || true)"
    [ -n "$dump" ] || { echo "No dumps in backups/. Make one with make backup." >&2; exit 1; }
elif [ -f "$want" ]; then
    dump="$want"
elif [ -f "$dir/$want" ]; then
    dump="$dir/$want"
else
    echo "No such dump: $want" >&2
    exit 1
fi

cd "$root/laravel"
if ! "$sail" ps --status running --services 2>/dev/null | grep -qx mysql; then
    echo "The mysql container is not running. Start the stack with make up." >&2
    exit 1
fi

db="$("$sail" exec -T mysql sh -c 'printf %s "$MYSQL_DATABASE"')"
dumped="$(gunzip -c "$dump" | grep -m1 -oE '^CREATE DATABASE .*`[^`]+`' | sed -E 's/.*`([^`]+)`$/\1/' || true)"
if [ "$dumped" != "$db" ]; then
    echo "Refusing: ${dump#"$root"/} is a dump of '${dumped:-unknown}', not of '${db}'." >&2
    exit 1
fi

"$root/scripts/dev/confirm.sh" "Replace the '${db}' database with ${dump#"$root"/}? The current data is backed up first."
"$root/scripts/dev/db-backup.sh"

"$sail" exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot \
    -e "DROP DATABASE IF EXISTS \`$MYSQL_DATABASE\`; CREATE DATABASE \`$MYSQL_DATABASE\`;"'
gunzip -c "$dump" | "$sail" exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot'

echo "Restored ${db} from ${dump#"$root"/}."
