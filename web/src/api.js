import { clipTooShortMessage } from "./flow.js";

// Fetch wrappers for the FastAPI backend. Paths are relative: in dev, Vite
// proxies /api to the server, so the browser only ever talks to one origin.

const UNREACHABLE = "Can't reach the DanceSync server. Is it running?";

// The server's error text is written for developers; these are for dancers.
const MESSAGES = {
  401: "You've been signed out. Reload the page to sign in again.",
  413: "That file's too big. Songs can be up to 100 MB and videos up to 500 MB.",
  415: "That file type isn't supported. Use a video (.mp4, .mov) or audio file (.mp3, .m4a, .wav).",
};

// The same statuses mean something else for a YouTube import.
const IMPORT_MESSAGES = {
  ...MESSAGES,
  400: "That's not a link to a YouTube video. Copy the link from the video's Share button.",
  413: "That video's too long or too big to import. Use one under 15 minutes, or upload the file instead.",
  422: "Couldn't download that video. It may be private, age-restricted, or live. Try another link, or upload the file instead.",
  503: "YouTube import isn't set up on this server. Upload the file instead.",
};

// `{ signed_in }`. Always true when the server has no passphrase set.
export function getSession() {
  return request("/api/session");
}

// Resolves on success. The session cookie it sets covers every later
// request, including the range requests <video> and <audio> make.
export async function signIn(passphrase) {
  const resp = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passphrase }),
  }).catch(() => {
    throw new Error(UNREACHABLE);
  });
  if (resp.status === 401) throw new Error("That's not the passphrase. Try again.");
  if (!resp.ok) throw new Error("Something went wrong on the server. Try again.");
}

export function listReferences() {
  return request("/api/references");
}

export function uploadReference(file, onProgress) {
  return upload("/api/references", file, onProgress);
}

// Downloads the video on the server and resolves to a Reference, the same as
// an upload. A link imported before resolves to the existing one.
export function importReference(url) {
  const options = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  };
  return request("/api/references/import", options, IMPORT_MESSAGES);
}

export function uploadClip(referenceId, file, onProgress) {
  const query = new URLSearchParams({ reference_id: referenceId });
  return upload(`/api/clips?${query}`, file, onProgress);
}

export function selectCandidate(clipId, index) {
  return request(`/api/clips/${clipId}/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ index }),
  });
}

// Override the matcher's alignment with one set by hand. `offset_sec` is in
// the original song timeline, like a candidate's. Resolves to the Clip.
export function setManualAlignment(clipId, { rate, offset_sec }) {
  return request(`/api/clips/${clipId}/manual`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rate, offset_sec }),
  });
}

// Back to the matcher's alignment. Resolves to the Clip.
export function clearManualAlignment(clipId) {
  return request(`/api/clips/${clipId}/manual`, { method: "DELETE" });
}

// The take exactly as it was uploaded, for playing on Watch without a render.
export function clipMediaUrl(clipId) {
  return `/api/clips/${clipId}/media`;
}

// The song file itself: audio for previews, video for the side-by-side view.
export function referenceMediaUrl(referenceId) {
  return `/api/references/${referenceId}/media`;
}

// Everything a render depends on besides the clip, which is in the URL's
// path. Mirrors the server's RenderParams, and tests/test_render_params.py
// fails if the two drift. Every field goes in the URL, so a render that
// changes never replays from the browser's cache (invariant 7).
export const RENDER_PARAM_FIELDS = ["reference_id", "rate", "offset_sec", "layout", "sound"];

// `renderParams` comes from flow.renderParams. The server reads `sound` and
// `layout` from the query and the alignment from its own catalog.
export function syncedVideoUrl(clipId, renderParams) {
  const query = new URLSearchParams();
  for (const field of RENDER_PARAM_FIELDS) {
    if (renderParams[field] === undefined) throw new Error(`syncedVideoUrl: missing ${field}`);
    query.set(field, renderParams[field]);
  }
  return `/api/clips/${clipId}/synced?${query}`;
}

// HEAD makes the server render (if it hasn't already) without sending the
// video, so the UI can wait for the render before handing the URL to <video>.
export async function renderSynced(url) {
  const resp = await fetch(url, { method: "HEAD" }).catch(() => {
    throw new Error(UNREACHABLE);
  });
  if (!resp.ok) throw new Error("Couldn't make that video. Try again, or try another take.");
}

async function request(url, options, messages = MESSAGES) {
  const resp = await fetch(url, options).catch(() => {
    throw new Error(UNREACHABLE);
  });
  return parseResponse(resp.status, await resp.text(), messages);
}

// XMLHttpRequest rather than fetch: fetch can't report upload progress, and a
// practice video can be hundreds of megabytes. `onProgress` gets 0 to 1.
function upload(url, file, onProgress) {
  const form = new FormData();
  form.append("file", file);
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (event) => onProgress(event.loaded / event.total);
    xhr.onload = () => resolve(xhr);
    xhr.onerror = () => reject(new Error(UNREACHABLE));
    xhr.send(form);
  }).then((xhr) => parseResponse(xhr.status, xhr.responseText));
}

function parseResponse(status, text, messages = MESSAGES) {
  if (status < 400) return JSON.parse(text);
  throw new Error(errorMessage(status, text, messages));
}

// Most errors get a fixed message by status. A too-short clip gets one with
// its own numbers, from the server's structured `detail`.
function errorMessage(status, text, messages) {
  const detail = errorDetail(text);
  if (detail?.error === "clip_too_short") return clipTooShortMessage(detail.duration_sec, detail.min_sec);
  return messages[status] ?? "Something went wrong on the server. Try again.";
}

function errorDetail(text) {
  try {
    return JSON.parse(text).detail;
  } catch {
    return null;
  }
}
