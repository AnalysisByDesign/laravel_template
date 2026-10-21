# Manual test plans

**Location**: `docs/test-plans/`

Manual, human-driven test plans, one directory per shipped spec (`spec-NNN/`), moved to `done/` once walked clean. This is a different thing from the Pest suite in `laravel/tests/`.

## Purpose

The Pest suite proves code-path correctness. It cannot tell you whether a feature is discoverable, whether the sequence of screens makes sense, or whether the right entry points and menu items exist. A page that exists, with working permissions and a green suite, but that nothing in the UI links to, is caught immediately by a person walking the application and never by a test.

## Two-phase validation

- **Phase 1: the operator as QA and product owner.** Walk each spec's plan, confirm the build matches what the spec promised, and iterate on navigation and UI gaps.
- **Phase 2: a real user.** Repeat the walkthrough in the role of the first real customer, to prove the flow works for someone who does not already know the product.
