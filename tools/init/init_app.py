#!/usr/bin/env python3
"""Turn a fresh copy of the template into a named application, once.

Driven by the init-laravel-app skill, which asks the questions and writes the
answers to a JSON file. This script does everything deterministic:

  1. refuses if the repository is already initialised, or has uncommitted
     changes (so the init is one reviewable diff);
  2. substitutes every {{PLACEHOLDER}} in tracked files and paths, and drops
     the template-only blocks from Markdown, checking nothing unknown is left
     before writing a byte;
  3. writes laravel/.env from the new .env.example, with a generated APP_KEY
     and, if asked, generated database passwords;
  4. writes docs/initialisation.md and the marker file, and prints the same
     summary.

Secrets go into laravel/.env (gitignored) only. They are never printed, and
never written to the summary or the marker.

Usage:
  python3 tools/init/init_app.py --detect
  python3 tools/init/init_app.py --answers answers.json [--dry-run]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import string
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from placeholders import (  # noqa: E402
    MARKER,
    PLACEHOLDER_RE,
    PLACEHOLDERS,
    REPO_ROOT,
    TEMPLATE_END,
    TEMPLATE_START,
    in_scope,
    read_text,
    tracked_files,
)

ENV_EXAMPLE = "laravel/.env.example"
COMPOSER_LOCK = "laravel/composer.lock"
ENV = "laravel/.env"
SUMMARY = "docs/initialisation.md"

# A slug has to be valid as a MySQL database name, a MySQL user name with
# "_rw"/"_ro" appended (32 characters at most), a Compose project name, a
# Docker image name and a DNS label. Lower-case letters and digits, starting
# with a letter, satisfies all of them at once.
SLUG_RE = re.compile(r"^[a-z][a-z0-9]{1,23}$")
PREFIX_RE = re.compile(r"^[a-z][a-z0-9]{1,7}$")
GITHUB_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
HOST_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}$")
# Text lands inside double-quoted .env values, YAML and Markdown.
PROSE_BAD = re.compile(r'["\\$`\n{}]')

PASSWORD_KEYS = ("DB_PASSWORD", "DB_RO_PASSWORD", "DB_ROOT_PASSWORD")


class InitError(Exception):
    pass


def git(*args: str, root: Path = REPO_ROOT, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=check
    ).stdout.strip()


def github_remote(root: Path = REPO_ROOT) -> tuple[str, str] | None:
    url = git("config", "--get", "remote.origin.url", root=root, check=False)
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    return (match.group(1), match.group(2)) if match else None


def laravel_version(root: Path = REPO_ROOT) -> str:
    """The laravel/framework version the template ships, from composer.lock.

    This, not a git tag, is what identifies the template a repository came
    from: GitHub copies a template's files but not its tags, so in a new
    repository `git describe` only ever finds the app's own first commit.
    """
    try:
        lock = json.loads((root / COMPOSER_LOCK).read_text())
    except (OSError, ValueError):
        return "unknown"
    for package in lock.get("packages", []):
        if package.get("name") == "laravel/framework":
            return str(package.get("version", "unknown")).lstrip("v")
    return "unknown"


def default_slug(repo: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", repo.lower())
    slug = re.sub(r"^[0-9]+", "", slug)
    return slug[:24] or "app"


def detect(root: Path = REPO_ROOT) -> dict:
    remote = github_remote(root)
    owner, repo = remote if remote else ("", "")
    slug = default_slug(repo) if repo else ""
    return {
        "initialised": (root / MARKER).exists(),
        "dirty": bool(git("status", "--porcelain", root=root, check=False)),
        "env_exists": (root / ENV).exists(),
        "github_owner": owner,
        "github_repo": repo,
        "suggested": {
            "app_slug": slug,
            "skill_prefix": slug[:4] if slug else "",
            "local_domain": f"{slug}.test" if slug else "",
            "production_domain": f"{slug}.example.com" if slug else "",
            "port_suffix": "100",
        },
        "template_ref": git("describe", "--tags", "--always", root=root, check=False),
        "laravel_version": laravel_version(root),
    }


def validate(a: dict) -> dict[str, str]:
    """The answers as the placeholder map, or InitError naming every problem."""
    problems: list[str] = []

    def need(key: str, ok: bool, why: str) -> None:
        if not ok:
            problems.append(f"{key}: {why} (got {a.get(key)!r})")

    for key in ("app_name", "app_slug", "app_description", "skill_prefix", "github_owner",
                "github_repo", "port_suffix", "local_domain", "production_domain"):
        need(key, isinstance(a.get(key), str) and a[key].strip() != "", "required")
    if problems:
        raise InitError("; ".join(problems))

    need("app_name", len(a["app_name"]) <= 60 and not PROSE_BAD.search(a["app_name"]),
         'at most 60 characters, no quotes, backslashes, $, backticks or braces')
    need("app_description", len(a["app_description"]) <= 200 and not PROSE_BAD.search(a["app_description"]),
         'one line, at most 200 characters, no quotes, backslashes, $, backticks or braces')
    need("app_slug", bool(SLUG_RE.match(a["app_slug"])),
         "2 to 24 lower-case letters and digits, starting with a letter")
    need("skill_prefix", bool(PREFIX_RE.match(a["skill_prefix"])),
         "2 to 8 lower-case letters and digits, starting with a letter")
    need("skill_prefix", a["skill_prefix"] != "speckit", "speckit is spec-kit's own prefix")
    need("github_owner", bool(GITHUB_RE.match(a["github_owner"])), "a GitHub owner name")
    need("github_repo", bool(GITHUB_RE.match(a["github_repo"])), "a GitHub repository name")
    need("port_suffix", bool(re.fullmatch(r"[1-9][0-9]{2}", a["port_suffix"])),
         "three digits, 100 to 999 (ports become 8NNN, 5NNN, 33NNN, 63NNN)")
    need("local_domain", bool(HOST_RE.match(a["local_domain"])), "a lower-case hostname")
    need("production_domain", bool(HOST_RE.match(a["production_domain"])), "a lower-case hostname")
    if problems:
        raise InitError("; ".join(problems))

    return {
        "APP_NAME": a["app_name"].strip(),
        "APP_SLUG": a["app_slug"],
        "APP_DESCRIPTION": a["app_description"].strip(),
        "SKILL_PREFIX": a["skill_prefix"],
        "GITHUB_OWNER": a["github_owner"],
        "GITHUB_REPO": a["github_repo"],
        "PORT_SUFFIX": a["port_suffix"],
        "LOCAL_DOMAIN": a["local_domain"],
        "PRODUCTION_DOMAIN": a["production_domain"],
    }


def substitute(text: str, values: dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), text)


def strip_template_blocks(text: str) -> str:
    pattern = re.compile(
        rf"^[ \t]*{re.escape(TEMPLATE_START)}[ \t]*\n.*?^[ \t]*{re.escape(TEMPLATE_END)}[ \t]*\n\n?",
        re.S | re.M,
    )
    return pattern.sub("", text)


def plan(values: dict[str, str], root: Path = REPO_ROOT) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """New contents by path, and path renames, with nothing written yet."""
    contents: dict[str, str] = {}
    renames: list[tuple[str, str]] = []
    leftovers: list[str] = []

    for rel in tracked_files(root):
        if not in_scope(rel):
            continue
        text = read_text(root / rel)
        if text is not None:
            new = substitute(text, values)
            if rel.endswith(".md"):
                new = strip_template_blocks(new)
            left = set(PLACEHOLDER_RE.findall(new))
            if left:
                leftovers.append(f"{rel}: {', '.join(sorted(left))}")
            if new != text:
                contents[rel] = new
        new_rel = substitute(rel, values)
        if new_rel != rel:
            renames.append((rel, new_rel))

    unknown = {n for line in leftovers for n in line.split(": ", 1)[1].split(", ")} - PLACEHOLDERS.keys()
    if leftovers:
        detail = "\n  ".join(leftovers)
        raise InitError(
            f"placeholders would remain after substitution"
            f"{' (unknown: ' + ', '.join(sorted(unknown)) + ')' if unknown else ''}:\n  {detail}"
        )
    return contents, renames


def directory_renames(renames: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Collapse file renames to the topmost directory or file that changes name."""
    moves: dict[str, str] = {}
    for old, new in renames:
        old_parts, new_parts = old.split("/"), new.split("/")
        for i, (o, n) in enumerate(zip(old_parts, new_parts)):
            if o != n:
                moves["/".join(old_parts[: i + 1])] = "/".join(new_parts[: i + 1])
                break
    return sorted(moves.items())


