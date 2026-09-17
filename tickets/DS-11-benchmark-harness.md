# DS-11 — Real-clip benchmark harness

**Track:** Operate · **Size:** M · **Depends on:** [DS-01](DS-01-ci-test-workflow.md)

## Context

Tier A is synthetic and catches outright bugs. It doesn't catch a matcher change that still passes synthetic cases but gets worse on phone recordings in rooms. Practice speeds (DS-40…44) changes the matcher substantially, so this wants to exist first.

## Scope

- A fixtures manifest: for each real clip, its reference, the known-correct offset and rate, and how the truth was established. Media stays gitignored; the manifest is committed.
- A runner that matches every fixture and reports offset error, rate error, score, and `peak_ratio` as a table.
- Thresholds that fail the run on regression, plus a written baseline committed alongside.
- A CI job that runs it only when the fixture media is available, so forks and cold clones still pass.

## Acceptance criteria

- The harness runs locally against the owner's clips and prints a per-clip table
- Deliberately detuning a matcher parameter makes it fail
- CI skips cleanly with a clear message when the media is absent
