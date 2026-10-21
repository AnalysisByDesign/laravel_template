# Brewfile: everything a Mac needs to develop this repository.
#
#   brew bundle --file=Brewfile          # install anything missing
#   brew bundle check --file=Brewfile    # report what is missing, change nothing
#
# A new machine, from nothing: docs/runbooks/setup/mac-workstation.md.
# Keep this file and that runbook in step, and make doctor checks the result.

# ── Source control ────────────────────────────────────────────────────────────
brew "git"
brew "gh"               # GitHub CLI: auth, PRs, repo create --template; the skills use it

# ── Containers ────────────────────────────────────────────────────────────────
# The whole app runs in Docker via Laravel Sail (PHP, MySQL, Redis, Caddy).
# Open Docker Desktop once after installing it, to accept its terms and start
# the engine.
cask "docker-desktop"

# ── PHP ───────────────────────────────────────────────────────────────────────
# Host PHP and Composer are needed once per clone: `composer install` in
# laravel/ is what puts vendor/bin/sail there, and every make target runs
# through Sail after that.
brew "php"              # composer.json requires ^8.5
brew "composer"

# ── JavaScript ────────────────────────────────────────────────────────────────
# Node LTS. Keg-only, so link it onto the PATH.
brew "node@24", link: true

# ── Repository tooling ───────────────────────────────────────────────────────
brew "python"           # tools/: docs guards, init, env-sync, roadmap
brew "plantuml"         # the pre-commit hook renders docs/**/*.puml to PNG
brew "gitleaks"         # the pre-commit hook scans staged files for secrets
brew "shellcheck"       # lints scripts/ and .githooks/, as CI does
brew "actionlint"       # lints .github/workflows/, as CI does
brew "jq"
brew "uv"               # installs spec-kit's `specify` CLI, for spec-kit upgrades

# ── Editor, terminal and agent ────────────────────────────────────────────────
cask "visual-studio-code"
cask "iterm2"           # casks always install the current release; iTerm2 then self-updates
cask "claude-code"

# ── Database GUI ──────────────────────────────────────────────────────────────
# Connects to the Sail MySQL on 127.0.0.1:FORWARD_DB_PORT (33NNN) as the
# <slug>_ro user for browsing, or <slug>_rw when a change is deliberate.
cask "mysqlworkbench"
# Browses the Sail Redis (queues, cache, sessions) on 127.0.0.1:FORWARD_REDIS_PORT.
cask "redis-insight"

# ── API client ────────────────────────────────────────────────────────────────
# Collections are plain files, so they can live in the repository beside the
# code they exercise.
cask "bruno"

vscode "anthropic.claude-code"
vscode "laravel.vscode-laravel"
vscode "bmewburn.vscode-intelephense-client"
vscode "open-southeners.laravel-pint"
vscode "editorconfig.editorconfig"
vscode "docker.docker"
vscode "redhat.vscode-yaml"
vscode "github.vscode-github-actions"
vscode "jebbs.plantuml"