def generate_password(length: int = 32) -> str:
    # Letters and digits only: safe unquoted in .env, in a mysql -p argument
    # and in a compose interpolation, with no escaping anywhere.
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def app_key() -> str:
    # The format `php artisan key:generate` writes for the AES-256-CBC cipher.
    return "base64:" + base64.b64encode(os.urandom(32)).decode()


def set_env(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    if not pattern.search(text):
        raise InitError(f"{ENV_EXAMPLE} has no {key}= line to fill")
    return pattern.sub(lambda _: f"{key}={value}", text, count=1)


def build_env(example: str, generate: bool) -> str:
    env = set_env(example, "APP_KEY", app_key())
    if generate:
        for key in PASSWORD_KEYS:
            env = set_env(env, key, generate_password())
    return env


def summary(values: dict[str, str], generated: bool, template_ref: str, laravel: str, when: str) -> str:
    s, p = values["APP_SLUG"], values["PORT_SUFFIX"]
    owner, repo = values["GITHUB_OWNER"], values["GITHUB_REPO"]
    passwords = (
        "Generated: 32 random letters and digits each, written to `laravel/.env` only."
        if generated
        else "**Not generated.** Set `DB_PASSWORD`, `DB_RO_PASSWORD` and `DB_ROOT_PASSWORD` in `laravel/.env` before the first `make up`."
    )
    return f"""# Initialisation

**Status**: Generated {when} by `tools/init/init_app.py` (the init-laravel-app skill) from the Laravel template carrying Laravel {laravel}, at commit `{template_ref}`. Record only: re-running init is refused.

## Application

| | |
| --- | --- |
| Name | {values['APP_NAME']} |
| Slug | `{s}` |
| Description | {values['APP_DESCRIPTION']} |
| Repository | [{owner}/{repo}](https://github.com/{owner}/{repo}) |
| Project skills | `{values['SKILL_PREFIX']}-*` (for example `/{values['SKILL_PREFIX']}-merge`) |

## Local stack

| | |
| --- | --- |
| App | http://localhost:8{p} |
| Vite | http://localhost:5{p} |
| MySQL (host) | 127.0.0.1:33{p} |
| Redis (host) | 127.0.0.1:63{p} |
| HTTPS (Caddy) | https://{values['LOCAL_DOMAIN']} (needs an `/etc/hosts` entry) |
| Compose project | `{s}-laravel` |
| Production host | {values['PRODUCTION_DOMAIN']} |

## Database

| Account | Access |
| --- | --- |
| `{s}_rw` | Read-write on `{s}`, plus the `testing%` databases for Pest |
| `{s}_ro` | `SELECT` on `{s}` only |
| `root` | `make backup`, `make restore` and `make test-db-grant` only |

Passwords: {passwords} `APP_KEY` was generated the same way. None of these values appear in this file or in git.

The MySQL container creates all three accounts on its **first** boot, from `laravel/.env`. Changing a password later means changing it in MySQL by hand as well.

## Next steps

1. Review and commit this diff: `git add -A && git commit -m "chore: initialise {s} from the template"`.
2. `make up` (the first run builds the PHP 8.5 image), then `make doctor`.
3. `git config core.hooksPath .githooks`.
4. Write the product summary and the `(PRODUCT)` principles in `.specify/memory/constitution.md`, and the phases in `docs/features/roadmap.md`.
5. Set the GitHub secrets and variables listed at the top of `.github/workflows/deploy.yml`, create the `production` environment and the `run-pest` label, and import `.github/rulesets/main.json`.
6. Start on `docs/work-packages/backlog/wp-laravel-foundation.md`.
"""


def apply(answers: dict, root: Path = REPO_ROOT, dry_run: bool = False) -> str:
    if (root / MARKER).exists():
        raise InitError(f"already initialised ({MARKER} exists); init runs once only")
    if git("status", "--porcelain", root=root, check=False):
        raise InitError("the working tree has uncommitted changes; commit or stash them so init is one reviewable diff")

    values = validate(answers)
    generate = bool(answers.get("generate_passwords"))
    template_ref = git("describe", "--tags", "--always", root=root, check=False) or "unknown"
    laravel = laravel_version(root)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    contents, renames = plan(values, root)
    moves = directory_renames(renames)
    example = contents.get(ENV_EXAMPLE, (root / ENV_EXAMPLE).read_text())
    env = build_env(example, generate)
    text = summary(values, generate, template_ref, laravel, when)

    if dry_run:
        return (
            f"Dry run: {len(contents)} file(s) would change, {len(moves)} path(s) would be renamed:\n"
            + "".join(f"  {o} -> {n}\n" for o, n in moves)
        )

    for rel, new in contents.items():
        (root / rel).write_text(new)
    for old, new in moves:
        (root / new).parent.mkdir(parents=True, exist_ok=True)
        git("mv", old, new, root=root)

    env_path = root / ENV
    if env_path.exists():
        env_path.rename(env_path.with_name(f".env.pre-init-{datetime.now():%Y%m%d-%H%M%S}"))
    env_path.write_text(env)
    env_path.chmod(0o600)

    (root / SUMMARY).write_text(text)
    marker = {
        "initialised_at": when,
        "template_ref": template_ref,
        "laravel_version": laravel,
        "values": values,
        "passwords_generated": generate,
    }
    (root / MARKER).write_text(json.dumps(marker, indent=2) + "\n")
    return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--detect", action="store_true", help="print what init would start from, as JSON")
    mode.add_argument("--answers", type=Path, help="JSON file of answers from the skill")
    ap.add_argument("--dry-run", action="store_true", help="validate and plan, write nothing")
    ap.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = ap.parse_args(argv)

    if args.detect:
        print(json.dumps(detect(args.repo_root), indent=2))
        return 0

    try:
        answers = json.loads(args.answers.read_text())
        print(apply(answers, args.repo_root, args.dry_run))
    except InitError as problem:
        print(f"FAIL {problem}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
