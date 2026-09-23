# DanceSync

Practice to slowed-down music, then review at full speed.

A dancer plays a song at reduced speed (say 0.75×) on a laptop and films themselves on a phone. DanceSync works out which part of the song the recording covers and how fast it was playing. It then re-times the video to the original tempo and puts the original track under it, next to the choreography video if there is one.

> **Two ways to run it:** from source on your own computer (below), or as a single Docker container that you can also host on a server ([Running it with Docker](#running-it-with-docker)).

## How it works

1. **Match** (`dancesync/matcher.py`): the phone's audio is compared against the reference at each candidate playback rate, using chroma features. When a repeated chorus makes the answer ambiguous, the user picks from the top three candidates.
2. **Re-time** (`dancesync/sync.py`): one ffmpeg command speeds the video up by `1/rate` and lays the reference audio underneath, starting from the matched point.
3. **Review** (`web/`): the synced take plays next to the reference video, with either the song or the room sound.

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

1. **Choose your song:** upload the original track. An audio file works; a video of the choreography is better, because then you get the side-by-side view.
2. **Add your practice video:** the phone recording. Finding your place in the song takes 10–30 seconds, and the first take against a new song takes longer.
3. **Which part did you dance?** You only see this screen if the song has repeated sections that sound alike. Play each candidate and pick yours.
4. **Watch:** the synced take plays next to the reference. Switch between the song and the room sound, or download the video.

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
| `.data/server/` | uploaded songs and videos, their metadata, and rendered videos |
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

**Poking at the API directly:** http://localhost:8000/docs lists every endpoint and lets you call them from the browser.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| "Can't reach the DanceSync server. Is it running?" | Terminal 1 isn't running, or it crashed. Check it and start it again. |
| "Something went wrong on the server." | Check terminal 1 for a traceback. If it ends in `needs ffmpeg to decode`, run `brew install ffmpeg` and restart the API. |
| "We couldn't find this take in the song" | The sound in the video didn't match the song well enough anywhere. Usually it's the wrong song, a practice speed other than full, ¾ or ½, or music too quiet under the room noise. "Watch the best guess anyway" shows what the matcher found. |
| "Couldn't make that video." | The render failed, and terminal 1 only logs a `422` line. To see ffmpeg's actual error, open your browser's developer tools, go to the Network tab, find the failed `synced?…` request, and open its URL in a new tab. The usual causes are a missing ffmpeg or a corrupt file. |
| `[Errno 48] Address already in use` | Something else is on port 8000, often an API server you left running. Find it with `lsof -i :8000`, or use another port (see above). |
| `ModuleNotFoundError` when starting the API | Run the `pip install` line from step 2 again. Make sure the command starts with `.venv/bin/`. |
| Vite refuses to start and mentions the Node version | Upgrade Node: `brew upgrade node`. |
| The phone can't load the page | Check that you started the web app with `-- --host`, that the phone is on the same Wi-Fi, and that you're using the numeric `Network:` address. |

---

## Tests

```bash
.venv/bin/python -m pytest     # about a minute, because it renders real video
npm --prefix web test
```

## Project layout

```
dancesync/   matcher + sync engine (Python library, no web code)
server/      FastAPI app: upload, align, select, render
web/         React + Vite frontend
tests/       pytest: Tier A matcher regression, API, renders
specs/       specs for post-MVP features
spike/       the original alignment experiment (reference only, not imported)
```

- [next-steps.md](next-steps.md): status and roadmap
- [CLAUDE.md](CLAUDE.md): architecture, invariants, and coding style
- [spike/README.md](spike/README.md): the validation experiment
