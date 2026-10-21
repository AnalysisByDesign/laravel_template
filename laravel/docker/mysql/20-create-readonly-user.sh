#!/usr/bin/env bash
# Create the read-only application user on the MySQL container's first boot.
#
# Mounted into /docker-entrypoint-initdb.d by compose.yaml, so it runs once,
# against an empty data volume, after the image has created MYSQL_DATABASE
# and the read-write MYSQL_USER. MYSQL_RO_USER and MYSQL_RO_PASSWORD come from
# DB_RO_USERNAME and DB_RO_PASSWORD in laravel/.env.
#
# The grant is SELECT on the application database only: no access to the
# testing databases, and no write of any kind.
set -euo pipefail

if [ -z "${MYSQL_RO_USER:-}" ]; then
    echo "20-create-readonly-user: DB_RO_USERNAME is not set, skipping."
    exit 0
fi

if [ -z "${MYSQL_RO_PASSWORD:-}" ]; then
    echo "20-create-readonly-user: DB_RO_PASSWORD is empty; refusing to create ${MYSQL_RO_USER} without a password." >&2
    exit 1
fi

mysql --user=root --password="${MYSQL_ROOT_PASSWORD:?}" <<-EOSQL
    CREATE USER IF NOT EXISTS '${MYSQL_RO_USER}'@'%' IDENTIFIED BY '${MYSQL_RO_PASSWORD}';
    GRANT SELECT, SHOW VIEW ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_RO_USER}'@'%';
    FLUSH PRIVILEGES;
EOSQL

echo "20-create-readonly-user: ${MYSQL_RO_USER} can read ${MYSQL_DATABASE}."
