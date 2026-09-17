# DS-01 — Run the test suites in CI

**Track:** Foundations · **Size:** S · **Depends on:** nothing · **Spec:** [next-steps.md](../next-steps.md) Phase 5

## Context

Both workflows in `.github/workflows/` run `claude-code-action`. Nothing runs `pytest` or Vitest, so a PR can go green with a broken matcher. This is first because every later ticket relies on the gate being real.

## Scope

- A `test.yml` workflow on `pull_request` and on pushes to `main`.
- Python job: Python 3.11, `apt-get install ffmpeg` (or `FedericoCarboni/setup-ffmpeg`), `pip install -e '.[dev]'`, `pytest`.
- Node job: Node 22, `npm --prefix web ci`, `npm --prefix web test`.
- Cache pip and npm so the run stays under a couple of minutes.

## Out of scope

Making the two jobs required in branch protection (a repo setting, not a file), and the real-clip benchmark (DS-11).

## Acceptance criteria

- A PR that breaks a Tier A case fails CI
- A PR that breaks a `flow.js` helper fails CI
- The full run finishes in under 5 minutes on a cold cache
