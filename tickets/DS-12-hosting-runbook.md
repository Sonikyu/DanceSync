# DS-12 — Hosting runbook

**Track:** Operate · **Size:** S · **Depends on:** [DS-08](DS-08-docker-compose.md), [DS-09](DS-09-access-control.md)

## Context

The plan is a small VPS or a home machine on a private network. The choice interacts with two other things: a reverse proxy's default 60 s timeout kills long renders, and YouTube blocks many datacenter IPs.

## Scope

A `docs/hosting.md` covering: the chosen target and why; reverse proxy config with timeouts raised past the longest expected render; TLS; where the volumes live and how they're backed up; how to update (pull, rebuild, restart); and the result of testing a YouTube import from the chosen host.

## Acceptance criteria

- Someone following the document reaches a running, password-protected instance
- The proxy timeout is stated as a number, justified by a measured render time
- The YouTube-from-this-host question is answered in writing, either way
