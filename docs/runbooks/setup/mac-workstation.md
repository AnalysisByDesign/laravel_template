# Mac workstation setup

**Status**: Current. Kept in step with the root `Brewfile`.
**Audience**: anyone setting up a Mac, from nothing, to work on {{APP_NAME}}.

This takes a Mac from a fresh install to a running app. Everything comes from Homebrew and the `Brewfile` at the root of this repository, so the only thing to download by hand is that one file. **The steps are in dependency order. Don't reorder them**: each one needs the ones before it.

<!-- TEMPLATE-ONLY:START -->
> **Still reading this in the template?** Until a new app is created from it, the repository is `AnalysisByDesign/laravel_template`. Use that wherever the steps below say `{{GITHUB_OWNER}}/{{GITHUB_REPO}}`. Step 6 creates the app from the template.
<!-- TEMPLATE-ONLY:END -->

## 1. Homebrew

Open Terminal and run the installer from [brew.sh](https://brew.sh). It installs the Xcode Command Line Tools as well, which takes a few minutes and may open a dialog:

```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

On Apple silicon the installer ends by printing two commands that put `brew` on the `PATH`. Run them, or run these, which do the same:

```sh
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
brew --version
```

## 2. Download the Brewfile

The repository isn't on the machine yet, and neither is git, so fetch the one file on its own:

```sh
curl -fsSL https://raw.githubusercontent.com/{{GITHUB_OWNER}}/{{GITHUB_REPO}}/main/Brewfile -o ~/Brewfile
```

**If the repository is private**, that URL returns 404 without credentials. Use one of these instead:
- In a browser, signed in to GitHub, open the repository's `Brewfile`, choose **Download raw file**, and save it as `~/Brewfile`.
- Or install the GitHub CLI first and fetch the file through it:
  ```sh
  brew install gh && gh auth login
  gh api repos/{{GITHUB_OWNER}}/{{GITHUB_REPO}}/contents/Brewfile -H "Accept: application/vnd.github.raw" > ~/Brewfile
  ```

## 3. Install everything in it

```sh
brew bundle --file=~/Brewfile
```

This installs git, the GitHub CLI, Docker Desktop, PHP and Composer, Node LTS, Python, PlantUML, gitleaks, shellcheck, actionlint, jq, uv, VS Code, iTerm2, Claude Code, MySQL Workbench, Redis Insight, Bruno and the VS Code extensions. The first run takes a while. Run the command again to pick up anything that failed; it skips whatever is already there.

Check the result. It should report that all dependencies are satisfied:

```sh
brew bundle check --file=~/Brewfile
```

## 4. First run of each tool

These need a person: each opens a browser, a dialog or a licence prompt.

1. **Docker Desktop.** Open it from Applications, accept the terms, and wait for the engine to show as running.
   - In *Settings → Resources*, give it at least 4 CPUs and 8 GB of memory. `compose.yaml` caps each container at 4 CPUs.
   - Docker Desktop needs a paid subscription in larger organisations. Check [Docker's terms](https://www.docker.com/pricing/) for yours.
   - Check it from Terminal with `docker info`.
2. **GitHub.** Run `gh auth login`, then choose GitHub.com, SSH, and let it generate and upload a new SSH key. Then `gh auth status`.
3. **Git identity**, which every commit carries:
   ```sh
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
4. **Claude Code.** Run `claude` once and sign in.
5. **iTerm2** (optional). It's installed beside Terminal; use whichever you prefer. Everything in this runbook works in either.
6. **MySQL Workbench**, once the stack is up (step 7). Add a connection to `127.0.0.1`, port `FORWARD_DB_PORT` from `laravel/.env` (33NNN). Log in as `{{APP_SLUG}}_ro` for browsing, or as `{{APP_SLUG}}_rw` only when a change is deliberate. Store the password in the macOS Keychain when Workbench offers. Workbench 8.0 may warn that MySQL 8.4 is untested; that's expected, and it works.
7. **Redis Insight**, also once the stack is up. Add a database at `127.0.0.1`, port `FORWARD_REDIS_PORT` (63NNN), with no password: local Redis has none. Queues, cache keys and sessions show up there.
8. **Bruno**, an API client. Its collections are plain files. Keep the ones for this app in the repository, under something like `docs/api/`, so they're reviewed alongside the code they exercise.

**Alternative to Docker Desktop:** [OrbStack](https://orbstack.dev) (`brew install --cask orbstack`) is a faster, lighter replacement that works with Sail. It's free for personal use and paid for commercial use. If you use it, install it *instead of* Docker Desktop: remove `cask "docker-desktop"` from your copy of the Brewfile, rather than running both engines.

## 5. Get the repository

To work on an app that already exists:

```sh
mkdir -p ~/code && cd ~/code
gh repo clone {{GITHUB_OWNER}}/{{GITHUB_REPO}}
cd {{GITHUB_REPO}}
```

## 6. Or create a new app from the template

Skip this step for an existing app.

```sh
mkdir -p ~/code && cd ~/code
gh repo create <owner>/<new-app> --template AnalysisByDesign/laravel_template --private --clone
cd <new-app>
claude
```

Then, in Claude Code, run `/init-laravel-app`. It asks for the app's name, slug, skill prefix, ports and domains, and generates the database passwords. Review the diff it leaves, and commit it on a branch as `docs/initialisation.md` describes.

## 7. Bring the app up

From the repository root:

```sh
git config core.hooksPath .githooks       # gitleaks, PlantUML and the main-push guard
(cd laravel && composer install)          # puts vendor/bin/sail in place; every make target needs it
make up                                   # first run builds the PHP 8.5 image: several minutes
make npm-install
make migrate
make doctor
```

`make doctor` should finish with "All required checks passed". The app is then at the `http://localhost:8NNN` address in `docs/initialisation.md`.

**No `laravel/.env` yet?** That's the case when cloning an existing app on a new machine, because `.env` is never committed. Copy it from `laravel/.env.example`, then set `APP_KEY` (`php laravel/artisan key:generate`) and the three database passwords. Ask whoever runs the project for the values in use, or choose new ones for a local-only database.

## Keeping the machine current

- `brew bundle --file=Brewfile` from the repo root installs anything the Brewfile has gained since. `make doctor` warns when something is missing.
- `brew upgrade` updates everything Homebrew manages.
- When a tool becomes a requirement, add it to the `Brewfile` and to this runbook in the same change.
