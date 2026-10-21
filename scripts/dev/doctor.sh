#!/usr/bin/env bash
# Check this machine can develop the app, cheapest checks first.
#
# Read-only: starts nothing, writes nothing, prints no secret values. Each
# line is ok, warn or FAIL; the exit status is 1 if anything FAILed.
set -uo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"
env_file="$root/laravel/.env"
sail="$root/laravel/vendor/bin/sail"
fails=0

ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  warn  %s\n' "$*"; }
fail() { printf '  FAIL  %s\n' "$*"; fails=$((fails + 1)); }

# The value of KEY in laravel/.env, for presence checks only; never printed.
env_value() {
    sed -n "s/^$1=//p" "$env_file" | tail -1 | sed -e 's/^"//' -e 's/"$//'
}

echo "Repository"
if [ ! -f "$root/.laravel-app-initialised.json" ]; then
    fail "not initialised: run the init-laravel-app skill"
elif python3 "$root/tools/init/check_placeholders.py" >/dev/null 2>&1; then
    ok "initialised, no placeholders left"
else
    fail "initialised, but placeholders remain (python3 tools/init/check_placeholders.py)"
fi
if [ "$(git -C "$root" config --get core.hooksPath)" = ".githooks" ]; then
    ok "git hooks active (.githooks)"
else
    warn "git hooks not active: git config core.hooksPath .githooks"
fi

echo "Host tools"
if command -v brew >/dev/null 2>&1; then
    # --no-upgrade: only a missing entry counts; an outdated one is not a fault.
    if HOMEBREW_NO_AUTO_UPDATE=1 brew bundle check --file="$root/Brewfile" --no-upgrade >/dev/null 2>&1; then
        ok "everything in the Brewfile is installed"
    else
        warn "Brewfile entries missing: brew bundle --file=Brewfile"
    fi
else
    warn "Homebrew not found: docs/runbooks/setup/mac-workstation.md"
fi
for tool in docker php composer node npm python3 plantuml gitleaks shellcheck gh; do
    if command -v "$tool" >/dev/null 2>&1; then
        ok "$tool"
    elif [ "$tool" = docker ]; then
        fail "docker is not installed"
    else
        warn "$tool is not installed"
    fi
done

echo "Environment"
if [ ! -f "$env_file" ]; then
    fail "laravel/.env is missing: copy laravel/.env.example, or re-run init"
else
    ok "laravel/.env exists"
    for key in APP_KEY DB_PASSWORD DB_RO_PASSWORD DB_ROOT_PASSWORD; do
        if [ -n "$(env_value "$key")" ]; then ok "$key is set"; else fail "$key is empty in laravel/.env"; fi
    done
    python3 "$root/tools/env-sync/sync_env.py" --check --strict >/dev/null 2>&1
    case $? in
        0) ok "laravel/.env is in line with .env.example" ;;
        3) warn "laravel/.env is out of line with .env.example: make env-sync" ;;
        *) fail "env-sync could not verify laravel/.env: make env-sync ARGS=--check" ;;
    esac
fi
if [ -d "$root/laravel/vendor" ]; then ok "composer dependencies installed"; else fail "laravel/vendor missing: composer install in laravel/"; fi
if [ -d "$root/laravel/node_modules" ]; then ok "npm dependencies installed"; else warn "laravel/node_modules missing: make npm-install"; fi

echo "Stack"
if ! docker info >/dev/null 2>&1; then
    fail "the Docker daemon is not reachable"
elif [ ! -x "$sail" ]; then
    fail "Sail is not installed (laravel/vendor/bin/sail)"
else
    running="$(cd "$root/laravel" && "$sail" ps --status running --services 2>/dev/null)"
    for svc in laravel.test mysql redis caddy; do
        if grep -qx "$svc" <<<"$running"; then ok "$svc running"; else warn "$svc not running: make up"; fi
    done
    if grep -qx mysql <<<"$running"; then
        # shellcheck disable=SC2016  # expands inside the container
        if (cd "$root/laravel" && "$sail" exec -T mysql sh -c \
            'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot -N -e "SELECT 1 FROM mysql.user WHERE user = \"$MYSQL_RO_USER\""' 2>/dev/null | grep -qx 1); then
            ok "read-only database user exists"
        else
            fail "read-only database user missing (created on the volume's first boot only)"
        fi
    fi
fi

echo
if [ "$fails" -gt 0 ]; then
    echo "$fails check(s) failed."
    exit 1
fi
echo "All required checks passed."
