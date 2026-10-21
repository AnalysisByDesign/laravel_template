# ADR-0001: Repository layout, one top-level directory per toolchain

**Status**: Accepted
**Date**: 2026-10-21 (carried from the template's source project)

## Context

A repository that holds an application alongside its infrastructure tooling, process documents and automation reads badly when the application's files sit at the root: infrastructure configuration ends up mixed into the Laravel tree, or Laravel's files crowd out everything else.

## Decision

- The Laravel application does **not** live at the repository root. It lives at `laravel/`: `composer.json`, `artisan`, `public/`, `app/` and everything Laravel-internal, nested one level down.
- Sibling top-level directories are reserved for other toolchains as they are added (`terraform/`, `packer/`, and any future tool), so the root reads as one directory per toolchain. Process material sits beside them: `docs/`, `specs/`, `.specify/`, `tools/`, `scripts/`.
- Laravel has no requirement to sit at a repository root. It only needs the web server's document root at `laravel/public` and `artisan` and Composer run with `laravel/` as the working directory; `.env`, `storage/` and `bootstrap/cache/` resolve relative to Laravel's own base path.

## Consequences

- CI steps set `working-directory: laravel` (or `defaults.run.working-directory`).
- The root `Makefile` wraps Sail, artisan and Composer and changes into `laravel/` first, so commands run from the repository root.
- Deploy scripts and any image build sync from `laravel/`, not the repository root.
- The Sail container mounts `laravel/` only, so checks over `docs/` (the `docs-guard` scripts) run on the host and in CI, never as Pest tests.
- release-please is unaffected: it tracks commits and tags at the repository root for a single-package repository regardless of where the code lives.
