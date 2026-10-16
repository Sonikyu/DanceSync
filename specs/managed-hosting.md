# Managed hosting: one-click deploy

> TODO.md: "make it a web app, not just locally hosted"

**Size:** S · **Depends on:** nothing on Render. On Fly.io it depends on the [job queue](../tickets/DS-13-job-queue.md) (see below).

## Today

DanceSync can already be a web app: [`docs/hosting.md`](../docs/hosting.md) puts it on a VPS with Docker and Caddy, behind the shared passphrase. Getting there takes a VPS, a DNS record, SSH, installing Docker and Caddy, editing two config files, and running a backup cron yourself. Updating means SSHing in to `git pull` and rebuild. That's an afternoon for the owner, and not something a friend could do.

## Goal

The owner clicks a "Deploy" button in the README, picks a passphrase, and a few minutes later has an `https://` link to send to friends. Nothing to SSH into, a TLS certificate that renews itself, backups that happen by themselves, and every push to `main` deploys.

The audience doesn't change: the owner and friends, behind one shared passphrase. Per-person accounts, open sign-up, cloud storage, and scaling past one machine are all out of scope (see the end).

## Key decisions

- **Render, with a Blueprint (`render.yaml`) and a "Deploy to Render" button.** It's the only common platform where today's code works unchanged:
  - **Long requests.** Alignment runs inside the upload POST, and renders inside `HEAD /synced`, so a request can take minutes. Render keeps an HTTP request open for up to 100 minutes. Fly.io closes a connection after 60 s with no bytes sent, and a `HEAD` that's rendering sends nothing, so on Fly every side-by-side render of a long take fails until [DS-13](../tickets/DS-13-job-queue.md) lands.
  - **A persistent disk** with automatic daily snapshots kept for at least 7 days. That replaces the hosting runbook's backup cron.
  - **Docker as-is.** Render builds the existing `Dockerfile`, sets `PORT` (which the `CMD` already reads), and terminates TLS with `X-Forwarded-Proto` set, which the cookie's `Secure` flag needs.
- **Fly.io is the cheaper second choice once DS-13 is in.** It can stop the machine when nobody's using it. Revisit this spec after DS-13 and add a `fly.toml` then, not now.
- **One disk, mounted at `/data`.** Render gives a service one disk. The cache moves under it with `DANCESYNC_CACHE_DIR=/data/cache`. The cache is still safe to delete; it now also gets snapshotted, which costs nothing that matters.
- **Instance size: 2 GB of RAM at least** (Render's "Standard" today). The matcher needs about 1 GB while it works, so the 512 MB tiers will be killed mid-upload. Renders are CPU-bound, so more CPU means shorter waits, as in the runbook's measurements.
- **Disk: 20 GB to start.** Uploads are never deleted, and renders are capped at 5 GB (`DANCESYNC_RENDER_CACHE_GB`). The disk can be grown later but not shrunk.
- **The passphrase is generated at deploy time** (`generateValue: true`), and the owner reads it from the dashboard, or replaces it with one they pick. A deploy without a passphrase would put an open, unauthenticated upload endpoint on the internet, so the Blueprint never allows that.
- **One instance, and a short outage on every deploy.** A service with a disk can't run two instances, so Render stops the old one before starting the new one. A render in progress during a deploy is lost, and the next request starts it again, as already happens with `docker compose up`. Fine for a group of friends; note it in the docs.
- **Auto-deploy from `main`.** Updating becomes "merge the PR". The owner can turn it off in the dashboard.
- **No code changes to `server/` or `dancesync/`.** If anything has to change in the app to run there, that's a finding that goes in the PR, not a silent fix.

## To verify before writing the docs

These are platform details that change, and getting them wrong shows up only on a real deploy:

- **The disk mount is writable by the `dancesync` user.** The image runs as a non-root user. If Render mounts the disk as root-owned, the first upload fails with a permission error. Fixes, in order of preference: a documented setting, or an entrypoint that creates the folders it needs.
- **The `VOLUME` line in the `Dockerfile`** doesn't conflict with Render's disk. Some platforms reject images that declare volumes.
- **A 500 MB upload goes through** Render's proxy (the clip limit). If it doesn't, lower `DANCESYNC_MAX_CLIP_MB` in the Blueprint and say why.
- **Current prices** for the instance and the disk, written down in the docs with the date checked.

## What to build

```
render.yaml          Blueprint: one Docker web service, a disk at /data, env vars
                     (DANCESYNC_PASSPHRASE generated, DANCESYNC_CACHE_DIR=/data/cache,
                     DANCESYNC_STORAGE_ROOT=/data), autoDeploy on main
README.md            "Deploy to Render" button, one paragraph on what it costs and does
docs/hosting.md      new first section: the one-click path, with the VPS + Caddy path
                     kept below it for anyone who wants it cheaper or self-managed:
                     - first deploy: find the passphrase, share the link
                     - backups: the daily snapshots, and how to restore one
                       (it rolls back the whole disk, so newer uploads are lost)
                     - updating: merge to main; turning auto-deploy off
                     - a deploy restarts the server and loses renders in progress
CLAUDE.md            mention render.yaml in the repository structure
```

## Tests

There's no automated test for a hosting platform. The acceptance check is one real deploy, recorded in the PR:

- **Smoke test** on a fresh Blueprint deploy, from a phone:
  1. Sign in with the generated passphrase.
  2. Upload a song, and a take of 3 minutes or more.
  3. Download a side-by-side render, which takes more than 60 s.
  4. Trigger a redeploy, and check the song and take are still there.
- **Record the timings** (align, render) next to the runbook's VPS numbers.
- `render.yaml` is checked by Render's Blueprint validation when the button is first used. No CI step for it.

## Acceptance criteria

- Clicking the README button deploys a working, passphrase-protected DanceSync without opening a terminal
- The smoke test passes, including a render that takes more than 60 s
- Uploads survive a redeploy, and a daily snapshot appears on the disk
- Merging to `main` deploys the change
- `docs/hosting.md` leads with the one-click path, and the VPS path still works unchanged

## Out of scope

- **Per-person accounts, open sign-up, billing.** A different audience, and a much bigger spec: per-user data, quotas, abuse limits, cloud storage, and takedown handling for uploaded songs. It also rules out [YouTube import](youtube-import.md).
- **More than one instance,** cloud storage (S3/GCS), or a database. One disk on one machine holds everything, as on the VPS.
- **Scale to zero.** That needs Fly.io, so it waits for DS-13.
- **A custom domain.** Render supports one through its dashboard. Mention it in the docs; there's nothing to build.
- **YouTube import from Render.** Same caveat as any datacenter IP: YouTube may block it. Test it when that feature lands.
