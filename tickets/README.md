# Tickets

One file per ticket, each sized at roughly half a day to a day, each independently mergeable with its own tests. Tickets are the implementation layer under [`specs/`](../specs/): a spec says what a feature is and why, a ticket says what to build next and how you'll know it's done. Every ticket links to its spec — read that first, then the ticket.

Ids are stable and never reused. They are grouped by track, and the number does not imply the order — the order is in this file.

## Conventions

- **A ticket that touches a render must satisfy invariant 7.** After [DS-03](DS-03-render-params-record.md) this means adding a field to the render-params record, not editing two string builders. A test fails if the two sides drift.
- **A ticket that changes the matcher must keep Tier A green.** A Tier A failure after a matcher change is a bug in the change, not a finding.
- **Sizes:** XS under an hour, S a few hours, M about a day, L more than a day (split it if you can).
- **New ideas** go to [`TODO.md`](../TODO.md), get a spec in `specs/`, and only then become tickets here.

## Tracks

| Track | What it is |
|---|---|
| **Foundations** | Make the gate real and stop the same two-sided bug from recurring. Before everything. |
| **Ship** | What's left before the MVP is done. |
| **Operate** | Keeping a self-hosted box healthy. Not MVP-blocking. |
| **Platform** | The job queue and progress channel. Not a user-facing feature; unblocks the slow ones. |
| **Feature tracks** | One per spec: instant preview, review speed, manual alignment, layouts, YouTube import, video editing, practice speeds, follow dancer. |

## Recommended order

Steps 1–5 are done (see the Status column in the index below). Next up is step 6, by what you need.

**1 · Foundations** — [DS-01](DS-01-ci-test-workflow.md), [DS-02](DS-02-ffmpeg-startup-check.md), [DS-03](DS-03-render-params-record.md).
DS-01 first, literally: every ticket after it relies on CI being real. DS-03 before any feature that changes a render, which is five of the eight.

**2 · Ship the MVP** — [DS-04](DS-04-clip-too-short.md), [DS-05](DS-05-alignment-failed.md), [DS-06](DS-06-dockerfile.md), [DS-07](DS-07-serve-web-dist.md), [DS-08](DS-08-docker-compose.md), [DS-09](DS-09-access-control.md).

**3 · Instant preview** — [DS-15](DS-15-clip-media-endpoint.md) → [DS-16](DS-16-clip-time-mapping.md) → [DS-17](DS-17-leader-follower-by-sound.md) → [DS-18](DS-18-play-raw-clip.md) → [DS-19](DS-19-playback-fallback.md).
The speedup the dancer notices most, and four later features queue behind it. DS-15 and DS-16 are independent of each other and can go in parallel.

**4 · The cheap wins it unlocks** — review speed ([DS-20](DS-20-segmented-control.md), [DS-21](DS-21-review-speed-control.md)) and layouts ([DS-27](DS-27-compare-command.md), [DS-28](DS-28-layout-api.md), [DS-29](DS-29-layout-picker.md)). Small, and each is visible the day it lands.

**5 · Manual alignment** — [DS-22](DS-22-manual-alignment-api.md) → [DS-23](DS-23-effective-alignment.md) → [DS-24](DS-24-fine-tune-ui.md) → [DS-25](DS-25-both-sound.md) → [DS-26](DS-26-manual-placement-fallback.md).
The safety net: it fixes a slightly-off match, covers speeds the matcher doesn't try until practice speeds lands, and DS-26 closes the loop on the MVP's failure message.

