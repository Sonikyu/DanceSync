# DanceSync

Practice to slowed-down music, then review at full speed.

A dancer plays a song at reduced speed (say 0.75×) on a laptop and films themselves on a phone. DanceSync works out which part of the song the recording covers and how fast it was playing. It then re-times the video to the original tempo and puts the original track under it, next to the choreography video if there is one.

> **Two ways to run it:** from source on your own computer (below), or as a single Docker container that you can also host on a server ([Running it with Docker](#running-it-with-docker)).

## What it can do today

| | Supported |
|---|---|
| **Song** | An audio file (MP3, M4A, WAV, …) or a video of the choreography (MP4, MOV), up to 100 MB. Or a YouTube link, up to 15 minutes and 300 MB; not private, age-restricted, or live videos. |
| **Practice video** | Any video ffmpeg can read (a phone's MOV or MP4, HEVC included), at least 10 seconds long and up to 500 MB. |
| **Practice speeds** | Found automatically at full, ¾, or ½ speed. Any other speed from 0.25× to 1× can be set by hand in Fine-tune. |
| **Repeated choruses** | When two parts of the song sound alike, you pick yours from the top three. |
| **No match** | Place the take on the song's timeline by hand, then fine-tune by ear. |
| **Watch** | Plays straight away, no rendering. Sound: the song, the room, or both (while fine-tuning). Review speed: 0.5×, 0.75×, or 1×. Layout: side by side, stacked, or take only. |
| **Edits** | Crop, mirror, and rotate either video; trim the start and end of the take. The song's framing is kept for every take of it. |
| **Download** | An MP4 of exactly what's on screen (layout, sound, edits), made on demand at full speed. |
| **Sharing** | One shared passphrase for the owner and friends. No separate accounts. |

**Not yet:** practice speeds other than full, ¾, and ½ found automatically, progress bars for long uploads and renders, and following one dancer in a group video. See [next-steps.md](next-steps.md).

## How it works

1. **Match** (`dancesync/matcher.py`): the phone's audio is compared against the reference at each candidate playback rate, using chroma features. When a repeated chorus makes the answer ambiguous, the user picks from the top three candidates.
2. **Review** (`web/`): the browser plays the uploaded video sped up by `1/rate`, next to the reference video and in time with the song, so it's ready the moment the match is. The two are kept in step by nudging the silent one's playback speed.
3. **Render on download** (`dancesync/sync.py`): one ffmpeg command speeds the video up by `1/rate`, applies the crop, mirror, rotate, and trim, puts it beside or under the reference video if asked, and lays the chosen sound underneath, starting from the matched point, with the same timing the browser uses.

---

## Running it locally

DanceSync is two programs that run side by side:

| | What it is | Address |
|---|---|---|
| **API server** | Python (FastAPI). Stores uploads, matches audio, and renders videos with ffmpeg. | http://localhost:8000 |
| **Web app** | React, served by Vite. The page you open in the browser. | http://localhost:5173 |

You only ever open the web app. It forwards anything under `/api` to the API server, so both need to be running.

### 1. Install the tools (once)

These steps assume macOS with [Homebrew](https://brew.sh).

```bash
brew install node ffmpeg
brew install deno          # optional: only needed to import songs from YouTube links
```

Check the versions:

```bash
python3 --version   # needs 3.11 or newer
node --version      # needs 20.19+ or 22.12+
ffmpeg -version     # any recent version
```

If `python3` is older than 3.11, run `brew install python@3.12` and use `python3.12` wherever step 2 says `python3`.

### 2. Set up the project (once)

```bash
git clone https://github.com/Sonikyu/DanceSync.git
cd DanceSync

python3 -m venv .venv                  # a private Python environment inside the repo
.venv/bin/pip install -e '.[dev]'      # the Python dependencies (librosa, FastAPI, …)
npm --prefix web install               # the web app's dependencies
```

All commands from here on are run from the `DanceSync` folder. Nothing needs activating: `.venv/bin/…` always uses the project's own Python.

### 3. Start the servers

Open **two terminal windows**, both in the `DanceSync` folder.

**Terminal 1: the API server**

```bash
.venv/bin/uvicorn server.main:app --port 8000
```

Wait for `Uvicorn running on http://127.0.0.1:8000`.

**Terminal 2: the web app**

```bash
npm --prefix web run dev
```

Wait for `Local: http://localhost:5173/`.

Now open **http://localhost:5173** in your browser.

Leave both terminals open while you use the app. Errors from the server show up in terminal 1.

> **Working on the Python code?** Add `--reload` to the uvicorn command so it restarts whenever you save a file. Leave it off when you're just using the app, because a restart kills any render that's in progress. The web app always reloads by itself.

### 4. Try it

1. **Choose your song:** upload the original track. An audio file works; a video of the choreography is better, because then you can watch your take beside it or under it. You can also paste a YouTube link to a dance practice video, and the server downloads it (up to 15 minutes long).
2. **Add your practice video:** the phone recording. Finding your place in the song takes 10–30 seconds, and the first take against a new song takes longer.
3. **Which part did you dance?** You only see this screen if the song has repeated sections that sound alike. Play each candidate and pick yours.
4. **Watch:** the synced take plays next to the reference, straight away. Switch between the song and the room sound, slow it down, pick a layout, or download the video (the download is made when you ask for it, and takes about as long as the clip). If it's slightly out of sync, open **Fine-tune**: nudge the offset (or the practice speed, if it drifts), and pick **Both** under Sound to hear the song and the room together; they sound like one when they line up.

To get the two dancers the same size, press **Adjust** under either video: drag the box to crop to the dancer, and **Mirror** or **Rotate** if needed. The song's framing is kept for every take of it. Under your take, **Set start here** and **Set end here** trim off the walk to and from the phone. Downloads come out exactly as the preview looks.

If DanceSync can't find your take in the song at all, you can place it by hand: drag to roughly where it starts, then fine-tune by ear.

Songs you've uploaded stay in the list the next time you start the app.

### Stopping

Press **Ctrl+C** in each terminal.

---

## Running it with Docker

On any machine that has [Docker](https://docs.docker.com/get-docker/), this is all it takes. The Docker image includes ffmpeg and the built web app, so you don't need to install Python or Node:

```bash
git clone https://github.com/Sonikyu/DanceSync.git && cd DanceSync
cp .env.example .env              # optional: change the port or upload limits
docker compose up -d --build
```

Open http://localhost:8000. A single container serves both the web app and the API on one port.

- **Your files live in two Docker volumes.** `data` holds uploads, their metadata, and renders. `cache` holds decoded audio and song features, and it's safe to delete. Both survive `docker compose down` and rebuilds. Only `docker compose down -v` deletes them.
- **Updating:** `git pull && docker compose up -d --build`.
- **Logs:** `docker compose logs -f`.
- **Hosting it on a server** for friends: follow [docs/hosting.md](docs/hosting.md).
- **Before you put it on the internet,** set `DANCESYNC_PASSPHRASE` in `.env` and run `docker compose up -d` again. Everyone then signs in once with that passphrase, and stays signed in for 30 days on that browser.

---

## Using it from your phone

To upload straight from your phone, or watch the result on it, start the web app with `--host`:

```bash
npm --prefix web run dev -- --host
```

Vite then prints a `Network:` address such as `http://192.168.1.23:5173/`. Open it on a phone that's on the same Wi-Fi. The API server doesn't need any changes, because the web app forwards to it.

- Use the numeric address Vite prints. Vite rejects hostnames like `my-mac.local` with "Blocked request. This host is not allowed."
- Only do this on a network you trust. Anyone on it can open the app, unless you start the API with a passphrase: `DANCESYNC_PASSPHRASE=… .venv/bin/uvicorn server.main:app --port 8000`.

---

## Everyday tasks

**After pulling new code**, update the dependencies if either dependency file changed:

```bash
.venv/bin/pip install -e '.[dev]'      # if pyproject.toml changed
npm --prefix web install               # if web/package.json changed
```

**Where your files go:**

| Folder | Holds |
|---|---|
| `.data/server/` | uploaded songs and videos, their metadata, and rendered videos (capped at 5 GB; the least recently watched are deleted and re-rendered on demand) |
| `.cache/dancesync/` | decoded audio and pre-computed song features, which make later takes faster |

Both folders are gitignored. **To start fresh**, stop the servers and delete them. This deletes everything you've uploaded:

```bash
rm -rf .data/server .cache/dancesync
```

**Running the API on a different port** (for example, if 8000 is taken):

```bash
.venv/bin/uvicorn server.main:app --port 8001
DANCESYNC_API_URL=http://localhost:8001 npm --prefix web run dev
```

**Running it as one process, without Docker** (what the container does): build the web app once, and the API serves it at http://localhost:8000. No second terminal needed, but rebuild after pulling new code.

```bash
npm --prefix web run build
.venv/bin/uvicorn server.main:app --port 8000
```

**Requiring a passphrase locally:** start the API with `DANCESYNC_PASSPHRASE=… .venv/bin/uvicorn server.main:app --port 8000`. The web app then shows a sign-in screen.

**Updating yt-dlp** when YouTube imports start failing (YouTube breaks it every few weeks):

```bash
.venv/bin/pip install -U 'yt-dlp[default]'
```

**Poking at the API directly:** http://localhost:8000/docs lists every endpoint and lets you call them from the browser.

---

## Settings

Every setting is optional and comes from an environment variable. With Docker, put them in `.env` (see `.env.example`); from source, put them in front of the `uvicorn` command.

| Variable | Default | What it does |
|---|---|---|
| `DANCESYNC_PASSPHRASE` | unset (no sign-in) | Shared passphrase. Set it before the app is reachable from the internet. Changing it signs everyone out. |
| `DANCESYNC_PORT` | `8000` | Docker only: the host port. `127.0.0.1:8000` keeps it private behind a reverse proxy. |
| `DANCESYNC_MAX_REFERENCE_MB` | `100` | Largest song upload. |
| `DANCESYNC_MAX_CLIP_MB` | `500` | Largest practice video upload. |
| `DANCESYNC_MAX_IMPORT_MB` | `300` | Largest YouTube import. |
| `DANCESYNC_RENDER_CACHE_GB` | `5` | Rendered videos past this size are deleted, least recently watched first, and re-rendered on demand. |
| `DANCESYNC_STORAGE_ROOT` | `.data/server` | Where uploads, their metadata, and renders go (`/data` in Docker). |
| `DANCESYNC_CACHE_DIR` | `.cache/dancesync` | Where decoded audio and song features go (`/cache` in Docker). Safe to delete. |
| `DANCESYNC_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Origins allowed to call the API from another site. Not needed for the web app this repo serves. |
| `DANCESYNC_WEB_DIST` | `web/dist` | The built web app, served at `/` when it exists. |
| `DANCESYNC_API_URL` | `http://localhost:8000` | Vite dev server only: where it forwards `/api`. |

---

## Troubleshooting

| What you see | What to do |
|---|---|
| "Can't reach the DanceSync server. Is it running?" | Terminal 1 isn't running, or it crashed. Check it and start it again. |
| "Something went wrong on the server." | Check terminal 1 for a traceback. If it ends in `needs ffmpeg to decode`, run `brew install ffmpeg` and restart the API. |
| "We couldn't find this take in the song" | The sound in the video didn't match the song well enough anywhere. Usually it's the wrong song, a practice speed other than full, ¾ or ½, or music too quiet under the room noise. "Watch the best guess anyway" shows what the matcher found. |
| "Preparing your video…" before Watch plays | Your browser can't play the phone's original file, usually HEVC (the iPhone default) in Firefox or in Chrome on Linux or older Windows, so the server converts it first. It works, just slower. To skip it, use Safari or Chrome on a Mac, or set the iPhone to Settings → Camera → Formats → Most Compatible. |
| "Couldn't make that video." | The render failed, and terminal 1 only logs a `422` line. To see ffmpeg's actual error, open your browser's developer tools, go to the Network tab, find the failed `synced?…` request, and open its URL in a new tab. The usual causes are a missing ffmpeg or a corrupt file. |
| `[Errno 48] Address already in use` | Something else is on port 8000, often an API server you left running. Find it with `lsof -i :8000`, or use another port (see above). |
| `ModuleNotFoundError` when starting the API | Run the `pip install` line from step 2 again. Make sure the command starts with `.venv/bin/`. |
| "YouTube import isn't set up on this server." | yt-dlp isn't installed. Run the `pip install` line from step 2 again. |
| "Couldn't download that video." | The video is private, age-restricted, or live, or YouTube changed something. Update yt-dlp (see Everyday tasks), and check that `deno --version` works. If terminal 1 says "confirm you're not a bot", YouTube is blocking that machine's IP; download the video another way and upload the file. |
| Vite refuses to start and mentions the Node version | Upgrade Node: `brew upgrade node`. |
| The phone can't load the page | Check that you started the web app with `-- --host`, that the phone is on the same Wi-Fi, and that you're using the numeric `Network:` address. |

---

## Tests

```bash
.venv/bin/python -m pytest              # a few minutes, because it renders real video
.venv/bin/python -m pytest -m network   # the tests that need the internet (a real YouTube import)
npm --prefix web test
```

CI runs pytest, Vitest, and a web build on every pull request.

## Project layout

```
dancesync/   matcher + sync engine (Python library, no web code)
server/      FastAPI app: sign-in, upload, YouTube import, align, edits, render
web/         React + Vite frontend
tests/       pytest: Tier A matcher regression, API, renders
docs/        hosting runbook
specs/       specs for post-MVP features
tickets/     each spec broken into day-sized tickets, and the working order
spike/       the original alignment experiment (reference only, not imported)
```

- [next-steps.md](next-steps.md): status and roadmap
- [CLAUDE.md](CLAUDE.md): architecture, invariants, and coding style
- [spike/README.md](spike/README.md): the validation experiment