**6 · Then, by what you need** — YouTube import ([DS-30](DS-30-youtube-url-validation.md)–[DS-32](DS-32-youtube-ui.md), independent, but behind DS-09 before it's exposed); video editing ([DS-33](DS-33-edit-models-api.md)–[DS-39](DS-39-trim-ui.md)); practice speeds ([DS-40](DS-40-coarse-rate-grid.md)–[DS-45](DS-45-stretch-clip-experiment.md), worth moving up if anyone regularly practices off-grid); platform ([DS-13](DS-13-job-queue.md), [DS-14](DS-14-progress-events.md)); operate ([DS-10](DS-10-render-cache-cleanup.md)–[DS-12](DS-12-hosting-runbook.md)).

**7 · Follow dancer** — [DS-46](DS-46-follow-dancer-spike.md) is a go/no-go spike, and nothing after it gets specced into tickets until it returns. [DS-47](DS-47-keyframed-crop.md) is the no-computer-vision fallback if it fails.

## Index

| Id | Ticket | Track | Size | Depends on | Status |
|---|---|---|---|---|---|
| [DS-01](DS-01-ci-test-workflow.md) | Run the test suites in CI | Foundations | S | — | Done |
| [DS-02](DS-02-ffmpeg-startup-check.md) | Fail fast when ffmpeg is missing | Foundations | XS | — | Done |
| [DS-03](DS-03-render-params-record.md) | One render-params record | Foundations | S | — | Done |
| [DS-04](DS-04-clip-too-short.md) | Reject clips too short to match | Ship | S | — | Done |
| [DS-05](DS-05-alignment-failed.md) | Report an outright alignment failure | Ship | S | — | Done |
| [DS-06](DS-06-dockerfile.md) | Dockerfile with ffmpeg | Ship | S | — | Done |
| [DS-07](DS-07-serve-web-dist.md) | FastAPI serves the built frontend | Ship | S | — | Done |
| [DS-08](DS-08-docker-compose.md) | `docker compose up` | Ship | XS | 06, 07 | Done |
| [DS-09](DS-09-access-control.md) | Shared-passphrase access control | Ship | S | 07 | Done |
| [DS-10](DS-10-render-cache-cleanup.md) | Cap the render cache | Operate | S | — | Done |
| [DS-11](DS-11-benchmark-harness.md) | Real-clip benchmark harness | Operate | M | 01 | |
| [DS-12](DS-12-hosting-runbook.md) | Hosting runbook | Operate | S | 08, 09 | Done |
| [DS-13](DS-13-job-queue.md) | Job queue for align and render | Platform | M–L | — | |
| [DS-14](DS-14-progress-events.md) | Progress over SSE | Platform | M | 13 | |
| [DS-15](DS-15-clip-media-endpoint.md) | Serve the uploaded clip bytes | Instant preview | S | — | Done |
| [DS-16](DS-16-clip-time-mapping.md) | Clip↔output time mapping | Instant preview | S | — | Done |
| [DS-17](DS-17-leader-follower-by-sound.md) | Leader and follower by sound | Instant preview | M | 16 | Done |
| [DS-18](DS-18-play-raw-clip.md) | Play the raw clip | Instant preview | M | 15, 16, 17 | Done |
| [DS-19](DS-19-playback-fallback.md) | Fall back to the server render | Instant preview | S–M | 18 | Done, but the real-device browser matrix is still owed |
| [DS-20](DS-20-segmented-control.md) | Shared `Segmented` control | Review speed | XS | — | Done |
| [DS-21](DS-21-review-speed-control.md) | Review at 0.5× / 0.75× / 1× | Review speed | S | 18, 20 | Done |
| [DS-22](DS-22-manual-alignment-api.md) | Manual alignment model + endpoints | Manual alignment | S | — | Done |
| [DS-23](DS-23-effective-alignment.md) | Use the effective alignment | Manual alignment | S | 03, 22 | Done |
| [DS-24](DS-24-fine-tune-ui.md) | Fine-tune panel | Manual alignment | M | 23 | Done |
| [DS-25](DS-25-both-sound.md) | "Both" sound for tuning by ear | Manual alignment | XS | 17, 24 | Done |
| [DS-26](DS-26-manual-placement-fallback.md) | Manual placement on failure | Manual alignment | S | 05, 24 | Done |
| [DS-27](DS-27-compare-command.md) | One compare command | Layouts | S | — | Done |
| [DS-28](DS-28-layout-api.md) | `stacked` through the API | Layouts | XS | 03, 27 | Done |
| [DS-29](DS-29-layout-picker.md) | Pick a layout on Watch | Layouts | S | 20, 28 | Done |
| [DS-30](DS-30-youtube-url-validation.md) | URL allowlist + metadata probe | YouTube | S | — | |
| [DS-31](DS-31-youtube-import-route.md) | Download an import | YouTube | M | 30 | |
| [DS-32](DS-32-youtube-ui.md) | Paste a link on the Song step | YouTube | XS | 31 | |
| [DS-33](DS-33-edit-models-api.md) | Framing and trim model + endpoints | Editing | S | — | |
| [DS-34](DS-34-framing-filters.md) | `framing.py` filter builders | Editing | S | 33 | |
| [DS-35](DS-35-trimmed-offset.md) | `trimmed_offset` | Editing | S | 33 | |
| [DS-36](DS-36-render-with-edits.md) | Renders apply the edits | Editing | M | 03, 34, 35 | |
| [DS-37](DS-37-framing-preview.md) | Live edit preview | Editing | S | 18, 33 | |
| [DS-38](DS-38-adjust-ui.md) | Adjust: crop, mirror, rotate | Editing | M | 37 | |
| [DS-39](DS-39-trim-ui.md) | Trim the take | Editing | S | 35, 38 | |
| [DS-40](DS-40-coarse-rate-grid.md) | Coarse rate grid + dedupe | Practice speeds | M | — | |
| [DS-41](DS-41-incremental-feature-cache.md) | Cache only missing rates | Practice speeds | S | 40 | |
| [DS-42](DS-42-rate-refinement.md) | Measure the rate from drift | Practice speeds | M | 40 | |
| [DS-43](DS-43-precompute-on-upload.md) | Stretch on song upload | Practice speeds | S | 13, 41 | |
| [DS-44](DS-44-offgrid-rate-tests.md) | Off-grid coverage + display | Practice speeds | S | 42 | |
| [DS-45](DS-45-stretch-clip-experiment.md) | Experiment: stretch the clip | Practice speeds | S | 40 | |
| [DS-46](DS-46-follow-dancer-spike.md) | Spike: follow one dancer | Follow dancer | L | 13 | |
| [DS-47](DS-47-keyframed-crop.md) | Fallback: keyframed crop | Follow dancer | M | 36, 46 fails | |

## Decisions made while writing these

- **The MVP no longer depends on post-MVP work.** The roadmap had Phase 5's "no strong peak" error case handing off to manual placement, which sits behind instant preview and the fine-tune panel. Split in two: [DS-05](DS-05-alignment-failed.md) detects the failure and says so (MVP), [DS-26](DS-26-manual-placement-fallback.md) turns that into the handoff (later).
- **Invariant 7 became one refactor instead of five reviews.** Five queued features each add a field to the server's cache name *and* the browser's query string, with a stale render as the silent failure. [DS-03](DS-03-render-params-record.md) makes that one field in one record, with a test that fails if the two sides drift.
- **Phase 5 split into three tracks.** Ship, Operate, and Platform were one heading covering MVP blockers, hosting hygiene, and a hard dependency of follow dancer. They have different urgency and different audiences.
